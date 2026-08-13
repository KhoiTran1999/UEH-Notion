import datetime
import json
import pytz
import uuid
from src.services.notion import NotionService
from src.services.ai import AIService
from src.utils.logger import logger
from src.utils.cache import (
    get_redis,
    CACHE_PAGE_TITLE_TTL,
    CACHE_CANDIDATES_TTL,
    CACHE_QUIZ_TTL,
    LOCK_QUIZ_TTL,
)

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
        if page_info:
            props = page_info.get("properties", {})
            for key, val in props.items():
                if val.get("type") == "title" and val["title"]:
                    title = val["title"][0]["plain_text"]
                    if r:
                        try:
                            r.setex(cache_key, CACHE_PAGE_TITLE_TTL, title)
                        except Exception as ce:
                            logger.warning(f"Redis set error: {ce}")
                    return title
    except Exception as e:
        logger.error(f"Error fetching page title for {page_id}: {e}")

    return None

def get_candidates(limit=5, force_refresh=False):
    """Fetch review notes, sort by 'Last Review At', return top candidates with metadata."""
    cache_key = f"study_candidates_{limit}"
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
            props = note.get("properties", {})
            last_review = props.get("Last Review At", {}).get("date", {})
            if last_review and last_review.get("start"):
                 return last_review["start"]
        except:
            pass
        return ""

    candidates.sort(key=get_last_review_sort_key)
    top_candidates = candidates[:limit]

    results = []
    relation_tasks = [] # list of (idx, prop_name, page_id)

    for idx, c in enumerate(top_candidates):
        c_id = c["id"]
        title = "Unknown Note"
        props = c.get("properties", {})

        for key, val in props.items():
            if val.get("type") == "title" and val["title"]:
                title = val["title"][0]["plain_text"]
                break

        chapter_id = None
        course_id = None

        chapter_prop = props.get("📍DB Chương", {})
        if chapter_prop.get("type") == "relation" and chapter_prop.get("relation"):
            chapter_id = chapter_prop["relation"][0]["id"]

        course_prop = props.get("🔹 DB Học Phần - UEH", {})
        if course_prop.get("type") == "relation" and course_prop.get("relation"):
            course_id = course_prop["relation"][0]["id"]

        results.append({
            "id": c_id,
            "title": title,
            "chapter": None,
            "course": None
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

def generate_quiz(topic_id, force_refresh=False, progress_callback=None):
    """Fetch content from Notion, call AI to generate quiz, parse into JSON/Dict format."""
    notion = NotionService()
    ai = AIService()

    import re
    import json

    # Try checking cache first
    if progress_callback:
        progress_callback("checking_cache", 5, "🔍 Đang kiểm tra bộ nhớ đệm...")

    r = None
    if not force_refresh:
        try:
            r = get_redis()
            if r:
                cache_key = f"quiz_{topic_id}"
                cached = r.get(cache_key)
                if cached:
                    logger.info(f"Using cached quiz for topic {topic_id}")
                    if progress_callback:
                        progress_callback("parsing_quiz", 100, "✨ Đã tải trắc nghiệm thành công!")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")
    else:
        try:
            r = get_redis()
            if r:
                r.delete(f"quiz_{topic_id}")
                logger.info(f"Cleared quiz cache for topic {topic_id} due to force refresh")
        except Exception as e:
            logger.warning(f"Redis cache delete failed: {e}")

    # Acquire Redis lock to prevent concurrent generation for same topic
    lock_key = f"quiz_lock_{topic_id}"
    lock_token = str(uuid.uuid4())
    lock_acquired = False
    try:
        r = r or get_redis()
        if r:
            lock_acquired = r.set(lock_key, lock_token, nx=True, ex=LOCK_QUIZ_TTL)
            if not lock_acquired:
                logger.info(f"⏳ Quiz generation already in progress for {topic_id}, waiting...")
                if progress_callback:
                    progress_callback("checking_cache", 10, "⏳ Đợi lượt tạo câu hỏi trước đó...")
                # Poll until lock released or timeout
                import time as time_mod
                waited = 0
                while waited < 30:
                    time_mod.sleep(2)
                    waited += 2
                    cached = r.get(f"quiz_{topic_id}")
                    if cached:
                        logger.info(f"✅ Found cached quiz after waiting for {topic_id}")
                        if progress_callback:
                            progress_callback("parsing_quiz", 100, "✨ Đã tải trắc nghiệm thành công!")
                        return json.loads(cached)
                    if not r.get(lock_key):
                        break
                lock_acquired = r.set(lock_key, lock_token, nx=True, ex=LOCK_QUIZ_TTL)
    except Exception as e:
        logger.warning(f"Redis lock acquire failed (non-fatal): {e}")

    # 1. Fetch content
    content_lines = notion.fetch_page_content(topic_id, progress_callback=progress_callback)
    # Pre-clean markdown input before sending to AI to strip math-breaking formatting like $*V*$ or raw currency $
    cleaned_lines = []
    import re
    for line in content_lines:
        # Strip Markdown italic/bold tags surrounding LaTeX math dollars like $*V*$ or $**V**$
        l = re.sub(r'\$\*+(.*?)\*+\$', r'$\1$', line)
        cleaned_lines.append(l)
    full_content = "\n".join(cleaned_lines)

    if not full_content.strip():
        return None

    # Default info
    note_url = f"https://notion.so/{topic_id.replace('-', '')}"
    note_title = "Bài học đã chọn"

    if progress_callback:
        progress_callback("page_info", 40, "📖 Đang đồng bộ thông tin tiêu đề...")

    cached_title = get_page_title(topic_id)
    if cached_title:
        note_title = cached_title

    # 2. Call AI in 3 parallel chunks
    if progress_callback:
        progress_callback("calling_ai", 45, "🧠 Đang chia 3 phần bài học và gửi AI xử lý song song...")

    chunks = split_into_3_chunks(full_content)
    from concurrent.futures import ThreadPoolExecutor

    def generate_single_chunk(chunk_text):
        try:
            return ai.generate_quiz(chunk_text)
        except Exception as e:
            logger.error(f"❌ Worker failed to generate quiz for chunk: {e}")
            return ""

    with ThreadPoolExecutor(max_workers=min(len(chunks), 3)) as executor:
        raw_results = list(executor.map(generate_single_chunk, chunks))

    raw_content = "\n\n".join([r for r in raw_results if r.strip()])
    if not raw_content.strip():
        raw_content = ai.generate_quiz(full_content)

    # 3. Review and self-correct quiz
    if progress_callback:
        progress_callback("reviewing_quiz", 75, "🔍 AI đang tự động đánh giá và chuẩn hóa câu hỏi...")

    try:
        reviewed_content = ai.review_quiz(raw_content, full_content)
    except Exception as e:
        logger.error(f"❌ Failed to review/self-correct quiz: {e}")
        reviewed_content = raw_content

    # 4. Final dedicated AI step to verify & correct KaTeX / LaTeX math formatting
    if progress_callback:
        progress_callback("reviewing_latex", 90, "📐 AI đang kiểm định và chuẩn hóa KaTeX toán học...")

    try:
        final_latex_content = ai.review_latex_quiz(reviewed_content)
    except Exception as e:
        logger.error(f"❌ Failed in final AI LaTeX review step: {e}")
        final_latex_content = reviewed_content

    # 5. Parse into structured Dict format
    if progress_callback:
        progress_callback("parsing_quiz", 95, "✨ Đang kiểm tra cấu trúc câu hỏi...")

    questions = []

    import re
    import json

    match = re.search(r'\[\s*\{.*\}\s*\]', final_latex_content, re.DOTALL)
    if match:
        try:
            questions = json.loads(clean_json_string(match.group(0)))
            for idx, q in enumerate(questions, 1):
                if isinstance(q, dict):
                    q["id"] = idx
        except Exception as e:
            logger.error(f"Failed to parse JSON quiz: {e}")
            questions = [{
                "q": "Lỗi tạo câu hỏi trắc nghiệm",
                "options": ["A. Lỗi hệ thống"],
                "correct": 0,
                "explanation": "Không thể phân tích cú pháp phản hồi từ AI"
            }]
    else:
        logger.error("No JSON array found in AI response")
        questions = [{
            "q": "Lỗi tạo câu hỏi trắc nghiệm",
            "options": ["A. Lỗi hệ thống"],
            "correct": 0,
            "explanation": "Không tìm thấy mảng JSON hợp lệ từ phản hồi AI"
        }]

    result = {
        "id": topic_id,
        "title": note_title,
        "url": note_url,
        "questions": questions
    }

    # Try saving to cache
    try:
        r = get_redis()
        if r:
            cache_key = f"quiz_{topic_id}"
            r.setex(cache_key, CACHE_QUIZ_TTL, json.dumps(result))
            logger.info(f"Saved quiz to cache for topic {topic_id}")
    except Exception as e:
        logger.warning(f"Redis cache save failed: {e}")

    # Release the generation lock
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

    return result

def generate_quiz_stream(topic_id, force_refresh=False):
    """Generate quiz with progress callbacks and yield progress updates as JSON lines."""
    import queue
    import threading
    import json

    q = queue.Queue()

    def callback(status, percentage, details):
        q.put({
            "type": "progress",
            "status": status,
            "percentage": percentage,
            "details": details
        })

    def worker():
        try:
            res = generate_quiz(topic_id, force_refresh=force_refresh, progress_callback=callback)
            if res:
                q.put({"type": "result", "data": res})
            else:
                q.put({"type": "error", "message": "Topic not found or content empty"})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    t = threading.Thread(target=worker)
    t.start()

    while True:
        item = q.get()
        yield json.dumps(item, ensure_ascii=False) + "\n"
        if item["type"] in ["result", "error"]:
            break

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
                r.delete("study_candidates")
                logger.info("Cleared study_candidates cache due to status update")
        except Exception as e:
            logger.warning(f"Failed to clear study_candidates cache: {e}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to update Last Review At: {e}")
        return False

def generate_quick_review():
    """Fetch all candidate topics, generate/fetch their quizzes in parallel, and combine them."""
    candidates = get_candidates()
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

    # Shuffle and pick up to 10 questions
    random.shuffle(all_questions)
    selected_questions = all_questions[:10]

    return {
        "id": "quick_review",
        "title": "Ôn tập tổng hợp",
        "questions": selected_questions
    }

