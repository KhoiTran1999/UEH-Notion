import asyncio
import os
import sys
import re

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from openai import OpenAI
from src.config.settings import Config
from src.utils.logger import logger

class VoiceService:
    @staticmethod
    def chunk_text(text, max_chars=1000, max_words=200):
        """Split text into chunks, respecting max_chars and max_words constraints."""
        parts = re.split(r'(?<=[.!?\n])\s+', text)

        chunks = []
        current_chunk = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            words_in_current = len(current_chunk.split())
            words_in_part = len(part.split())

            if (len(current_chunk) + len(part) + 1 <= max_chars) and (words_in_current + words_in_part <= max_words):
                current_chunk += (" " + part if current_chunk else part)
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                # If the part itself is too big
                if len(part) > max_chars or words_in_part > max_words:
                    words = part.split()
                    temp_chunk = ""
                    for w in words:
                        if len(temp_chunk) + len(w) + 1 <= max_chars and len(temp_chunk.split()) < max_words:
                            temp_chunk += (" " + w if temp_chunk else w)
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            temp_chunk = w
                    current_chunk = temp_chunk
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    @staticmethod
    async def generate_audio(text, output_file):
        """Generates audio file from text using OpenAI SDK, handling chunks."""
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

            # Ensure output file ends with correct extension. OpenAI default is mp3.
            real_output_file = output_file
            if not real_output_file.lower().endswith((".mp3", ".wav", ".aac", ".flac", ".opus", ".pcm")):
                 real_output_file = real_output_file + ".mp3"

            chunks = VoiceService.chunk_text(text)
            logger.info(f"📝 Split text into {len(chunks)} chunks for TTS processing.")

            combined_audio = bytearray()

            for i, chunk in enumerate(chunks):
                logger.info(f"🎙️ Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                response = client.audio.speech.create(
                    model=Config.CUSTOM_AI_VOICE_MODEL,
                    voice="alloy", # Required by API but might be ignored by some custom endpoints
                    input=chunk
                )
                # Concatenate raw bytes
                combined_audio.extend(response.content)

            # Write all bytes at once to output file
            with open(real_output_file, 'wb') as f:
                f.write(combined_audio)

            logger.info(f"✅ Audio generated successfully ({len(chunks)} chunks combined): {real_output_file}")
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
