import datetime
import json
import pytz
import re
import uuid
from src.services.notion import NotionService
from src.services.ai import AIService
from src.utils.logger import logger
from src.utils.cache import (
    get_redis,
    CACHE_PAGE_TITLE_TTL,
    CACHE_CANDIDATES_TTL,
    CACHE_QUIZ_TTL,
    CACHE_QUIZ_PROGRESS_TTL,
    LOCK_QUIZ_TTL,
)

def natural_sort_key(s):
    """Natural sort key for strings containing numbers (e.g. Buổi 1, Buổi 2, Buổi 10)."""
    if not s:
        return []
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def get_page_title(page_id):
    """Retrieve title of a page by ID, using Redis cache if available."""
    cache_key = f"page_title_{page_id}"
    r = get_redis()
    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                return cached
        except Exception as e:
            logger.warning(f"Redis get error for {cache_key}: {e}")

    notion = NotionService()
    try:
        page_info = notion.retrieve_page(page_id)
        if isinstance(page_info, dict):
            props = page_info.get("properties") or {}
            for key, val in props.items():
                if isinstance(val, dict) and val.get("type") == "title" and val.get("title"):
                    title = "".join([t.get("plain_text", "") for t in val["title"] if isinstance(t, dict)]).strip() or None
                    if title:
                        if r:
                            try:
                                r.setex(cache_key, CACHE_PAGE_TITLE_TTL, title)
                            except Exception as ce:
                                logger.warning(f"Redis set error: {ce}")
                        return title
    except Exception as e:
        logger.error(f"Error fetching page title for {page_id}: {e}")

    return None

def get_candidates(limit=None, force_refresh=False):
    """Fetch review notes, sort by 'Last Review At', return top candidates with metadata."""
    cache_key = f"study_candidates_{limit if limit is not None else 'all'}"
    r = None
    if not force_refresh:
        try:
            r = get_redis()
            if r:
                cached = r.get(cache_key)
                if cached:
                    logger.info(f"Using cached study candidates list (limit={limit})")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis get candidates cache error: {e}")

    # Fallback to check if smaller limit cache exists when force_refresh=False is requested
    # But wait, if force_refresh is True, we bypass cache.
    # If limit=10 was cached previously under 'study_candidates_5', no, cache keys are distinct.

    notion = NotionService()
    candidates = notion.get_review_notes()

    if not candidates:
        return []

    def get_last_review_sort_key(note):
        try:
            if not isinstance(note, dict): return ""
            props = note.get("properties") or {}
            last_review_prop = props.get("Last Review At") or {}
            last_review = last_review_prop.get("date") or {}
            if isinstance(last_review, dict) and last_review.get("start"):
                 return last_review["start"]
        except Exception:
            pass
        return ""

    candidates.sort(key=get_last_review_sort_key)
    top_candidates = candidates[:limit] if limit is not None else candidates

    results = []
    relation_tasks = [] # list of (idx, prop_name, page_id)

    for idx, c in enumerate(top_candidates):
        c_id = c["id"]
        title = "Unknown Note"
        props = c.get("properties") or {}

        for key, val in props.items():
            if isinstance(val, dict) and val.get("type") == "title" and val.get("title"):
                title = "".join([t.get("plain_text", "") for t in val["title"] if isinstance(t, dict)]).strip() or "Unknown Note"
                break

        chapter_id = None
        course_id = None

        chapter_prop = props.get("📍DB Chương") or {}
        if isinstance(chapter_prop, dict) and chapter_prop.get("type") == "relation" and chapter_prop.get("relation"):
            chapter_id = chapter_prop["relation"][0]["id"]

        course_prop = props.get("🔹 DB Học Phần - UEH") or {}
        if isinstance(course_prop, dict) and course_prop.get("type") == "relation" and course_prop.get("relation"):
            course_id = course_prop["relation"][0]["id"]

        results.append({
            "id": c_id,
            "title": title,
            "chapter": None,
            "course": None,
            "updated_at": c.get("last_edited_time") or get_last_review_sort_key(c)
        })

        if chapter_id:
            relation_tasks.append((idx, "chapter", chapter_id))
        if course_id:
            relation_tasks.append((idx, "course", course_id))

    if relation_tasks:
        from concurrent.futures import ThreadPoolExecutor

        def fetch_task(task):
            res_idx, prop_name, page_id = task
            t_title = get_page_title(page_id)
            return res_idx, prop_name, t_title

        with ThreadPoolExecutor(max_workers=10) as executor:
            task_results = executor.map(fetch_task, relation_tasks)
            for res_idx, prop_name, t_title in task_results:
                if t_title:
                    results[res_idx][prop_name] = t_title

    # Sort results by Course -> Chapter -> Title using natural sort (Buổi 1, 2, ... 10)
    results.sort(key=lambda x: (
        natural_sort_key(x.get("course") or ""),
        natural_sort_key(x.get("chapter") or ""),
        natural_sort_key(x.get("title") or "")
    ))

    # Save to Redis cache
    if results:
        try:
            r = r or get_redis()
            if r:
                r.setex(cache_key, CACHE_CANDIDATES_TTL, json.dumps(results))
                logger.info("Saved study candidates list to cache")
        except Exception as e:
            logger.warning(f"Redis set candidates cache error: {e}")

    return results

def split_into_3_chunks(text: str) -> list[str]:
    """Split text into 3 chunks using Markdown H1 (#) headings if possible."""
    import math
    import re

    sections = [s.strip() for s in re.split(r'\n(?=#\s)|^(?=#\s)', text) if s.strip()]
    if len(sections) >= 3:
        group_size = math.ceil(len(sections) / 3)
        return [
            "\n\n".join(sections[i : i + group_size])
            for i in range(0, len(sections), group_size)
        ]

    # Fallback to H2 (##) if H1 is less than 3
    h2_sections = [s.strip() for s in re.split(r'\n(?=##\s)|^(?=##\s)', text) if s.strip()]
    if len(h2_sections) >= 3:
        group_size = math.ceil(len(h2_sections) / 3)
        return [
            "\n\n".join(h2_sections[i : i + group_size])
            for i in range(0, len(h2_sections), group_size)
        ]

    # Final fallback for plain text or very short notes
    lines = text.splitlines()
    if len(lines) >= 3:
        group_size = math.ceil(len(lines) / 3)
        return [
            "\n".join(lines[i : i + group_size])
            for i in range(0, len(lines), group_size)
        ]

    return [text]

def clean_json_string(json_str):
    """Clean unescaped LaTeX backslashes and invalid escape sequences inside JSON string literals."""
    import re
    pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
    def replace_string(match):
        s = match.group(0)
        content = s[1:-1]
        fixed = []
        i = 0
        n = len(content)
        in_math = False
        while i < n:
            if content[i] == '$':
                if i + 1 < n and content[i+1] == '$':
                    in_math = not in_math
                    fixed.append('$$')
                    i += 2
                else:
                    in_math = not in_math
                    fixed.append('$')
                    i += 1
                continue
            if content[i] == '\\':
                is_double = (i + 1 < n and content[i+1] == '\\')
                next_char = content[i+2] if is_double and i + 2 < n else (content[i+1] if i + 1 < n else '')

                # In JSON strings, \n and \t might be literal escapes or intended as \n / \t LaTeX commands (\nu, \theta, \times)
                # If followed by letters (e.g. \frac, \nu, \theta, \times), treat as LaTeX backslash -> escape as \\
                if not is_double and next_char in ['n', 't', 'f', 'b', 'r'] and i + 2 < n and content[i+2].isalpha():
                    fixed.append('\\\\')
                    i += 1
                elif not is_double and next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't']:
                    fixed.append('\\')
                    fixed.append(next_char)
                    i += 2
                elif not is_double and next_char == 'u' and i + 5 < n and all(c in '0123456789abcdefABCDEF' for c in content[i+2:i+6]):
                    fixed.append('\\')
                    fixed.append('u')
                    fixed.extend(content[i+2:i+6])
                    i += 6
                else:
                    # Escape raw single backslash for LaTeX commands so JSON parsing succeeds without corrupting TeX
                    fixed.append('\\\\')
                    i += (2 if is_double else 1)
            elif content[i] == '\n':
                fixed.append('\\n')
                i += 1
            elif content[i] == '\t':
                fixed.append('\\t')
                i += 1
            else:
                fixed.append(content[i])
                i += 1
        return '"' + "".join(fixed) + '"'
    return pattern.sub(replace_string, json_str)

def clear_quiz_cache(topic_id: str, num_questions: int | None = None, difficulty: str | None = None, question_type: str | None = None) -> bool:
    """Delete cached quiz for a specific topic (or specific config) from Redis."""
    try:
        r = get_redis()
        if r:
            if num_questions is not None and difficulty is not None and question_type is not None:
                r.delete(f"quiz_{topic_id}_{num_questions}_{difficulty}_{question_type}")
            else:
                # Delete all variations of quiz cache for this topic
                r.delete(f"quiz_{topic_id}")
                for k in r.scan_iter(f"quiz_{topic_id}_*"):
                    r.delete(k)
            logger.info(f"Cleared quiz cache for topic {topic_id}")
            return True
    except Exception as e:
        logger.warning(f"Redis cache delete failed for topic {topic_id}: {e}")
    return False

def generate_quiz(topic_id, force_refresh=False, num_questions=15, difficulty='medium', question_type='balanced', progress_callback=None, cancel_event=None):
    """Fetch content from Notion, call AI to generate quiz with custom configuration, parse into JSON/Dict format."""
    if cancel_event and cancel_event.is_set():
        logger.info(f"Quiz generation cancelled early for topic {topic_id}")
        return None

    notion = NotionService()
    ai = AIService()

    import re
    import json

    # Cache key reflects configuration parameters
    cache_key = f"quiz_{topic_id}_{num_questions}_{difficulty}_{question_type}"

    # Try checking cache first
    if progress_callback:
        progress_callback("checking_cache", 5, "🔍 Đang kiểm tra bộ nhớ đệm...")

    r = None
    if not force_refresh:
        try:
            r = get_redis()
            if r:
                cached = r.get(cache_key)
                if not cached:
                    # Fallback to legacy unconfigured cache key if num_questions is 15 and default config
                    if num_questions == 15 and difficulty == 'medium' and question_type == 'balanced':
                        cached = r.get(f"quiz_{topic_id}")
                if cached:
                    logger.info(f"Using cached quiz for topic {topic_id} ({num_questions}q, {difficulty}, {question_type})")
                    if progress_callback:
                        progress_callback("parsing_quiz", 100, "✨ Đã tải trắc nghiệm thành công!")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")
    else:
        clear_quiz_cache(topic_id, num_questions, difficulty, question_type)

    if cancel_event and cancel_event.is_set():
        return None

    # Acquire Redis lock to prevent concurrent generation for same topic and config
    lock_key = f"quiz_lock_{topic_id}_{num_questions}_{difficulty}_{question_type}"
    lock_token = str(uuid.uuid4())
    lock_acquired = False
    try:
        r = r or get_redis()
        if r:
            lock_acquired = r.set(lock_key, lock_token, nx=True, ex=LOCK_QUIZ_TTL)
            if not lock_acquired:
                logger.info(f"⏳ Quiz generation already in progress for {topic_id} ({num_questions}q), waiting...")
                if progress_callback:
                    progress_callback("checking_cache", 10, "⏳ Đợi lượt tạo câu hỏi trước đó...")
                # Poll until lock released or timeout
                import time as time_mod
                waited = 0
                while waited < 30:
                    if cancel_event and cancel_event.is_set():
                        return None
                    time_mod.sleep(2)
                    waited += 2
                    cached = r.get(cache_key)
                    if cached:
                        logger.info(f"✅ Found cached quiz after waiting for {topic_id}")
                        if progress_callback:
                            progress_callback("parsing_quiz", 100, "✨ Đã tải trắc nghiệm thành công!")
                        return json.loads(cached)
                    if not r.get(lock_key):
                        break
                if cancel_event and cancel_event.is_set():
                    return None
                lock_acquired = r.set(lock_key, lock_token, nx=True, ex=LOCK_QUIZ_TTL)
    except Exception as e:
        logger.warning(f"Redis lock acquire failed (non-fatal): {e}")

    try:
        if cancel_event and cancel_event.is_set():
            return None

        # 1. Fetch content
        content_lines = notion.fetch_page_content(topic_id, progress_callback=progress_callback)
        if cancel_event and cancel_event.is_set():
            return None

        # Pre-clean markdown input before sending to AI to strip math-breaking formatting like $*V*$ or raw currency $
        cleaned_lines = []
        import re
        for line in content_lines:
            # Strip Markdown italic/bold tags surrounding LaTeX math dollars like $*V*$ or $**V**$
            l = re.sub(r'\$\*+(.*?)\*+\$', r'$\1$', line)
            cleaned_lines.append(l)
        full_content = "\n".join(cleaned_lines)

        if not full_content.strip() or (cancel_event and cancel_event.is_set()):
            return None

        # Default info
        note_url = f"https://notion.so/{topic_id.replace('-', '')}"
        note_title = "Bài học đã chọn"

        if progress_callback:
            progress_callback("page_info", 40, "📖 Đang đồng bộ thông tin tiêu đề...")

        cached_title = get_page_title(topic_id)
        if cached_title:
            note_title = cached_title

        if cancel_event and cancel_event.is_set():
            return None

        # 2. Call AI in 3 parallel chunks
        if progress_callback:
            diff_vn = {'easy': 'Cơ bản', 'medium': 'Chuẩn thi UEH', 'hard': 'Nâng cao'}.get(difficulty, 'Chuẩn thi')
            type_vn = {'theory': 'Lý thuyết', 'calculation': 'Tính toán', 'balanced': 'Cân bằng'}.get(question_type, 'Cân bằng')
            progress_callback("calling_ai", 45, f"🧠 Đang chia 3 phần bài học và soạn {num_questions} câu [{diff_vn} - {type_vn}]...")

        chunks = split_into_3_chunks(full_content)
        from concurrent.futures import ThreadPoolExecutor

        def generate_single_chunk(chunk_text):
            if cancel_event and cancel_event.is_set():
                return ""
            try:
                return ai.generate_quiz(chunk_text, num_questions=num_questions, difficulty=difficulty, question_type=question_type)
            except Exception as e:
                logger.error(f"❌ Worker failed to generate quiz for chunk: {e}")
                return ""

        with ThreadPoolExecutor(max_workers=min(len(chunks), 3)) as executor:
            raw_results = list(executor.map(generate_single_chunk, chunks))

        if cancel_event and cancel_event.is_set():
            return None

        raw_content = "\n\n".join([r for r in raw_results if r.strip()])
        if not raw_content.strip():
            if cancel_event and cancel_event.is_set():
                return None
            raw_content = ai.generate_quiz(full_content, num_questions=num_questions, difficulty=difficulty, question_type=question_type)

        if cancel_event and cancel_event.is_set():
            return None

        # 3. Enhance quiz with MODEL_BRAIN for university-level exam quality
        if progress_callback:
            progress_callback("enhancing_quiz", 70, f"🎯 MODEL_BRAIN đang tối ưu hóa phương án nhiễu & bẫy tư duy ({num_questions} câu)...")

        try:
            enhanced_content = ai.enhance_quiz(raw_content, full_content, num_questions=num_questions, difficulty=difficulty, question_type=question_type)
            if enhanced_content and enhanced_content.strip():
                raw_content = enhanced_content
        except Exception as e:
            logger.error(f"❌ Failed to enhance quiz with MODEL_BRAIN: {e}")

        if cancel_event and cancel_event.is_set():
            return None

        # 4. Standardize KaTeX / LaTeX math formatting using MODEL_WORKER
        if progress_callback:
            progress_callback("reviewing_latex", 88, "📐 MODEL_WORKER đang rà soát KaTeX & định dạng công thức toán...")

        try:
            final_latex_content = ai.review_latex_quiz(raw_content)
        except Exception as e:
            logger.error(f"❌ Failed in MODEL_WORKER LaTeX review step: {e}")
            final_latex_content = raw_content

        if cancel_event and cancel_event.is_set():
            return None

        # 5. Parse into structured Dict format
        if progress_callback:
            progress_callback("parsing_quiz", 96, "✨ Đang đối chiếu cấu trúc câu hỏi hoàn tất...")

        questions = []
        is_valid_quiz = False

        import re
        import json

        match = re.search(r'\[\s*\{.*\}\s*\]', final_latex_content, re.DOTALL)
        if match:
            try:
                parsed_questions = json.loads(clean_json_string(match.group(0)))
                if isinstance(parsed_questions, list) and len(parsed_questions) > 0:
                    valid_items = []
                    for idx, q in enumerate(parsed_questions, 1):
                        if isinstance(q, dict) and ("q" in q or "question" in q) and "options" in q:
                            q["id"] = idx
                            valid_items.append(q)
                    if valid_items:
                        # Limit to requested num_questions if AI returned slightly more
                        questions = valid_items[:num_questions]
                        is_valid_quiz = True
            except Exception as e:
                logger.error(f"Failed to parse JSON quiz: {e}")

        if not is_valid_quiz:
            logger.error("No valid questions parsed from AI response")
            questions = [{
                "q": "Lỗi tạo câu hỏi trắc nghiệm",
                "options": ["A. Lỗi phân tích cú pháp AI"],
                "correct": 0,
                "explanation": "Không thể phân tích mảng câu hỏi JSON hợp lệ từ phản hồi AI. Vui lòng tải lại bài học."
            }]

        result = {
            "id": topic_id,
            "title": note_title,
            "url": note_url,
            "num_questions": len(questions),
            "difficulty": difficulty,
            "question_type": question_type,
            "questions": questions
        }

        # Try saving to cache only if questions are valid (never poison cache with dummy error)
        if is_valid_quiz:
            try:
                r = r or get_redis()
                if r:
                    r.set(cache_key, json.dumps(result), ex=CACHE_QUIZ_TTL)
                    logger.info(f"Saved quiz to cache for topic {topic_id} ({cache_key})")
            except Exception as e:
                logger.warning(f"Redis cache save failed: {e}")

        return result

    finally:
        # Guarantee release of the generation lock
        if lock_acquired:
            try:
                r = r or get_redis()
                if r:
                    r.eval(
                        "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
                        1, lock_key, lock_token
                    )
            except Exception as e:
                logger.warning(f"Failed to release quiz lock: {e}")

def generate_quiz_stream(topic_id, force_refresh=False, num_questions=15, difficulty='medium', question_type='balanced', cancel_event=None):
    """Generate quiz with progress callbacks and yield progress updates as JSON lines."""
    import queue
    import threading
    import json

    q = queue.Queue()

    def callback(status, percentage, details):
        if cancel_event and cancel_event.is_set():
            return
        q.put({
            "type": "progress",
            "status": status,
            "percentage": percentage,
            "details": details
        })

    def worker():
        try:
            res = generate_quiz(
                topic_id,
                force_refresh=force_refresh,
                num_questions=num_questions,
                difficulty=difficulty,
                question_type=question_type,
                progress_callback=callback,
                cancel_event=cancel_event
            )
            if cancel_event and cancel_event.is_set():
                return
            if res:
                q.put({"type": "result", "data": res})
            else:
                q.put({"type": "error", "message": "Nội dung bài học trống hoặc không tìm thấy trang Notion."})
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                return
            q.put({"type": "error", "message": str(e)})

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    while True:
        if cancel_event and cancel_event.is_set():
            break
        try:
            item = q.get(timeout=0.1)
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item["type"] in ["result", "error"]:
                break
        except queue.Empty:
            continue

def generate_batch_quiz_stream(topics_config: list[dict], max_workers: int = 3, cancel_event=None):
    """Generate quizzes for multiple topics in batch with progress callbacks and yield stream events as JSON lines.
    Each item in topics_config: {
        'topic_id': str,
        'title': str (optional),
        'force_refresh': bool (default False),
        'num_questions': int (default 15),
        'difficulty': str (default 'medium'),
        'question_type': str (default 'balanced')
    }
    """
    import queue
    import threading
    import json
    from concurrent.futures import ThreadPoolExecutor

    q = queue.Queue()
    total_topics = len(topics_config)
    completed_topics = 0
    results_map = {}
    lock = threading.Lock()

    def topic_callback(topic_id, status, percentage, details):
        if cancel_event and cancel_event.is_set():
            return
        q.put({
            "type": "topic_progress",
            "topic_id": topic_id,
            "status": status,
            "percentage": percentage,
            "details": details
        })

    def process_single_topic(cfg):
        nonlocal completed_topics
        if cancel_event and cancel_event.is_set():
            return

        t_id = cfg["topic_id"]
        force_ref = cfg.get("force_refresh", False)
        num_q = cfg.get("num_questions", 15)
        diff = cfg.get("difficulty", "medium")
        q_type = cfg.get("question_type", "balanced")
        title = cfg.get("title", "")

        def cb(status, percentage, details):
            topic_callback(t_id, status, percentage, details)

        try:
            quiz = generate_quiz(
                t_id,
                force_refresh=force_ref,
                num_questions=num_q,
                difficulty=diff,
                question_type=q_type,
                progress_callback=cb,
                cancel_event=cancel_event
            )
            if cancel_event and cancel_event.is_set():
                return

            with lock:
                completed_topics += 1
                current_completed = completed_topics
                results_map[t_id] = {
                    "success": bool(quiz and quiz.get("questions")),
                    "quiz": quiz,
                    "error": None if (quiz and quiz.get("questions")) else "Không thể tạo câu hỏi hoặc nội dung rỗng"
                }

            q.put({
                "type": "topic_completed",
                "topic_id": t_id,
                "title": title or (quiz.get("title") if quiz else ""),
                "num_questions": len(quiz.get("questions", [])) if quiz else 0,
                "completed_count": current_completed,
                "total_count": total_topics,
                "percentage": int((current_completed / total_topics) * 100),
                "success": bool(quiz and quiz.get("questions"))
            })
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                return
            logger.error(f"❌ Batch generation failed for topic {t_id}: {e}")
            with lock:
                completed_topics += 1
                current_completed = completed_topics
                results_map[t_id] = {
                    "success": False,
                    "quiz": None,
                    "error": str(e)
                }
            q.put({
                "type": "topic_completed",
                "topic_id": t_id,
                "title": title,
                "num_questions": 0,
                "completed_count": current_completed,
                "total_count": total_topics,
                "percentage": int((current_completed / total_topics) * 100),
                "success": False,
                "error": str(e)
            })

    def worker():
        try:
            q.put({
                "type": "batch_started",
                "total_topics": total_topics,
                "message": f"🚀 Bắt đầu tạo trắc nghiệm hàng loạt cho {total_topics} chủ đề..."
            })
            with ThreadPoolExecutor(max_workers=min(max_workers, total_topics or 1)) as executor:
                list(executor.map(process_single_topic, topics_config))

            if cancel_event and cancel_event.is_set():
                return

            q.put({
                "type": "batch_finished",
                "total_topics": total_topics,
                "successful_topics": sum(1 for v in results_map.values() if v["success"]),
                "results": results_map
            })
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                return
            logger.error(f"❌ Batch generation worker exception: {e}")
            q.put({"type": "error", "message": str(e)})

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    while True:
        if cancel_event and cancel_event.is_set():
            break
        try:
            item = q.get(timeout=0.1)
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item["type"] in ["batch_finished", "error"]:
                break
        except queue.Empty:
            continue

def update_status(topic_id, status=None):
    """Update 'Last Review At' and possibly status in Notion."""
    notion = NotionService()

    try:
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now_iso = datetime.datetime.now(vn_tz).isoformat()

        logger.info(f"🗓 Updating Last Review At to: {now_iso}")
        notion.update_page_property(topic_id, "Last Review At", now_iso, type_key="date")

        # If status is provided, we might want to update it too
        if status:
             status_map = {
                 "da_nam_vung": "🟢 Đã nắm vững",
                 "chua_nam_vung": "🔴 Cần xem lại"
             }
             if status in status_map:
                 logger.info(f"🏷 Updating Độ hiểu bài to: {status_map[status]}")
                 notion.update_page_property(topic_id, "Độ hiểu bài", status_map[status], type_key="select")

        # Clear candidates list cache in Redis since database changed
        try:
            r = get_redis()
            if r:
                for k in r.scan_iter("study_candidates*"):
                    r.delete(k)
                logger.info("Cleared study_candidates* cache due to status update")
        except Exception as e:
            logger.warning(f"Failed to clear study_candidates cache: {e}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to update Last Review At: {e}")
        return False

def generate_quick_review(course=None):
    """Fetch all candidate topics (optionally filtered by course), generate/fetch their quizzes in parallel, and combine them."""
    candidates = get_candidates()
    if not candidates:
        return None

    if course and course.strip():
        c_filter = course.strip().lower()
        candidates = [c for c in candidates if c.get("course") and c.get("course").strip().lower() == c_filter]
        if not candidates:
            return None

    from concurrent.futures import ThreadPoolExecutor
    import random

    def fetch_topic_quiz(topic):
        try:
            quiz = generate_quiz(topic["id"])
            if quiz and quiz.get("questions"):
                # Tag each question with its source topic title and ID for context
                for q in quiz["questions"]:
                    q["topic_title"] = topic["title"]
                    q["topic_id"] = topic["id"]
                return quiz["questions"]
        except Exception as e:
            logger.error(f"Error fetching quiz for topic {topic['id']}: {e}")
        return []

    all_questions = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_topic_quiz, candidates)
        for questions in results:
            all_questions.extend(questions)

    if not all_questions:
        return None

    # Shuffle all combined questions
    random.shuffle(all_questions)

    title = f"Ôn tập nhanh - {course.strip()}" if course and course.strip() else "Ôn tập tổng hợp"

    return {
        "id": "quick_review",
        "title": title,
        "questions": all_questions
    }


def save_quiz_progress(telegram_id: str | int, progress_data: dict, topic_id: str | None = None) -> bool:
    """Save quiz progress for a user and topic into Redis."""
    r = get_redis()
    if not r:
        return False
    try:
        tid = topic_id
        if not tid and isinstance(progress_data, dict):
            topic_obj = progress_data.get("topic")
            if isinstance(topic_obj, dict):
                tid = topic_obj.get("id")
        if not tid:
            tid = "default"
        cache_key = f"quiz_progress_{telegram_id}:{tid}"
        r.setex(cache_key, CACHE_QUIZ_PROGRESS_TTL, json.dumps(progress_data, ensure_ascii=False))
        return True
    except Exception as e:
        logger.warning(f"Failed to save quiz progress for user {telegram_id}, topic {topic_id}: {e}")
        return False


def get_quiz_progress(telegram_id: str | int, topic_id: str | None = None) -> dict | None:
    """Retrieve quiz progress for a user from Redis.
    If topic_id is provided, returns that topic's progress dict.
    If topic_id is None, returns a dict of all in-progress topics: {topic_id: progress_data}
    """
    r = get_redis()
    if not r:
        return None
    try:
        if topic_id:
            cache_key = f"quiz_progress_{telegram_id}:{topic_id}"
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
            # Fallback to old format key quiz_progress_{telegram_id}
            old_cached = r.get(f"quiz_progress_{telegram_id}")
            if old_cached:
                try:
                    data = json.loads(old_cached)
                    if isinstance(data, dict) and data.get("topic", {}).get("id") == topic_id:
                        return data
                except Exception:
                    pass
            return None
        else:
            result = {}
            pattern = f"quiz_progress_{telegram_id}:*"
            for k in r.scan_iter(pattern):
                key_str = k if isinstance(k, str) else k.decode('utf-8')
                val = r.get(key_str)
                if val:
                    try:
                        pdata = json.loads(val)
                        tid = key_str.split(":", 1)[1]
                        result[tid] = pdata
                    except Exception:
                        pass
            # Also check old key format if any
            old_cached = r.get(f"quiz_progress_{telegram_id}")
            if old_cached:
                try:
                    pdata = json.loads(old_cached)
                    old_tid = pdata.get("topic", {}).get("id") if isinstance(pdata, dict) else None
                    if old_tid and old_tid not in result:
                        result[old_tid] = pdata
                except Exception:
                    pass
            return result if result else None
    except Exception as e:
        logger.warning(f"Failed to get quiz progress for user {telegram_id}: {e}")
    return None


def clear_quiz_progress(telegram_id: str | int, topic_id: str | None = None) -> bool:
    """Delete quiz progress for a user and topic in Redis.
    If topic_id is None, deletes all progress for this user.
    """
    r = get_redis()
    if not r:
        return False
    try:
        if topic_id:
            r.delete(f"quiz_progress_{telegram_id}:{topic_id}")
            # Also clean old key if matched
            old_cached = r.get(f"quiz_progress_{telegram_id}")
            if old_cached:
                try:
                    pdata = json.loads(old_cached)
                    if isinstance(pdata, dict) and pdata.get("topic", {}).get("id") == topic_id:
                        r.delete(f"quiz_progress_{telegram_id}")
                except Exception:
                    pass
            return True
        else:
            pattern = f"quiz_progress_{telegram_id}:*"
            keys = list(r.scan_iter(pattern))
            if keys:
                r.delete(*keys)
            r.delete(f"quiz_progress_{telegram_id}")
            return True
    except Exception as e:
        logger.warning(f"Failed to clear quiz progress for user {telegram_id}: {e}")
        return False

