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

def run_study_assistant():
    logger.info("🎓 Starting Study Assistant Job...")

    # Initialize Services
    notion = NotionService()
    ai = AIService()
    telegram = TelegramService()

    # 1. Fetch Candidates (Assume this returns raw page objects)
    candidates = notion.get_review_notes()
    
    if not candidates:
        logger.info("🎉 No review notes found today.")
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
    
    # Select the top 1 (oldest or unreviewed)
    selected_note = candidates[0]
    
    note_id = selected_note["id"]
    note_url = selected_note["url"]
    
    note_title = "Unknown Note"
    if selected_note["properties"].get("Tên bài học", {}).get("title"):
        note_title = selected_note["properties"]["Tên bài học"]["title"][0]["plain_text"]
    
    logger.info(f"🎯 Selected Note: {note_title}")

    # 3. Deep Fetch Content
    content_lines = notion.fetch_page_content(note_id)
    full_content = "\n".join(content_lines)

    if not full_content.strip():
        logger.warning("⚠️ Note content is empty.")
        return

    # 4. Generate Quiz
    logger.info("🧠 Generating Quiz...")

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
