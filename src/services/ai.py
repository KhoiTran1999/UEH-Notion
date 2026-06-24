import json
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from src.config.settings import Config
from src.utils.logger import logger

from src.services.prompt_service import PromptService
from src.services.telegram import TelegramService

class AIService:
    def __init__(self):
        self.prompt_service = PromptService()
        self.telegram = TelegramService()

        if Config.USE_CUSTOM_AI:
            self.client = OpenAI(
                base_url=Config.CUSTOM_AI_BASE_URL,
                api_key=Config.CUSTOM_AI_API_KEY
            )
        else:
            logger.error("❌ Legacy Gemini config used but google-genai is removed!")
            self.client = None

    def _get_vn_time(self):
        return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    def generate_content(self, prompt, model=Config.CUSTOM_AI_MODEL):
        if not self.client: return "AI Service Unavailable"

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from AI model")
            return content.strip()

        except Exception as e:
            logger.error(f"❌ AI Generation Error: {e}")
            self.telegram.send_message(f"❌ Lỗi khi gọi AI Router: {str(e)}", disable_notification=True)
            return f"Error: {str(e)}"

    def analyze_tasks(self, tasks, db_options=None):
        """Generates the daily report analysis using prompts from Notion."""
        if not tasks:
            return "Chào buổi sáng! 🌞 Hôm nay bạn không có task nào phải làm. Hãy tận hưởng ngày nghỉ nhé! 🚀"

        # Fetch prompt from Notion
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "task_planner")

        if not prompt_data:
            # Fallback if Notion fetch fails (optional, or just error out)
            system_prompt = "Bạn là một Chuyên gia Quản trị năng suất."
            user_template = "Dữ liệu: {tasks_str}. Hãy phân tích."
            model = Config.CUSTOM_AI_MODEL
            logger.warning("⚠️ Using fallback prompt for analyze_tasks")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]
            # Ignore Notion model config to force custom router model, or fallback
            model = Config.CUSTOM_AI_MODEL

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

        final_prompt = f"{user_template}\n\n{system_prompt}"
        final_prompt = final_prompt.replace("{time}", self._get_vn_time())
        final_prompt = final_prompt.replace("{tasks_str}", tasks_str)
        final_prompt = final_prompt.replace("{tags}", tags_instruction)

        return self.generate_content(final_prompt, model=model)

    def generate_voice_script(self, original_text):
        """Rewrites text for voice generation using Notion prompt."""
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "voice_script")

        if not prompt_data:
            return "Error: Could not fetch voice script prompt."

        system_prompt = prompt_data["system_prompt"]
        user_template = prompt_data["user_template"]
        model = Config.CUSTOM_AI_MODEL

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
            model = Config.CUSTOM_AI_MODEL
            logger.warning("⚠️ Using fallback prompt for generate_quiz")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]
            model = Config.CUSTOM_AI_MODEL

        # Construct the final prompt
        additional_instructions = """
        QUAN TRỌNG VỀ ĐỊNH DẠNG TOÁN HỌC:
        1. SỬ DỤNG định dạng LaTeX (kẹp giữa ký tự $ cho công thức cùng dòng và $$ cho công thức nằm riêng dòng) để viết các công thức toán học, tài chính, thống kê, ma trận phức tạp.
        2. Đảm bảo cú pháp LaTeX chính xác và chuẩn chỉnh để bộ thư viện KaTeX có thể render được.
        3. Đối với các biểu thức cực kỳ đơn giản, có thể dùng ký tự thường hoặc Unicode nếu muốn, nhưng ưu tiên sử dụng LaTeX ($...$) cho các công thức, ký hiệu toán học để hiển thị chuyên nghiệp nhất.
        """

        final_prompt = f"{user_template}\n\n{system_prompt}\n\n{additional_instructions}"
        final_prompt = final_prompt.replace("{content}", content)

        return self.generate_content(final_prompt, model=model)
