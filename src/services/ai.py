import json
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from src.config.settings import Config
from src.utils.logger import logger

from src.services.prompt_service import PromptService
from src.services.telegram import TelegramService
from src.services.notion import NotionService

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

    def generate_content(self, prompt, model=Config.MODEL_WORKER):
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

    def _execute_tool(self, name, arguments):
        logger.info(f"[Tool] Execution: {name} with args {arguments}")
        try:
            if name == "fetch_notion_tasks":
                notion = NotionService()
                tasks = notion.get_tasks()
                return json.dumps(tasks, ensure_ascii=False)
            elif name == "fetch_notion_review_notes":
                notion = NotionService()
                notes = notion.get_review_notes()
                simplified_notes = []
                for note in notes:
                    title = "Unknown Note"
                    for key, val in note.get("properties", {}).items():
                        if val.get("type") == "title" and val["title"]:
                            title = val["title"][0]["plain_text"]
                            break
                    simplified_notes.append({
                        "id": note["id"],
                        "title": title
                    })
                return json.dumps(simplified_notes, ensure_ascii=False)
            elif name == "fetch_notion_page_content":
                page_id = arguments.get("page_id")
                if not page_id:
                    return "Error: page_id is required"
                notion = NotionService()
                content = notion.fetch_page_content(page_id)
                return json.dumps(content, ensure_ascii=False)
            elif name == "delegate_to_worker":
                instruction = arguments.get("instruction")
                if not instruction:
                    return "Error: instruction is required"
                result = self.generate_content(instruction, model=Config.MODEL_WORKER)
                return result
            else:
                return f"Error: Tool {name} not found"
        except Exception as e:
            logger.error(f"[Error] executing tool {name}: {e}")
            return f"Error executing tool: {str(e)}"

    def run_agent(self, system_prompt, user_prompt, model=Config.MODEL_BRAIN):
        """Runs MODEL_BRAIN as an agent with access to tools."""
        if not self.client: return "AI Service Unavailable"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_notion_tasks",
                    "description": "Lấy danh sách tất cả các nhiệm vụ (tasks) hiện tại chưa hoàn thành (trạng thái 'Not started' hoặc 'In progress') từ cơ sở dữ liệu Notion của người dùng. Trả về mảng các đối tượng chứa: tên nhiệm vụ, hạn chót, trạng thái, loại nhiệm vụ, và độ ưu tiên. Thích hợp dùng khi lập kế hoạch ngày hoặc báo cáo tiến độ."
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_notion_review_notes",
                    "description": "Lấy danh sách các bài học hoặc ghi chép học tập cần ôn tập (có trạng thái 'Cần xem lại' / '🔴 Cần xem lại') từ cơ sở dữ liệu Notion. Trả về mảng các trang chứa ID và tiêu đề trang. Dùng để xác định bài học nào cần làm trắc nghiệm ôn tập."
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_notion_page_content",
                    "description": "Tải toàn bộ nội dung chi tiết của một trang Notion cụ thể (dựa vào page_id). Trả về danh sách các chuỗi văn bản (các khối nội dung) đã được định dạng cơ bản. Phải dùng tool này để lấy nội dung bài viết trước khi biên soạn câu hỏi trắc nghiệm hoặc phân tích sâu nội dung bài học.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "ID của trang Notion cần đọc nội dung."
                            }
                        },
                        "required": ["page_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_worker",
                    "description": "Ủy quyền/Giao việc cho mô hình phụ (MODEL_WORKER) để thực hiện các tác vụ xử lý văn bản cơ bản không đòi hỏi tư duy logic phức tạp hay đưa ra quyết định hệ thống. Các việc phù hợp: tóm tắt văn bản dài, viết kịch bản đọc giọng nói (voice script) từ bản tóm tắt, định dạng văn bản thành Markdown/HTML, dịch ngôn ngữ, trích xuất dữ liệu thô. KHÔNG giao cho Worker các việc như tự quyết định chọn bài học, tự phân tích chiến lược, hoặc tự tổng hợp kế hoạch ngày lớn.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instruction": {
                                "type": "string",
                                "description": "Yêu cầu chi tiết, chỉ dẫn định dạng và đầy đủ dữ liệu/ngữ cảnh đầu vào để MODEL_WORKER thực hiện độc lập mà không cần hỏi lại."
                            }
                        },
                        "required": ["instruction"]
                    }
                }
            }
        ]

        max_steps = 10
        step = 0
        try:
            while step < max_steps:
                step += 1
                logger.info(f"[Agent] Loop Step {step} calling model...")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    stream=False
                )

                choice = response.choices[0]
                message = choice.message
                messages.append(message)

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except Exception as e:
                            logger.error(f"Failed to parse tool arguments: {e}")
                            tool_args = {}

                        tool_result = self._execute_tool(tool_name, tool_args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result
                        })
                else:
                    content = message.content
                    if not content:
                        raise ValueError("Empty response from AI Agent")
                    return content.strip()

            logger.error("[Error] Agent exceeded max tool call steps.")
            return "Error: Agent loop exceeded maximum steps."

        except Exception as e:
            logger.error(f"[Error] Agent Execution Error: {e}")
            self.telegram.send_message(f"❌ Lỗi khi chạy AI Agent: {str(e)}", disable_notification=True)
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
            logger.warning("⚠️ Using fallback prompt for analyze_tasks")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]

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

        user_prompt = user_template
        user_prompt = user_prompt.replace("{time}", self._get_vn_time())
        user_prompt = user_prompt.replace("{tasks_str}", tasks_str)
        user_prompt = user_prompt.replace("{tags}", tags_instruction)

        agent_system_prompt = (
            f"{system_prompt}\n\n"
            "QUY TẮC PHÂN CHIA VAI TRÒ:\n"
            "- Bạn là MODEL_BRAIN: Chịu trách nhiệm thực hiện các tác vụ tư duy, tính toán, lên kế hoạch, lập luận logic và sáng tạo.\n"
            "- Bạn có quyền điều phối MODEL_WORKER thông qua công cụ `delegate_to_worker` để xử lý các việc không cần suy nghĩ sâu như: tóm tắt văn bản thô, trích xuất thông tin đơn giản, định dạng lại dữ liệu thành Markdown/HTML, hoặc xử lý chuyển đổi chữ viết.\n"
            "Hãy giữ vai trò điều phối tối cao, tập trung tư duy chiến lược và giao phó triệt để việc cơ khí cho MODEL_WORKER."
        )

        return self.run_agent(system_prompt=agent_system_prompt, user_prompt=user_prompt, model=Config.MODEL_BRAIN)

    def generate_voice_script(self, original_text):
        """Rewrites text for voice generation using Notion prompt."""
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "voice_script")

        if not prompt_data:
            return "Error: Could not fetch voice script prompt."

        system_prompt = prompt_data["system_prompt"]
        user_template = prompt_data["user_template"]

        final_prompt = f"{user_template}\n\n{system_prompt}"
        final_prompt = final_prompt.replace("{time}", self._get_vn_time())
        final_prompt = final_prompt.replace("{user_label}", "Khôi") # Hardcoded user name for now
        final_prompt = final_prompt.replace("{original_text}", original_text)

        # Voice script generation is a simple text rewriting job - run it directly on MODEL_WORKER
        return self.generate_content(final_prompt, model=Config.MODEL_WORKER)

    def generate_quiz(self, content):
        """Generates quiz questions from review notes using Notion prompt."""
        if not content: return "Nội dung trống."

        # Fetch prompt from Notion
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "study_assistant")

        if not prompt_data:
            # Fallback if Notion fetch fails
            system_prompt = "Bạn là một Chuyên gia Giáo dục và Trợ lý Học tập Thông minh."
            user_template = "--- NỘI DUNG GHI CHÉP ---\n{content}\n-------------------------"
            logger.warning("⚠️ Using fallback prompt for generate_quiz")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]

        # Construct the final prompt
        additional_instructions = """
        QUAN TRỌNG VỀ ĐỊNH DẠNG TOÁN HỌC:
        1. SỬ DỤNG định dạng LaTeX (kẹp giữa ký tự $ cho công thức cùng dòng và $$ cho công thức nằm riêng dòng) để viết các công thức toán học, tài chính, thống kê, ma trận phức tạp.
        2. Đảm bảo cú pháp LaTeX chính xác và chuẩn chỉnh để bộ thư viện KaTeX có thể render được.
        3. Đối với các biểu thức cực kỳ đơn giản, có thể dùng ký tự thường hoặc Unicode nếu muốn, nhưng ưu tiên sử dụng LaTeX ($...$) cho các công thức, ký hiệu toán học để hiển thị chuyên nghiệp nhất.
        """

        user_prompt = user_template.replace("{content}", content)
        agent_system_prompt = (
            f"{system_prompt}\n\n{additional_instructions}\n\n"
            "QUY TẮC PHÂN CHIA VAI TRÒ:\n"
            "- Bạn là MODEL_BRAIN: Tập trung hoàn toàn vào việc tư duy, phân tích kiến thức sâu, tính toán bài tập, sáng tạo các câu hỏi trắc nghiệm chất lượng.\n"
            "- Bạn có công cụ `delegate_to_worker` để sai khiến MODEL_WORKER làm việc cơ học như: trích xuất từ khóa thô từ bài học, định dạng lại công thức hoặc cấu trúc đề thi thô, hay tóm tắt sơ bộ.\n"
            "Hãy giữ vai trò thiết kế và tư duy logic, giao phó việc định dạng hoặc xử lý dữ liệu thô cho MODEL_WORKER."
        )

        return self.run_agent(system_prompt=agent_system_prompt, user_prompt=user_prompt, model=Config.MODEL_BRAIN)
