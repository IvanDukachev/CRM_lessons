import asyncio
from celery import Celery
from main import send_notification_to_user  # Импортируем функцию отправки уведомлений из bot.py


celery_app = Celery('tasks', broker='redis://redis:6379/1')

@celery_app.task(name='tasks.send_message_task')
def send_notification(user_id: int, message: str):
    try:
        asyncio.run(send_notification_to_user(user_id, message))
        return f"Message sent to {user_id}"
    except Exception as e:
        return f"Failed to send message to {user_id}: {e}"
