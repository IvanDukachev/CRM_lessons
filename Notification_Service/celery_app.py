from celery import Celery

# Настроим Celery с использованием Redis как брокера сообщений
app = Celery('notification_service', broker='redis://redis:6379/1')

# Конфигурация Celery
app.conf.update(
    result_backend='redis://redis:6379/2',
    task_serializer='json',
    accept_content=['json'],
)