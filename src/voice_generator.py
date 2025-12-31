import asyncio
import edge_tts
import os

# Voice constant: high quality Vietnamese male voice
VOICE = "vi-VN-NamMinhNeural" 

async def _generate_audio_async(text, output_file):
    """
    Async helper to generate audio using edge-tts.
    """
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def generate_voice_summary(text, output_file="summary.mp3"):
    """
    Synchronous wrapper to generate voice summary from text.
    """
    try:
        # Check if text is valid
        if not text or not text.strip():
            print("❌ Voice Generator: No text provided.")
            return None

        # Run async function
        asyncio.run(_generate_audio_async(text, output_file))
        
        # Verify file creation
        if os.path.exists(output_file):
            print(f"✅ Created voice file: {output_file}")
            return output_file
        else:
            print("❌ Voice Generator: File was not created.")
            return None
            
    except Exception as e:
        print(f"❌ Voice Generator Error: {e}")
        return None

if __name__ == "__main__":
    # Test standalone
    test_text = "Xin chào Khôi! Hôm nay là một ngày tuyệt vời để học tập và làm việc. Hãy cố gắng hết mình nhé!"
    generate_voice_summary(test_text, "test_voice.mp3")
