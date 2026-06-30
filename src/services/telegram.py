import httpx
from src.config.settings import Config
from src.utils.logger import logger

class TelegramService:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
        self.chat_id = Config.TELEGRAM_CHAT_ID

    def send_message(self, message, parse_mode="Markdown", disable_notification=False, reply_markup=None):
        if not message:
            return

        MAX_LEN = 4000
        
        chunks = []
        if len(message) <= MAX_LEN:
            chunks = [message]
        else:
            nl = chr(10)
            dnl = chr(10) + chr(10)
            parts = message.split(dnl)
            current_chunk = ""
            for part in parts:
                if len(current_chunk) + len(part) + 2 <= MAX_LEN:
                    if current_chunk:
                        current_chunk += dnl + part
                    else:
                        current_chunk = part
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    if len(part) > MAX_LEN:
                        subparts = part.split(nl)
                        sub_chunk = ""
                        for subpart in subparts:
                            if len(sub_chunk) + len(subpart) + 1 <= MAX_LEN:
                                if sub_chunk:
                                    sub_chunk += nl + subpart
                                else:
                                    sub_chunk = subpart
                            else:
                                if sub_chunk:
                                    chunks.append(sub_chunk)
                                if len(subpart) > MAX_LEN:
                                    for i in range(0, len(subpart), MAX_LEN):
                                        chunks.append(subpart[i:i+MAX_LEN])
                                    sub_chunk = ""
                                else:
                                    sub_chunk = subpart
                        if sub_chunk:
                            current_chunk = sub_chunk
                    else:
                        current_chunk = part
            if current_chunk:
                chunks.append(current_chunk)

        url = f"{self.base_url}/sendMessage"
        
        for i, chunk in enumerate(chunks):
            current_reply_markup = reply_markup if i == len(chunks) - 1 else None
            
            payload = {
                "chat_id": self.chat_id,
                "text": chunk,
                "disable_notification": disable_notification
            }

            if parse_mode:
                payload["parse_mode"] = parse_mode

            if current_reply_markup:
                import json
                if isinstance(current_reply_markup, dict):
                    payload["reply_markup"] = json.dumps(current_reply_markup)
                else:
                    payload["reply_markup"] = current_reply_markup

            try:
                import httpx
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        logger.info(f"✅ Telegram message chunk {i+1}/{len(chunks)} sent.")
                    elif resp.status_code == 400 and parse_mode:
                        logger.warning(f"⚠️ Telegram Error 400 (Formatting issue): {resp.text}")
                        logger.info("🔄 Retrying as plain text...")
                        if "parse_mode" in payload:
                            del payload["parse_mode"]
                        resp_retry = client.post(url, json=payload)
                        if resp_retry.status_code == 200:
                            logger.info(f"✅ Telegram message chunk {i+1}/{len(chunks)} sent (Plain Text).")
                        else:
                            logger.error(f"❌ Retry Failed {resp_retry.status_code}: {resp_retry.text}")
                    else:
                        logger.error(f"❌ Telegram Error {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"❌ Telegram Exception: {e}")
    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        """Answers a callback query to remove loading state on button."""
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert
        }
        if text:
            payload["text"] = text

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"✅ Telegram answer_callback_query success: {callback_query_id}")
                else:
                    logger.error(f"❌ Telegram answerCallbackQuery Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Telegram answerCallbackQuery Exception: {e}")

    def send_error_alert(self, message):
        """Sends a critical error alert."""
        alert_msg = f"🚨 **CRITICAL ERROR** 🚨\n\n{message}"
        self.send_message(alert_msg)

    def set_menu_button(self, chat_id, text, web_app_url):
        """Configures the chat menu button to open Web App directly."""
        url = f"{self.base_url}/setChatMenuButton"
        payload = {
            "chat_id": chat_id,
            "menu_button": {
                "type": "web_app",
                "text": text,
                "web_app": {
                    "url": web_app_url
                }
            }
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"✅ Telegram menu button configured for chat {chat_id}")
                else:
                    logger.error(f"❌ Telegram setChatMenuButton Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Telegram setChatMenuButton Exception: {e}")

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
