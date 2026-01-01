import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Notion
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    NOTION_DB_GHI_CHEP_ID = os.getenv("NOTION_DB_GHI_CHEP_ID", "2d96633f4324813b9d9eca9f85d2ea48")
    NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

    # AI (Gemini)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_FLASH = "gemini-1.5-flash"
    GEMINI_MODEL_PRO = "gemini-2.0-flash-exp" # Or gemini-3-flash-preview as user requested

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Voice
    VOICE_NAME = "vi-VN-HoaiMyNeural"

    @classmethod
    def validate(cls):
        """Check for critical missing variables"""
        missing = []
        if not cls.NOTION_TOKEN: missing.append("NOTION_TOKEN")
        if not cls.GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
        if not cls.TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
        
        if missing:
            raise EnvironmentError(f"Missing critical environment variables: {', '.join(missing)}")
