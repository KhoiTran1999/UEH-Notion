import sys
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from src.config.settings import Config

def test():
    bot_token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    message = """
---
👉 <i>Hãy tự đánh giá mức độ hiểu bài của bạn sau khi trả lời:</i>
"""

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🟢 Đã nắm vững", "callback_data": "/mastered_387a5eb5b9bd80b79d7feac51124a3d1"},
                {"text": "🔴 Chưa nắm vững", "callback_data": "/review_387a5eb5b9bd80b79d7feac51124a3d1"}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }
    
    print("Sending direct request...")
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    test()
