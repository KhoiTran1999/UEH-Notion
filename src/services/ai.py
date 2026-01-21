import json
from datetime import datetime, timedelta, timezone
from google import genai
from src.config.settings import Config
from src.utils.logger import logger

from src.services.prompt_service import PromptService

class AIService:
    def __init__(self):
        self.api_keys = Config.GEMINI_API_KEYS
        self.current_key_index = 0
        self.prompt_service = PromptService()
        
        if self.api_keys:
            self.client = self._get_client()
        else:
            logger.error("❌ No GEMINI_API_KEYS found!")
            self.client = None

    def _get_client(self):
        """Initializes a client with the current API key."""
        if not self.api_keys: return None
        current_key = self.api_keys[self.current_key_index]
        return genai.Client(api_key=current_key)

    def _rotate_key(self):
        """Switches to the next available API key."""
        if not self.api_keys: return
        
        prev_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.client = self._get_client()
        
        logger.warning(f"🔄 Rotating API Key: {prev_index} -> {self.current_key_index}")

    def _get_vn_time(self):
        return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    def generate_content(self, prompt, model=Config.GEMINI_MODEL_FLASH):
        if not self.client: return "AI Service Unavailable"
        
        # Try up to the number of available keys
        max_attempts = len(self.api_keys)
        
        for attempt in range(max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                if not response.text:
                    raise ValueError("Empty response from AI model (response.text is None)")
                return response.text.strip()
            except Exception as e:
                logger.error(f"❌ AI Generation Error (Key {self.current_key_index}): {e}")
                
                # Check if it is a quota error or if we have other keys to try
                if attempt < max_attempts - 1:
                    logger.info("⚠️ Retrying with a new API Key...")
                    self._rotate_key()
                else:
                    logger.error("❌ All API keys failed.")
                    return f"Error: All API keys failed. Last error: {str(e)}"

    def analyze_tasks(self, tasks, db_options=None):
        """Generates the daily report analysis using prompts from Notion."""
        if not tasks:
            return "Chào buổi sáng! 🌞 Hôm nay bạn không có task nào phải làm. Hãy tận hưởng ngày nghỉ nhé! 🚀"

        # Fetch prompt from Notion
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "daily_report")
        
        if not prompt_data:
            # Fallback if Notion fetch fails (optional, or just error out)
            system_prompt = "Bạn là một Chuyên gia Quản trị năng suất."
            user_template = "Dữ liệu: {tasks_str}. Hãy phân tích."
            model = Config.GEMINI_MODEL_FLASH
            logger.warning("⚠️ Using fallback prompt for analyze_tasks")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]
            model = prompt_data["model"]

        # Format Options string
        status_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Trạng thái", [])]) if db_options else ""
        type_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Loại nhiệm vụ", [])]) if db_options else ""
        priority_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Độ ưu tiên", [])]) if db_options else ""
        
        tags_instruction = f"""
   • Trạng thái: {status_opts}
   • Loại nhiệm vụ: {type_opts}
   • Độ ưu tiên: {priority_opts}
""" if db_options else ""

        tasks_str = json.dumps(tasks, ensure_ascii=False, indent=2)
        
        # Construct the final prompt
        # We assume the user_template has placeholders like {tasks_str}, {time}, {tags}
        # But looking at the user request image, it seems the user template might be fixed or I need to inject variables.
        # The original code injected {tasks_str} and {tags_instruction} into a f-string.
        # I should try to replace placeholders if they exist in the fetched template.
        # Or simply append the data.
        
        # Strategy: Inject variables into the fetched template
        final_prompt = f"{user_template}\n\n{system_prompt}"
        final_prompt = final_prompt.replace("{time}", self._get_vn_time())
        final_prompt = final_prompt.replace("{tasks_str}", tasks_str)
        final_prompt = final_prompt.replace("{tags}", tags_instruction)
        
        # If the Notion prompt doesn't use placeholders, we might need to conform the Notion Prompt to this expectation
        # Or strictly follow the format: System Prompt + Context + Template.
        
        # For now, let's assume the user put the text as shown in the file I read earlier
        # which had: "Thời gian hiện tại: {self._get_vn_time()} ... {tasks_str}"
        # So I will do a textual replacement.
        
        return self.generate_content(final_prompt, model=model)

    def generate_voice_script(self, original_text):
        """Rewrites text for voice generation using Notion prompt."""
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "voice_script")
        
        if not prompt_data:
            return "Error: Could not fetch voice script prompt."
            
        system_prompt = prompt_data["system_prompt"]
        user_template = prompt_data["user_template"]
        model = prompt_data["model"]
        
        final_prompt = f"{user_template}\n\n{system_prompt}"
        final_prompt = final_prompt.replace("{time}", self._get_vn_time())
        final_prompt = final_prompt.replace("{user_label}", "Khôi") # Hardcoded user name for now
        final_prompt = final_prompt.replace("{original_text}", original_text)
        
        return self.generate_content(final_prompt, model=model)

    def generate_quiz(self, content):
        """Generates quiz questions from review notes using Notion prompt."""
        if not content: return "Nội dung trống."

        # Fetch prompt from Notion
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "study_assistant")
        
        if not prompt_data:
            # Fallback if Notion fetch fails
            system_prompt = "Bạn là một Chuyên gia Giáo dục và Trợ lý Học tập Thông minh."
            user_template = "--- NỘI DUNG GHI CHÉP ---\n{content}\n-------------------------"
            model = Config.GEMINI_MODEL_FLASH
            logger.warning("⚠️ Using fallback prompt for generate_quiz")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]
            model = prompt_data["model"]

        # Construct the final prompt
        additional_instructions = """
        QUAN TRỌNG VỀ ĐỊNH DẠNG TOÁN HỌC:
        1. KHÔNG sử dụng định dạng LaTeX (dấu $).
        2. SỬ DỤNG ký tự Unicode để viết công thức (ví dụ: ×, ÷, =, ≈, ≠, ≤, ≥, ², ³, √, ∑, ∫...).
        3. Viết công thức liền mạch với văn bản, dễ đọc trên điện thoại.
        4. Ví dụ: thay vì $A \times B$, hãy viết "Ma trận A nhân ma trận B" hoặc "A × B".
        5. KHÔNG dùng dấu gạch dưới (_) gây lỗi định dạng Telegram.
        """
        
        final_prompt = f"{user_template}\n\n{system_prompt}\n\n{additional_instructions}"
        final_prompt = final_prompt.replace("{content}", content)
        
        return self.generate_content(final_prompt, model=model)
