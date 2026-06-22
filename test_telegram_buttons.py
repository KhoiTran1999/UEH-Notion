import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.services.telegram import TelegramService

def test():
    telegram = TelegramService()
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🟢 Đã nắm vững", "callback_data": "/mastered_test123"},
                {"text": "🔴 Chưa nắm vững", "callback_data": "/review_test123"}
            ]
        ]
    }
    
    print("Sending test message with buttons...")
    telegram.send_message("Test message with buttons", reply_markup=reply_markup)
    print("Done")

if __name__ == "__main__":
    test()
