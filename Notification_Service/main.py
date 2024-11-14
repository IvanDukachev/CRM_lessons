from fastapi import FastAPI
from celery_app import app as celery_app
from celery.result import AsyncResult

app = FastAPI()
# ids = ["798833594", "448664743", "1093243938"]
ids = ["798833594", "1093243938"]
@app.post("/send_notification/")
async def send_notification():
    for id in ids:
        celery_app.send_task('tasks.send_message_task', args=[id, "Hello"])
    return {"status": "Notifications queued"}

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    return {"task_id": task.id, "status": task.status}