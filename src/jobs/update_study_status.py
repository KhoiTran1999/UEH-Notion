import sys
import os

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.services.notion import NotionService
from src.services.telegram import TelegramService
from src.utils.logger import logger

def run_update_study_status(topic_id, status):
    logger.info(f"🚀 Updating study status for {topic_id} to {status}...")

    if not topic_id:
        logger.error("❌ Missing topic_id.")
        return

    notion = NotionService()
    telegram = TelegramService()

    success = notion.update_page_property(topic_id, "Độ hiểu bài", status, type_key="select")

    if success:
        telegram.send_message(f"✅ Đã lưu trạng thái: {status}", disable_notification=True)
    else:
        telegram.send_message("❌ Lỗi: Không thể cập nhật trạng thái Notion.", disable_notification=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("topic_id")
    parser.add_argument("status")
    args = parser.parse_args()
    run_update_study_status(args.topic_id, args.status)
