import asyncio
import os
import sys

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from openai import OpenAI
from src.config.settings import Config
from src.utils.logger import logger

class VoiceService:
    @staticmethod
    async def generate_audio(text, output_file):
        """Generates audio file from text using OpenAI SDK."""
        if not Config.USE_CUSTOM_AI:
            logger.error("❌ Error: USE_CUSTOM_AI is false.")
            return None
            
        if not Config.CUSTOM_AI_API_KEY:
            logger.error("❌ Error: CUSTOM_AI_API_KEY not found.")
            return None
            
        logger.info(f"🗣️ Generating voice with custom AI ({Config.CUSTOM_AI_VOICE_MODEL})...")
        
        try:
            client = OpenAI(
                base_url=Config.CUSTOM_AI_BASE_URL,
                api_key=Config.CUSTOM_AI_API_KEY
            )
            
            response = client.audio.speech.create(
                model=Config.CUSTOM_AI_VOICE_MODEL,
                voice="alloy", # Required by API but might be ignored by some custom endpoints
                input=text
            )
            
            # Ensure output file ends with correct extension. OpenAI default is mp3.
            real_output_file = output_file
            if not real_output_file.lower().endswith((".mp3", ".wav", ".aac", ".flac", ".opus", ".pcm")):
                 real_output_file = real_output_file + ".mp3"

            response.stream_to_file(real_output_file)
            
            logger.info(f"✅ Audio generated: {real_output_file}")
            return real_output_file

        except Exception as e:
            logger.error(f"❌ OpenAI TTS Error: {e}")
            return None

    @staticmethod
    def run_generate_sync(text, output_file):
        """Wrapper to run async generation synchronously."""
        try:
            return asyncio.run(VoiceService.generate_audio(text, output_file))
        except Exception as e:
            logger.error(f"❌ Sync TTS Error: {e}")
            return None

if __name__ == "__main__":
    # Test standalone
    test_text = "Xin chào! Đây là giọng đọc thử nghiệm từ Custom AI."
    VoiceService.run_generate_sync(test_text, "test_custom_voice.mp3")
