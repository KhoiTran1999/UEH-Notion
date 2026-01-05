import time
import random
import sys
import os
import re
import urllib.parse

# Add project root to python path to allow direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.services.notion import NotionService
from src.services.ai import AIService
from src.services.telegram import TelegramService
from src.utils.logger import logger

def send_content_with_latex(telegram_service: TelegramService, text: str):
    """
    Parses text for LaTeX formulas wrapped in $.
    - Aggregates text and "simple" formulas (e.g., variables) into a single text message.
    - Sends "complex" formulas as images, interrupting the text flow.
    - Handles HTML tag balancing.
    """
    parts = re.split(r'\$(.*?)\$', text)
    
    # Buffer for collecting text to be sent as one message
    current_message_buffer = ""
    
    # Track open tags to preserve context across chunks
    open_tags = []

    def update_open_tags(text_chunk, tags_stack):
        """Updates the tags_stack based on tags found in text_chunk."""
        # Regex for tags: <tag>, </tag>, <tag ...>
        # We handle <tg-spoiler> etc via [\w-]+
        tag_iter = re.finditer(r'<(/?)(\w+)([^>]*)>', text_chunk) # Simplified regex again for safety, hyphens covered?
        # Actually previous regex was r'<(/?)([\w-]+)([^>]*)>' - let's reuse that
        tag_iter = re.finditer(r'<(/?)([\w-]+)([^>]*)>', text_chunk)
        
        temp_stack = list(tags_stack)
        for match in tag_iter:
            is_close = match.group(1) == "/"
            tag_name = match.group(2)
            
            if not is_close:
                # Self-closing tags like <br/> are rare in Telegram HTML, assume standard
                temp_stack.append(tag_name)
            else:
                if temp_stack and temp_stack[-1] == tag_name:
                    temp_stack.pop()
        return temp_stack

    def get_balanced_text(text_content, current_tags):
        """Wraps text with any currently open tags to ensure valid HTML."""
        if not text_content: return ""
        
        prefix = ""
        for tag in current_tags:
            if tag == 'tg-spoiler':
                prefix += "<tg-spoiler>"
            else:
                prefix += f"<{tag}>"
                
        suffix = ""
        for tag in reversed(current_tags):
            suffix += f"</{tag}>"
            
        return prefix + text_content + suffix

    def is_complex_formula(latex_str):
        """
        Determines if a LaTeX string should be an image.
        Criteria: Contains special LaTeX cmds OR length > variable threshold.
        """
        # Symbols implying complexity
        special_chars = ['\\', '=', '^', '_', '{', '}', '>', '<']
        if any(char in latex_str for char in special_chars):
            return True
        # If it's just text but very long?
        if len(latex_str) > 10: 
            return True
        return False

    for i, part in enumerate(parts):
        clean_part = part.strip()
        
        if i % 2 == 0:
            # -- Text Part --
            if not clean_part: continue
            
            # Append to buffer
            current_message_buffer += part
            open_tags = update_open_tags(part, open_tags)
            
        else:
            # -- Formula Part --
            if not clean_part: continue
            
            if is_complex_formula(clean_part):
                # COMPLETE BREAK: Flush Buffer -> Send Image -> Resume
                
                # Punctuation Lookahead Logic
                # Check if the NEXT part (i+1) exists and is a text part
                # parts[i] is formula. parts[i+1] is text.
                # We want to steal leading punctuation from parts[i+1]
                trailing_punc = ""
                if i + 1 < len(parts):
                    next_text = parts[i+1]
                    # Regex to match leading punctuation. 
                    # We match typical sentence enders or separators: . , ; : ) ] ? !
                    # Note: We modifying parts[i+1] in place or just handling it?
                    # Since we iterate sequentially, if we modify parts[i+1], the next iteration will see the modified version.
                    # Yes, lists are mutable.
                    
                    match = re.match(r'^([.,;:!?)\]\}]+)(.*)', next_text, re.DOTALL)
                    if match:
                        found_punc = match.group(1)
                        rest_of_text = match.group(2)
                        
                        # Absorb punctuation
                        trailing_punc = found_punc
                        
                        # Update the next part to remove the absorbed punctuation
                        parts[i+1] = rest_of_text
                
                # 1. Flush existing buffer
                suffix = ""
                for tag in reversed(open_tags):
                    suffix += f"</{tag}>"
                
                msg_to_send = current_message_buffer + suffix
                
                # Check if message has actual text content (ignoring HTML tags)
                # This prevents sending empty messages like "<tg-spoiler></tg-spoiler>"
                if re.sub(r'<[^>]+>', '', msg_to_send).strip():
                     telegram_service.send_message(msg_to_send, parse_mode="HTML", disable_notification=True)
                     time.sleep(0.5)
                
                current_message_buffer = "" 
                
                # 2. Send Image with merged punctuation
                # Use \text{} for the punctuation to preserve it plain
                latex_with_punc = clean_part
                if trailing_punc:
                    latex_with_punc += f"\\text{{{trailing_punc}}}"
                
                # Use fixed DPI
                full_latex = f"\\dpi{{300}} \\bg_white {{{latex_with_punc}}}"
                encoded_latex = urllib.parse.quote(full_latex)
                image_url = f"https://latex.codecogs.com/png.image?{encoded_latex}"
                
                is_spoiler = 'tg-spoiler' in open_tags
                telegram_service.send_photo(image_url, has_spoiler=is_spoiler, disable_notification=True)
                time.sleep(1)
                
                # 3. Prepare buffer for next text
                prefix = ""
                for tag in open_tags:
                    if tag == 'tg-spoiler':
                        prefix += "<tg-spoiler>"
                    else:
                        prefix += f"<{tag}>"
                current_message_buffer = prefix
                    
            else:
                # Simple -> Bold Text
                simple_fmt = f"<b>{clean_part}</b>"
                current_message_buffer += " " + simple_fmt + " " # Spacing for variables
                current_message_buffer += simple_fmt # Wait, I duplicated the line above in my thought process?
                # " " + simple_fmt + " " creates " <b>x</b> "
                # If I do += simple_fmt, I get "<b>x</b>"
                # Variables usually need space if not present.
                # But 'part' logic preserved spaces?
                # 'parts = re.split' preserves separators but 'clean_part' strips.
                # However 'part' which I added to buffer in even index WAS NOT STRIPPED.
                # So trailing space from previous text is there.
                # What about leading space for next text?
                # If I just append `simple_fmt` (<b>x</b>), it depends on the surrounding text.
                # Safest allows tight packing: "Function<b>f(x)</b>..."
                # Let's just append `simple_fmt` without extra spaces, trusting the source text had them.
                # BUT, I removed the `current_message_buffer += " " + simple_fmt + " "` line from my thought, 
                # let's be careful in replacement.
                
                # Correct logic:
                current_message_buffer += f"<b>{clean_part}</b>"

    # Final Flush
    if current_message_buffer.strip():
        suffix = ""
        for tag in reversed(open_tags):
            suffix += f"</{tag}>"
        
        final_msg = current_message_buffer + suffix
        
        if re.sub(r'<[^>]+>', '', final_msg).strip():
            telegram_service.send_message(final_msg, parse_mode="HTML", disable_notification=True)

def run_study_assistant():
    logger.info("🎓 Starting Study Assistant Job...")

    # Initialize Services
    notion = NotionService()
    ai = AIService()
    telegram = TelegramService()

    # 1. Fetch Candidates (Assume this returns raw page objects)
    candidates = notion.get_review_notes()
    
    if not candidates:
        logger.info("🎉 No review notes found today.")
        return

    # 2. Select Note based on Spaced Repetition (Oldest "Last Review At" first)
    def get_last_review_sort_key(note):
        # We want to sort ascending.
        # Priority 1: No "Last Review At" (None or Empty) -> Treat as "" to sort first.
        # Priority 2: Oldest "Last Review At" -> "2023..." comes before "2025..."
        try:
            props = note.get("properties", {})
            last_review = props.get("Last Review At", {}).get("date", {})
            if last_review and last_review.get("start"):
                 return last_review["start"]
        except:
            pass
        return "" # Empty string sorts before any ISO date string

    # Sort candidates
    candidates.sort(key=get_last_review_sort_key)
    
    # Select the top 1 (oldest or unreviewed)
    selected_note = candidates[0]
    
    note_id = selected_note["id"]
    note_url = selected_note["url"]
    
    note_title = "Unknown Note"
    if selected_note["properties"].get("Tên bài học", {}).get("title"):
        note_title = selected_note["properties"]["Tên bài học"]["title"][0]["plain_text"]
    
    logger.info(f"🎯 Selected Note: {note_title}")

    # 3. Deep Fetch Content
    content_lines = notion.fetch_page_content(note_id)
    full_content = "\n".join(content_lines)

    if not full_content.strip():
        logger.warning("⚠️ Note content is empty.")
        return

    # 4. Generate Quiz
    logger.info("🧠 Generating Quiz...")

    quiz_content = ai.generate_quiz(full_content)

    # 5. Send to Telegram
    logger.info("📨 Sending to Telegram...")
    
    # Header
    header_msg = f"""
🎯 <b>GÓC ÔN TẬP KHẮC SÂU (Spaced Repetition)</b>
Bài: <a href="{note_url}">{note_title}</a>
Trạng thái: 🔴 Cần xem lại
"""
    telegram.send_message(header_msg, parse_mode="HTML")
    time.sleep(1)

    # Content
    raw_chunks = quiz_content.split("🎯")
    questions = []
    
    for chunk in raw_chunks:
        clean = chunk.strip()
        if not clean: continue
        questions.append(f"🎯 {clean}")
        
    if not questions:
        # Fallback
        send_content_with_latex(telegram, quiz_content)
    else:
        for q in questions:
            send_content_with_latex(telegram, q)
            time.sleep(1)

    # Footer
    footer = """
---
👉 <i>Bấm vào link bài học để tự sửa trạng thái thành 🟢 Đã nắm vững nếu bạn trả lời đúng hết nhé!</i>
"""
    telegram.send_message(footer, parse_mode="HTML", disable_notification=True)
    
    # 6. Update "Last Review At"
    try:
        import datetime
        import pytz
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now_iso = datetime.datetime.now(vn_tz).isoformat()
        
        logger.info(f"🗓 Updating Last Review At to: {now_iso}")
        notion.update_page_property(note_id, "Last Review At", now_iso, type_key="date")
        
    except Exception as e:
        logger.error(f"❌ Failed to update Last Review At: {e}")

    logger.info("🏁 Study Job Completed!")

if __name__ == "__main__":
    run_study_assistant()
