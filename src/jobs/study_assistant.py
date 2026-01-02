import time
import random
import sys
import os

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

    # 1. Fetch Candidates
    candidates = notion.get_review_notes()
    
    if not candidates:
        logger.info("🎉 No review notes found today.")
        return

    # 2. Select Note
    selected_note = random.choice(candidates)
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

    # 5. Send to Telegram
    logger.info("📨 Sending to Telegram...")
    
    # Header
    header_msg = f"""
🎯 <b>GÓC ÔN TẬP NGẪU NHIÊN</b>
Bài: <a href="{note_url}">{note_title}</a>
Trạng thái: 🔴 Cần xem lại
"""
    telegram.send_message(header_msg, parse_mode="HTML")
    time.sleep(1)

    # Content
    raw_chunks = quiz_content.split("🎯")
    questions = []
    
    for chunk in raw_chunks:
        clean = chunk.strip()
        if not clean: continue
        questions.append(f"🎯 {clean}")
        
    if not questions:
        # Fallback
        telegram.send_message(quiz_content, parse_mode="HTML", disable_notification=True)
    else:
        for q in questions:
            telegram.send_message(q, parse_mode="HTML", disable_notification=True)
            time.sleep(1)

    # Footer
    footer = """
---
👉 <i>Bấm vào link bài học để tự sửa trạng thái thành 🟢 Đã nắm vững nếu bạn trả lời đúng hết nhé!</i>
"""
    telegram.send_message(footer, parse_mode="HTML", disable_notification=True)
    
    logger.info("🏁 Study Job Completed!")

if __name__ == "__main__":
    run_study_assistant()
