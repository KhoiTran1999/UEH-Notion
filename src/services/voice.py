import asyncio
import struct
import sys
import os

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google import genai
from google.genai import types
from src.config.settings import Config
from src.utils.logger import logger

class VoiceService:
    @staticmethod
    def _parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
        """Parses bits per sample and rate from an audio MIME type string."""
        bits_per_sample = 16
        rate = 24000
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate_str = param.split("=", 1)[1]
                    rate = int(rate_str)
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass
        return {"bits_per_sample": bits_per_sample, "rate": rate}

    @staticmethod
    def _convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
        """Generates a WAV file header for the given audio data and parameters."""
        parameters = VoiceService._parse_audio_mime_type(mime_type)
        bits_per_sample = parameters["bits_per_sample"]
        sample_rate = parameters["rate"]
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
        )
        return header + audio_data

    @staticmethod
    async def generate_audio(text, output_file):
        """Generates audio file from text using Gemini TTS."""
        logger.info(f"🗣️ Generating voice with Gemini ({Config.GEMINI_VOICE_NAME})...")
        
        if not Config.GEMINI_API_KEY:
            logger.error("❌ Error: GEMINI_API_KEY not found.")
            return None

        # Clean text basic cleanup if needed, though Gemini handles well
        # text = text.replace("*", "").replace("#", "") 
        
        try:
            client = genai.Client(api_key=Config.GEMINI_API_KEY)
            
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=text)],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=Config.GEMINI_VOICE_NAME
                        )
                    )
                ),
            )
            
            model_name = Config.GEMINI_VOICE_MODEL

            all_raw_bytes = bytearray()
            mime_type = None

            # Streaming generation
            for chunk in client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=generate_content_config,
            ):
                if (chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None):
                    continue
                
                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    if not mime_type:
                        mime_type = part.inline_data.mime_type
                    all_raw_bytes.extend(part.inline_data.data)

            if len(all_raw_bytes) > 0:
                if not mime_type:
                    mime_type = "audio/L16;rate=24000"
                
                wav_data = VoiceService._convert_to_wav(all_raw_bytes, mime_type)
                
                # Ensure output file ends with .wav (Gemini output is PCM/WAV friendly)
                # But if user requested .mp3, we might just save wav with that name or strict replace?
                # The user's code forced .wav extension. We will follow that logic.
                real_output_file = output_file
                if not real_output_file.lower().endswith(".wav"):
                     if real_output_file.lower().endswith(".mp3"):
                          real_output_file = real_output_file[:-4] + ".wav"
                     else:
                          real_output_file = real_output_file + ".wav"

                with open(real_output_file, "wb") as f:
                    f.write(wav_data)
                
                logger.info(f"✅ Audio generated: {real_output_file} (Size: {len(wav_data)})")
                return real_output_file
            else:
                logger.error("❌ Stream finished. No audio data collected.")
                return None

        except Exception as e:
            logger.error(f"❌ Gemini TTS Error: {e}")
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
    test_text = "Xin chào! Đây là giọng đọc thử nghiệm từ Gemini."
    VoiceService.run_generate_sync(test_text, "test_gemini_voice.wav")
