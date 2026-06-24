import time
import sys
import os

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.services.telegram import TelegramService
from src.utils.logger import logger
from src.services.study_logic import get_candidates, generate_quiz, update_status
from src.config.settings import Config

def run_study_assistant(topic_id=None):
    logger.info("🎓 Starting Study Assistant Job...")
    telegram = TelegramService()

    if topic_id:
        logger.info(f"🎯 Explicit topic_id provided: {topic_id}")
        telegram.send_message("⏳ Đang đọc nội dung bài học từ Notion...", disable_notification=True)
        
        quiz_data = generate_quiz(topic_id)
        if not quiz_data:
            logger.warning("⚠️ Note content is empty.")
            telegram.send_message("⚠️ Nội dung bài học này đang trống!")
            return
            
        logger.info(f"🎯 Selected Note: {quiz_data['title']}")
        
        logger.info("🧠 Generating Quiz...")
        telegram.send_message("🧠 Đang dùng AI biên soạn câu hỏi trắc nghiệm...", disable_notification=True)
        
        # Format for Telegram
        message_parts = []
        header_msg = f"""
🎯 <b>GÓC ÔN TẬP KHẮC SÂU (Spaced Repetition)</b>
Bài: <a href="{quiz_data['url']}">{quiz_data['title']}</a>
Trạng thái: 🔴 Cần xem lại
"""
        message_parts.append(header_msg)
        
        for q in quiz_data['questions']:
            q_text = f"🎯 {q['question']}"
            message_parts.append(q_text)
            
            if q['answer']:
                ans_text = f"<tg-spoiler>{q['answer']}"
                message_parts.append(ans_text)
                
        footer = """
---
👉 <i>Hãy tự đánh giá mức độ hiểu bài của bạn sau khi trả lời:</i>
"""
        message_parts.append(footer)
        
        current_buffer = ""
        MAX_LENGTH = 4096

        for part in message_parts:
            if len(current_buffer) + len(part) + 2 > MAX_LENGTH:
                if current_buffer:
                    telegram.send_message(current_buffer, parse_mode="HTML", disable_notification=True)
                    time.sleep(1)
                current_buffer = part
            else:
                if current_buffer:
                    current_buffer += "\n\n" + part
                else:
                    current_buffer = part

        short_id = topic_id.replace("-", "")
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🟢 Đã nắm vững", "callback_data": f"/mastered_{short_id}"},
                    {"text": "🔴 Chưa nắm vững", "callback_data": f"/review_{short_id}"}
                ]
            ]
        }

        if current_buffer:
             telegram.send_message(current_buffer, parse_mode="HTML", reply_markup=reply_markup, disable_notification=True)
             
        update_status(topic_id)

    else:
        candidates = get_candidates()

        if not candidates:
            logger.info("🎉 No review notes found today.")
            telegram.send_message("🎉 Hôm nay không có bài nào cần ôn tập!")
            return

        buttons = []
        for c in candidates:
            buttons.append([{"text": c["title"], "web_app": {"url": Config.WEBAPP_URL}}])

        reply_markup = {"inline_keyboard": buttons}
        msg = "📚 **Dưới đây là các bài học cần ôn tập:**\n\nNhấp vào bài học để mở Web App ôn tập trắc nghiệm:"
        telegram.send_message(msg, parse_mode="Markdown", reply_markup=reply_markup)
        logger.info("Sent topic selection to Telegram.")
        return

    logger.info("🏁 Study Job Completed!")

if __name__ == "__main__":
    run_study_assistant()
