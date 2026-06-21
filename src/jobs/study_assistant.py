import time
import random
import sys
import os
import re

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.services.notion import NotionService
from src.services.ai import AIService
from src.services.telegram import TelegramService
from src.utils.logger import logger

def run_study_assistant(topic_id=None):
    logger.info("🎓 Starting Study Assistant Job...")

    # Initialize Services
    notion = NotionService()
    ai = AIService()
    telegram = TelegramService()

    if topic_id:
        logger.info(f"🎯 Explicit topic_id provided: {topic_id}")
        telegram.send_message("⏳ Đang đọc nội dung bài học từ Notion...", disable_notification=True)

        # 1. Fetch content specifically for this topic
        content_lines = notion.fetch_page_content(topic_id)
        full_content = "\n".join(content_lines)

        if not full_content.strip():
            logger.warning("⚠️ Note content is empty.")
            telegram.send_message("⚠️ Nội dung bài học này đang trống!")
            return

        # Default info if we can't fetch metadata easily
        note_id = topic_id
        note_url = f"https://notion.so/{topic_id.replace('-', '')}"
        note_title = "Bài học đã chọn"

        # Try to fetch actual title
        try:
            page_info = notion.client.pages.retrieve(page_id=topic_id)
            if page_info.get("url"):
                note_url = page_info["url"]
            props = page_info.get("properties", {})

            # Look for the title property (it might be named differently, assume 'Tên bài học' or 'Name')
            title_prop = None
            for key, val in props.items():
                if val.get("type") == "title":
                    title_prop = val["title"]
                    break

            if title_prop and len(title_prop) > 0:
                note_title = title_prop[0]["plain_text"]
        except Exception as e:
            logger.warning(f"Could not fetch full page info for title: {e}")

        logger.info(f"🎯 Selected Note: {note_title}")

    else:
        # 1. Fetch Candidates (Assume this returns raw page objects)
        candidates = notion.get_review_notes()

        if not candidates:
            logger.info("🎉 No review notes found today.")
            telegram.send_message("🎉 Hôm nay không có bài nào cần ôn tập!")
            return

        # 2. Select Note based on Spaced Repetition (Oldest "Last Review At" first)
        def get_last_review_sort_key(note):
            # We want to sort ascending.
            # Priority 1: No "Last Review At" (None or Empty) -> Treat as "" to sort first.
            # Priority 2: Oldest "Last Review At" -> "2023..." comes before "2025..."
            try:
                props = note.get("properties", {})
                last_review = props.get("Last Review At", {}).get("date", {})
                if last_review and last_review.get("start"):
                     return last_review["start"]
            except:
                pass
            return "" # Empty string sorts before any ISO date string

        # Sort candidates
        candidates.sort(key=get_last_review_sort_key)

        # Take Top 5 candidates for the user to choose
        top_candidates = candidates[:5]

        buttons = []
        for c in top_candidates:
            c_id = c["id"]
            title = "Unknown Note"
            # Try to extract title dynamically
            for key, val in c.get("properties", {}).items():
                if val.get("type") == "title" and val["title"]:
                    title = val["title"][0]["plain_text"]
                    break

            # Telegram callback_data limit is 64 bytes. UUID without hyphens is 32 bytes.
            short_id = c_id.replace("-", "")
            buttons.append([{"text": title, "callback_data": f"/study_{short_id}"}])

        reply_markup = {"inline_keyboard": buttons}

        msg = "📚 **Dưới đây là các bài học cần ôn tập:**\n\nBạn muốn làm trắc nghiệm bài nào?"
        telegram.send_message(msg, parse_mode="Markdown", reply_markup=reply_markup)
        logger.info("Sent topic selection to Telegram.")
        return # Stop execution here, wait for user click

    # 4. Generate Quiz
    logger.info("🧠 Generating Quiz...")
    telegram.send_message("🧠 Đang dùng AI biên soạn câu hỏi trắc nghiệm...", disable_notification=True)

    quiz_content = ai.generate_quiz(full_content)

    # 5. Send to Telegram (Consolidated)
    logger.info("📨 Sending to Telegram...")
    
    # buffers for message accumulation
    message_parts = []
    
    # Header
    header_msg = f"""
🎯 <b>GÓC ÔN TẬP KHẮC SÂU (Spaced Repetition)</b>
Bài: <a href="{note_url}">{note_title}</a>
Trạng thái: 🔴 Cần xem lại
"""
    message_parts.append(header_msg)

    # Content
    raw_chunks = quiz_content.split("🎯")
    
    for chunk in raw_chunks:
        clean = chunk.strip()
        if not clean: continue
        
        # Split Question and Answer to ensure Spoiler works and LaTeX doesn't break Markdown
        q_text = ""
        ans_text = ""
        
        # Try splitting by "👉" first (visual separator)
        if "👉" in clean:
             parts = clean.split("👉", 1)
             q_text = f"🎯 {parts[0].strip()}"
             ans_text = f"👉 {parts[1].strip()}"
        
        # Fallback: Try splitting by <tg-spoiler> if 👉 is missing but spoiler exists
        elif "<tg-spoiler>" in clean:
             parts = clean.split("<tg-spoiler>", 1)
             q_text = f"🎯 {parts[0].strip()}"
             ans_text = f"<tg-spoiler>{parts[1].strip()}"
        
        else:
             # valid plain text content
             q_text = f"🎯 {clean}"
             
        # Add Question
        message_parts.append(q_text)
        
        # Add Answer if exists
        if ans_text:
            message_parts.append(ans_text)

    # Footer
    footer = """
---
👉 <i>Bấm vào link bài học để tự sửa trạng thái thành 🟢 Đã nắm vững nếu bạn trả lời đúng hết nhé!</i>
"""
    message_parts.append(footer)
    
    # Combine and Send
    current_buffer = ""
    MAX_LENGTH = 4096

    for part in message_parts:
        # Check if adding this part would exceed the limit
        # Adding 2 for "\n\n" separator
        if len(current_buffer) + len(part) + 2 > MAX_LENGTH:
            # Send current buffer
            if current_buffer:
                telegram.send_message(current_buffer, parse_mode="HTML", disable_notification=True)
                time.sleep(1) # Rate limit friendly
            
            # Start new buffer with current part
            current_buffer = part
        else:
            if current_buffer:
                current_buffer += "\n\n" + part
            else:
                current_buffer = part
    
    # Send remaining buffer
    if current_buffer:
         telegram.send_message(current_buffer, parse_mode="HTML", disable_notification=True)
    
    # 6. Update "Last Review At"
    try:
        import datetime
        import pytz
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now_iso = datetime.datetime.now(vn_tz).isoformat()
        
        logger.info(f"🗓 Updating Last Review At to: {now_iso}")
        notion.update_page_property(note_id, "Last Review At", now_iso, type_key="date")
        
    except Exception as e:
        logger.error(f"❌ Failed to update Last Review At: {e}")

    logger.info("🏁 Study Job Completed!")

if __name__ == "__main__":
    run_study_assistant()
