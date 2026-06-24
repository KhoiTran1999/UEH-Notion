from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.services.study_logic import get_candidates, generate_quiz, update_status
from src.jobs.daily_report import run_daily_report
from src.services.telegram import TelegramService
from src.config.settings import Config
import json

app = FastAPI(title="Study Quiz API")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuizRequest(BaseModel):
    topic_id: str
    force_refresh: bool = False

class StatusRequest(BaseModel):
    topic_id: str
    status: str | None = None

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    """Health check endpoint for UptimeRobot"""
    return {"status": "alive"}

@app.get("/api/study/candidates")
def api_get_candidates():
    try:
        candidates = get_candidates()
        return {"candidates": candidates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/study/quiz")
def api_generate_quiz(request: QuizRequest):
    try:
        quiz_data = generate_quiz(request.topic_id, force_refresh=request.force_refresh)
        if not quiz_data:
            raise HTTPException(status_code=404, detail="Topic not found or content empty")
        return quiz_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/study/status")
def api_update_status(request: StatusRequest):
    success = update_status(request.topic_id, request.status)
    if success:
        return {"success": True, "message": "Status updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update status")

class ReportRequest(BaseModel):
    telegram_id: str | None = None

@app.post("/api/tasks/report")
def api_generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_report)
    return {"success": True, "message": "Report generation started"}

def process_telegram_command(text: str, chat_id: str, background_tasks: BackgroundTasks):
    telegram = TelegramService()
    if text in ["/start", "/help"]:
        telegram.send_message(
            "✅ Bot đã sẵn sàng!\nChọn chức năng bên dưới hoặc gõ lệnh tương ứng:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📊 Báo cáo Task", "callback_data": "/taskreport"}],
                    [{"text": "🎓 Ôn tập khắc sâu", "web_app": {"url": Config.WEBAPP_URL}}]
                ]
            }
        )
    elif text == "/taskreport":
        telegram.send_message("🚀 Đã nhận lệnh! Bắt đầu tạo báo cáo ngày cho bạn...")
        background_tasks.add_task(run_daily_report)
    elif text == "/study":
        telegram.send_message(
            "📚 Mở góc ôn tập bằng Web App bên dưới nhé:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "Mở Góc Ôn Tập", "web_app": {"url": Config.WEBAPP_URL}}]
                ]
            }
        )
    elif text.startswith("/study_") or text.startswith("/mastered_") or text.startswith("/review_"):
        telegram.send_message("⚠️ Chức năng này hiện được xử lý qua Web App.")

@app.post("/webhook/telegram")
@app.post("/webhook/telegram/")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        update = await request.json()
    except json.JSONDecodeError:
        return {"status": "error"}

    if "callback_query" in update:
        chat_id = str(update["callback_query"]["message"]["chat"]["id"])
        data = update["callback_query"]["data"]
        cb_id = update["callback_query"]["id"]

        TelegramService().answer_callback_query(cb_id)
        process_telegram_command(data, chat_id, background_tasks)
    elif "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"].strip()
        process_telegram_command(text, chat_id, background_tasks)

    return {"status": "ok"}
