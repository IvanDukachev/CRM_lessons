# Используем официальный базовый образ Python
FROM python:3.12-slim

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения в контейнер
COPY /Telegram_Bot .
COPY config.py .

# Определяем команду для запуска приложения
CMD ["python", "main.py"]