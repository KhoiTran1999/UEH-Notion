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

def get_candidates():
    """Fetch review notes, sort by 'Last Review At', return top 5 with metadata."""
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

    return results

def generate_quiz(topic_id, force_refresh=False):
    """Fetch content from Notion, call AI to generate quiz, parse into JSON/Dict format."""
    notion = NotionService()
    ai = AIService()

    import re
    import json
    import redis

    # Try checking cache first
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
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")

    # 1. Fetch content
    content_lines = notion.fetch_page_content(topic_id)
    full_content = "\n".join(content_lines)
    
    if not full_content.strip():
        return None
        
    # Default info
    note_url = f"https://notion.so/{topic_id.replace('-', '')}"
    note_title = "Bài học đã chọn"
    
    try:
        page_info = notion.client.pages.retrieve(page_id=topic_id)
        if page_info.get("url"):
            note_url = page_info["url"]
        props = page_info.get("properties", {})
        
        for key, val in props.items():
            if val.get("type") == "title" and val["title"]:
                note_title = val["title"][0]["plain_text"]
                break
    except Exception as e:
        logger.warning(f"Could not fetch full page info for title: {e}")
        
    # 2. Call AI
    raw_content = ai.generate_quiz(full_content)
    
    # 3. Parse into structured Dict format
    questions = []

    import re
    import json

    match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
    if match:
        try:
            questions = json.loads(match.group(0))
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
