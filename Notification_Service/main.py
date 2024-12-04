from fastapi import FastAPI, Body
from celery_app import app as celery_app
from celery.result import AsyncResult
from typing import List
from datetime import datetime, timedelta


app = FastAPI()


@app.post("/send_notification/")
async def send_notification(
    course_id: int = Body(...),
    schedule_ids: List[int] = Body(...),
    schedule_time_str: List[str] = Body(...),
):
    schedule_time = [
        datetime.fromisoformat(time) - timedelta(hours=1)
        for time in schedule_time_str
    ]
    for eta_time, schedule_id in zip(schedule_time, schedule_ids):
        celery_app.send_task(
            'tasks.send_message_task',
            args=[schedule_id, course_id],
            eta=eta_time
        )

    return {
        "status": "Notifications queued",
        "notification_time": schedule_time
    }


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    return {"task_id": task.id, "status": task.status}
