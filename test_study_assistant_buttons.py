import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.services.telegram import TelegramService

def test():
    telegram = TelegramService()
    
    current_buffer = "Test study assistant content without markup"
    short_id = "test12345"
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🟢 Đã nắm vững", "callback_data": f"/mastered_{short_id}"},
                {"text": "🔴 Chưa nắm vững", "callback_data": f"/review_{short_id}"}
            ]
        ]
    }
    
    print("Testing study assistant send format...")
    telegram.send_message(current_buffer, parse_mode="HTML", reply_markup=reply_markup)
    print("Done")

if __name__ == "__main__":
    test()
