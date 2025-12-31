import asyncio
import os
import struct
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Voice constant: high quality Vietnamese male voice (Note: GenAI voices are different, using 'Puck' or similar as default or from config)
# The user wants to use genai, example.py uses "Puck".
# We'll allow passing voice name or default to "Puck".
VOICE = "Sadachbia"

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
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

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
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

async def _generate_audio_async(text, output_file, voice=VOICE):
    """
    Async helper to generate audio using Google GenAI.
    """
    print(f"🗣️ Generating voice with Gemini ({voice})...")
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found.")
        return False

    client = genai.Client(api_key=GEMINI_API_KEY)
    
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
                    voice_name=voice
                )
            )
        ),
    )
    
    model_name = "gemini-2.5-flash-preview-tts" # Using consistent model name

    all_raw_bytes = bytearray()
    mime_type = None

    try:
        # Note: generate_content_stream is synchronous in the example provided, 
        # but we are in an async function. 
        # The client library seems to be sync in the example.
        # However, to avoid blocking the event loop if this were a real async app, we might need run_in_executor.
        # But for now, we follow the simplest port. 
        # Warning: This is blocking I/O in an async function!
        # But since the previous edge_tts was awaited, the caller expects async.
        # We will wrap it or just run it. 
        # The example.py used async def generate_audio_from_text but called sync client methods inside.
        
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
            
            wav_data = convert_to_wav(all_raw_bytes, mime_type)
            
            # Ensure output file ends with .wav
            if not output_file.lower().endswith(".wav"):
                if output_file.lower().endswith(".mp3"):
                     output_file = output_file[:-4] + ".wav"
                else:
                     output_file = output_file + ".wav"

            with open(output_file, "wb") as f:
                f.write(wav_data)
            print(f"✅ Created voice file: {output_file} (Size: {len(wav_data)})")
            return output_file
        else:
            print("❌ Stream finished. No audio data collected.")
            return None

    except Exception as e:
        print(f"❌ Voice Generator Error: {e}")
        return None

def generate_voice_summary(text, output_file="summary.wav"):
    """
    Synchronous wrapper to generate voice summary from text.
    """
    try:
        if not text or not text.strip():
            print("❌ Voice Generator: No text provided.")
            return None

        # Run async function
        result = asyncio.run(_generate_audio_async(text, output_file))
        return result
            
    except Exception as e:
        print(f"❌ Voice Generator Error: {e}")
        return None

if __name__ == "__main__":
    # Test standalone
    test_text = "Xin chào Khôi! Hôm nay là một ngày tuyệt vời để học tập và làm việc. Hãy cố gắng hết mình nhé!"
    generate_voice_summary(test_text, "test_voice.wav")
