import asyncio
import edge_tts
from src.config.settings import Config
from src.utils.logger import logger

class VoiceService:
    @staticmethod
    async def generate_audio(text, output_file):
        """Generates audio file from text using Edge TTS."""
        voice = Config.VOICE_NAME
        clean_text = text.replace("*", "").replace("#", "").replace("-", "") # Basic cleanup
        
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(output_file)
            logger.info(f"✅ Audio generated: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"❌ TTS Error: {e}")
            return None

    @staticmethod
    def run_generate_sync(text, output_file):
        """Wrapper to run async generation synchronously."""
        try:
            asyncio.run(VoiceService.generate_audio(text, output_file))
            return output_file
        except Exception as e:
            logger.error(f"❌ Sync TTS Error: {e}")
            return None
