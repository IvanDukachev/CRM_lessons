import asyncio
from celery import Celery
from main import send_notification_to_user


celery_app = Celery('tasks', broker='redis://redis:6379/1')


@celery_app.task(name='tasks.send_message_task')
def send_notification(schedule_id: int, course_id: int) -> str:
    """
    Задача для отправки уведомления пользователям о предстоящем курсе.

    Args:
        schedule_id (int): Идентификатор расписания курса.
        course_id (int): Идентификатор курса.

    Returns:
        str: Сообщение об успешной отправке или причине неудачи.
    """
    try:
        loop = asyncio.get_event_loop()

        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(
            send_notification_to_user(schedule_id, course_id)
        )
        return f"Message sent to {schedule_id}"
    except Exception as e:
        return f"Failed to send message to {schedule_id}: {e}"
