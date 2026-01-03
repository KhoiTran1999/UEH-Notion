import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Notion
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    NOTION_DB_GHI_CHEP_ID = os.getenv("NOTION_DB_GHI_CHEP_ID")
    NOTION_VERSION = os.getenv("NOTION_VERSION", "2025-09-03")

    # AI (Gemini)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Load all keys starting with GEMINI_API_KEY
    GEMINI_API_KEYS = [
        val for key, val in os.environ.items() 
        if key.startswith("GEMINI_API_KEY") and val
    ]
    # Ensure the main key is in the list if not already (though the loop covers it)
    if GEMINI_API_KEY and GEMINI_API_KEY not in GEMINI_API_KEYS:
        GEMINI_API_KEYS.insert(0, GEMINI_API_KEY)
        
    GEMINI_MODEL_FLASH = "gemini-3-flash-preview"

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Voice
    # VOICE_NAME = "vi-VN-HoaiMyNeural" # Old Edge-TTS voice
    GEMINI_VOICE_MODEL = "gemini-2.5-flash-preview-tts"
    GEMINI_VOICE_NAME = "Sadachbia"

    @classmethod
    def validate(cls):
        """Check for critical missing variables"""
        missing = []
        if not cls.NOTION_TOKEN: missing.append("NOTION_TOKEN")
        if not cls.TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
        
        if missing:
            raise EnvironmentError(f"Missing critical environment variables: {', '.join(missing)}")
