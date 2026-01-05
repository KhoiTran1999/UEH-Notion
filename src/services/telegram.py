import httpx
from src.config.settings import Config
from src.utils.logger import logger

class TelegramService:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
        self.chat_id = Config.TELEGRAM_CHAT_ID

    def send_message(self, message, parse_mode="Markdown", disable_notification=False):
        """Sends a text message to the default chat."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("✅ Telegram message sent.")
                else:
                    logger.error(f"❌ Telegram Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Telegram Exception: {e}")

    def send_error_alert(self, message):
        """Sends a critical error alert."""
        alert_msg = f"🚨 **CRITICAL ERROR** 🚨\n\n{message}"
        self.send_message(alert_msg)

    def send_photo(self, photo, caption=None, has_spoiler=False, disable_notification=False):
        """Sends a photo to the default chat."""
        url = f"{self.base_url}/sendPhoto"
        
        payload = {
            "chat_id": self.chat_id,
            "photo": photo,
            "has_spoiler": has_spoiler,
            "disable_notification": disable_notification
        }
        
        if caption:
            payload["caption"] = caption
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("✅ Telegram photo sent.")
                else:
                    logger.error(f"❌ Telegram Photo Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Telegram Photo Exception: {e}")

    def send_voice(self, audio_path, caption=None):
        """Sends a voice note."""
        url = f"{self.base_url}/sendVoice"
        
        try:
            with open(audio_path, "rb") as audio_file:
                files = {"voice": audio_file}
                data = {"chat_id": self.chat_id}
                if caption:
                    data["caption"] = caption
                    
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, data=data, files=files)
                    if resp.status_code == 200:
                        logger.info("✅ Telegram voice sent.")
                    else:
                        logger.error(f"❌ Telegram Voice Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Telegram Voice Exception: {e}")
