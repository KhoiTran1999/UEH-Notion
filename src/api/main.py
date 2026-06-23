from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.services.study_logic import get_candidates, generate_quiz, update_status
from src.jobs.daily_report import run_daily_report

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
