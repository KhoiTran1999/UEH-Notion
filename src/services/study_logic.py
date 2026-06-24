import datetime
import pytz
from src.services.notion import NotionService
from src.services.ai import AIService
from src.utils.logger import logger

def get_page_title(page_id):
    """Retrieve title of a page by ID, using Redis cache if available."""
    import redis
    import httpx
    from src.config.settings import Config
    from src.services.notion import NotionService

    cache_key = f"page_title_{page_id}"
    r = None
    try:
        if Config.REDIS_URL:
            r = redis.from_url(Config.REDIS_URL)
            cached = r.get(cache_key)
            if cached:
                return cached.decode('utf-8')
    except Exception as e:
        logger.warning(f"Redis get error for {cache_key}: {e}")

    notion = NotionService()
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=notion.headers)
            if resp.status_code == 200:
                props = resp.json().get("properties", {})
                for key, val in props.items():
                    if val.get("type") == "title" and val["title"]:
                        title = val["title"][0]["plain_text"]
                        if r:
                            try:
                                r.setex(cache_key, 2592000, title)
                            except Exception as ce:
                                logger.warning(f"Redis set error: {ce}")
                        return title
    except Exception as e:
        logger.error(f"Error fetching page title for {page_id}: {e}")

    return None

def get_candidates(force_refresh=False):
    """Fetch review notes, sort by 'Last Review At', return top 5 with metadata."""
    import redis
    import json
    from src.config.settings import Config

    cache_key = "study_candidates"
    r = None
    if not force_refresh:
        try:
            if Config.REDIS_URL:
                r = redis.from_url(Config.REDIS_URL)
                cached = r.get(cache_key)
                if cached:
                    logger.info("Using cached study candidates list")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis get candidates cache error: {e}")

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
    top_candidates = candidates[:5]

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
            if not r and Config.REDIS_URL:
                r = redis.from_url(Config.REDIS_URL)
            if r:
                r.setex(cache_key, 86400, json.dumps(results)) # Cache for 24 hours
                logger.info("Saved study candidates list to cache")
        except Exception as e:
            logger.warning(f"Redis set candidates cache error: {e}")

    return results

def replace_currency_dollars(text):
    """Replace standalone currency $ signs (e.g. $50 or 50$) with 'USD ' or ' USD' to prevent KaTeX rendering issues."""
    parts = list(text)
    n = len(parts)
    i = 0
    while i < n:
        if parts[i] == '$':
            is_escaped = False
            if i > 0 and parts[i-1] == '\\':
                bs_count = 0
                k = i - 1
                while k >= 0 and parts[k] == '\\':
                    bs_count += 1
                    k -= 1
                if bs_count % 2 == 1:
                    is_escaped = True

            if is_escaped:
                i += 1
                continue

            next_dollar_idx = -1
            j = i + 1
            while j < n:
                if parts[j] == '$':
                    next_is_escaped = False
                    if parts[j-1] == '\\':
                        bs_count = 0
                        k = j - 1
                        while k >= 0 and parts[k] == '\\':
                            bs_count += 1
                            k -= 1
                        if bs_count % 2 == 1:
                            next_is_escaped = True
                    if not next_is_escaped:
                        next_dollar_idx = j
                        break
                j += 1

            if next_dollar_idx == -1:
                if i + 1 < n and parts[i+1].isdigit():
                    parts[i] = 'USD '
                else:
                    parts[i] = ' USD'
                i += 1
                continue

            math_content = "".join(parts[i+1:next_dollar_idx])

            is_math = True
            if '\n' in math_content:
                is_math = False
            elif len(math_content) > 100:
                is_math = False
            else:
                has_math_chars = any(c in math_content for c in ['\\', '_', '^', '=', '+', '*', '/', '{', '}'])
                if math_content.count(' ') > 3 and not has_math_chars:
                    is_math = False

            if not is_math:
                if i + 1 < n and parts[i+1].isdigit():
                    parts[i] = 'USD '
                else:
                    parts[i] = ' USD'
                i += 1
            else:
                i = next_dollar_idx + 1
        else:
            i += 1

    return "".join(parts)

def clean_json_string(json_str):
    """Clean unescaped LaTeX backslashes and invalid escape sequences inside JSON string literals."""
    import re
    pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
    def replace_string(match):
        s = match.group(0)
        content = s[1:-1]
        content = replace_currency_dollars(content)
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
                is_double = False
                if i + 1 < n and content[i+1] == '\\':
                    is_double = True

                if in_math:
                    if is_double:
                        if i + 2 < n and content[i+2].isalpha():
                            fixed.append('\\\\')
                            i += 2
                        else:
                            fixed.append('\\\\\\\\')
                            i += 2
                    else:
                        if i + 1 < n and content[i+1].isalpha():
                            fixed.append('\\\\')
                            i += 1
                        else:
                            fixed.append('\\\\\\\\')
                            i += 1
                else:
                    if is_double:
                        fixed.append('\\\\')
                        i += 2
                    else:
                        next_char = content[i+1] if i + 1 < n else ''
                        if next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't']:
                            fixed.append('\\')
                            fixed.append(next_char)
                            i += 2
                        elif next_char == 'u':
                            if i + 5 < n and all(c in '0123456789abcdefABCDEF' for c in content[i+2:i+6]):
                                fixed.append('\\')
                                fixed.append('u')
                                fixed.extend(content[i+2:i+6])
                                i += 6
                            else:
                                fixed.append('\\\\')
                                fixed.append('u')
                                i += 2
                        else:
                            fixed.append('\\\\')
                            i += 1
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
    import redis

    # Try checking cache first
    if progress_callback:
        progress_callback("checking_cache", 5, "🔍 Đang kiểm tra bộ nhớ đệm...")

    if not force_refresh:
        try:
            from src.config.settings import Config
            redis_url = Config.REDIS_URL
            if redis_url:
                r = redis.from_url(redis_url)
                cache_key = f"quiz_{topic_id}"
                cached = r.get(cache_key)
                if cached:
                    logger.info(f"Using cached quiz for topic {topic_id}")
                    if progress_callback:
                        progress_callback("parsing_quiz", 100, "✨ Đã tải trắc nghiệm thành công!")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")

    # 1. Fetch content
    content_lines = notion.fetch_page_content(topic_id, progress_callback=progress_callback)
    full_content = "\n".join(content_lines)

    if not full_content.strip():
        return None

    # Default info
    note_url = f"https://notion.so/{topic_id.replace('-', '')}"
    note_title = "Bài học đã chọn"

    if progress_callback:
        progress_callback("page_info", 40, "📖 Đang đồng bộ thông tin tiêu đề...")

    try:
        page_info = notion.retrieve_page(topic_id)
        if page_info and page_info.get("url"):
            note_url = page_info["url"]
        props = page_info.get("properties", {}) if page_info else {}

        for key, val in props.items():
            if val.get("type") == "title" and val["title"]:
                note_title = val["title"][0]["plain_text"]
                break
    except Exception as e:
        logger.warning(f"Could not fetch full page info for title: {e}")

    # 2. Call AI
    if progress_callback:
        progress_callback("calling_ai", 45, "🧠 Đang gửi nội dung bài học tới AI...")

    raw_content = ai.generate_quiz(full_content)

    # 3. Parse into structured Dict format
    if progress_callback:
        progress_callback("parsing_quiz", 95, "✨ Đang kiểm tra cấu trúc câu hỏi...")

    questions = []

    import re
    import json

    match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
    if match:
        try:
            questions = json.loads(clean_json_string(match.group(0)))
        except Exception as e:
            logger.error(f"Failed to parse JSON quiz: {e}")
            questions = [{
                "q": "Error generating quiz",
                "options": ["A. Error"],
                "correct": 0,
                "explanation": "Could not parse AI response"
            }]
    else:
        logger.error("No JSON array found in AI response")
        questions = [{
            "q": "Error generating quiz",
            "options": ["A. Error"],
            "correct": 0,
            "explanation": "No JSON array found in AI response"
        }]

    result = {
        "id": topic_id,
        "title": note_title,
        "url": note_url,
        "questions": questions
    }

    # Try saving to cache
    try:
        from src.config.settings import Config
        redis_url = Config.REDIS_URL
        if redis_url:
            r = redis.from_url(redis_url)
            cache_key = f"quiz_{topic_id}"
            r.setex(cache_key, 1209600, json.dumps(result))
            logger.info(f"Saved quiz to cache for topic {topic_id}")
    except Exception as e:
        logger.warning(f"Redis cache save failed: {e}")

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
                 "chua_nam_vung": "🔴 Chưa nắm vững"
             }
             if status in status_map:
                 logger.info(f"🏷 Updating Độ hiểu bài to: {status_map[status]}")
                 notion.update_page_property(topic_id, "Độ hiểu bài", status_map[status], type_key="select")

        # Clear candidates list cache in Redis since database changed
        try:
            if Config.REDIS_URL:
                r = redis.from_url(Config.REDIS_URL)
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
