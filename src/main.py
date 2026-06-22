import sys
import os
import argparse
import traceback
# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.telegram import TelegramService
from src.utils.logger import logger
from src.jobs.daily_report import run_daily_report
from src.jobs.study_assistant import run_study_assistant
from src.jobs.update_study_status import run_update_study_status

def main():
    parser = argparse.ArgumentParser(description="UEH Notion Bot CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a specific job")
    run_parser.add_argument("job", choices=["daily-report", "study-assistant", "mark-mastered", "mark-review"], help="Job name")
    run_parser.add_argument("--chat_id", default=None, help="Telegram Chat ID (from Telegram trigger)")
    run_parser.add_argument("--topic_id", default=None, help="Specific Notion Page ID to study")

    args = parser.parse_args()

    if args.command == "run":
        # Override TELEGRAM_CHAT_ID if provided via Telegram trigger
        if args.chat_id:
            os.environ["TELEGRAM_CHAT_ID"] = args.chat_id
            logger.info(f"🎯 Telegram trigger from chat_id: {args.chat_id}")

        if args.job == "daily-report":
            run_daily_report()
        elif args.job == "study-assistant":
            run_study_assistant(topic_id=args.topic_id)
        elif args.job == "mark-mastered":
            run_update_study_status(topic_id=args.topic_id, status="🟢 Đã nắm vững")
        elif args.job == "mark-review":
            run_update_study_status(topic_id=args.topic_id, status="🔴 Chưa nắm vững")
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"Script crashed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(error_msg)
        try:
            TelegramService().send_error_alert(error_msg)
        except Exception as telegram_error:
            logger.error(f"Failed to send Telegram alert: {telegram_error}")
        sys.exit(1)
