import os
import httpx

def send_telegram_message(message, parse_mode="Markdown", disable_notification=False):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ Thiếu Telegram Token hoặc Chat ID")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                print("✅ Đã gửi tin nhắn Telegram thành công!")
            else:
                print(f"❌ Lỗi gửi Telegram: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Exception Telegram: {e}")

def send_telegram_voice(audio_path, caption=None):
    """
    Gửi file âm thanh (voice) sang Telegram
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ Thiếu Telegram Token hoặc Chat ID")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendVoice"
    
    try:
        # Mở file audio ở chế độ binary read
        with open(audio_path, "rb") as audio_file:
            files = {"voice": audio_file}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
                
            with httpx.Client(timeout=60.0) as client: # Timeout lâu hơn cho file upload
                resp = client.post(url, data=data, files=files)
                
                if resp.status_code == 200:
                    print("✅ Đã gửi Voice Telegram thành công!")
                else:
                    print(f"❌ Lỗi gửi Voice: {resp.status_code} - {resp.text}")
                    
    except Exception as e:
        print(f"❌ Exception Telegram Voice: {e}")
