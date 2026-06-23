import datetime
import pytz
from src.services.notion import NotionService
from src.services.ai import AIService
from src.utils.logger import logger

def get_candidates():
    """Fetch review notes, sort by 'Last Review At', return top 5 with id and title."""
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
    for c in top_candidates:
        c_id = c["id"]
        title = "Unknown Note"
        for key, val in c.get("properties", {}).items():
            if val.get("type") == "title" and val["title"]:
                title = val["title"][0]["plain_text"]
                break
        results.append({"id": c_id, "title": title})
        
    return results

def generate_quiz(topic_id):
    """Fetch content from Notion, call AI to generate quiz, parse into JSON/Dict format."""
    notion = NotionService()
    ai = AIService()
    
    import re
    import json
    import redis

    # Try checking cache first
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
             # Map status if necessary (e.g. from mastered/review to actual Notion status)
             pass
             
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update Last Review At: {e}")
        return False
