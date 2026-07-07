import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import src.utils.path_setup  # ensure project root is on sys.path

from src.services.notion import NotionService
from src.services.ai import AIService
from src.services.telegram import TelegramService
from src.services.voice import VoiceService
from src.utils.logger import logger

def run_daily_report():
    logger.info("🚀 Starting Daily Report Job...")

    notion = NotionService()
    ai = AIService()
    telegram = TelegramService()

    telegram.send_message("⏳ Đang lấy dữ liệu task từ Notion...", disable_notification=True)

    # 1. Fetch Tasks
    tasks = notion.get_tasks()
    db_options = notion.get_database_options()
    
    if not tasks:
        logger.warning("⚠️ No tasks found or fetched.")

    # 2. Analyze
    logger.info("🧠 Analyzing tasks...")
    telegram.send_message("🧠 Đang dùng AI phân tích và lập kế hoạch...", disable_notification=True)
    summary = ai.analyze_tasks(tasks, db_options)
    
    # 3. Send Text
    logger.info("📨 Sending Report...")
    telegram.send_message(summary)

    # 4. Voice Generation
    if tasks:
        logger.info("🎙️ Generating Voice...")
        telegram.send_message("🎙️ Đang tạo audio tóm tắt...", disable_notification=True)
        voice_script = ai.generate_voice_script(summary)
        
        output_file = "daily_voice.mp3"
        audio_path = VoiceService.run_generate_sync(voice_script, output_file)
        
        if audio_path:
            logger.info("📨 Sending Voice...")
            telegram.send_voice(audio_path, caption="🎧 Daily Audio Brief")
        else:
            logger.error("❌ Audio generation failed.")
    else:
        logger.info("🔕 Skipped voice generation (no tasks).")

    logger.info("🏁 Daily Report Job Completed!")

if __name__ == "__main__":
    run_daily_report()
