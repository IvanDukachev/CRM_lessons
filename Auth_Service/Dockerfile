FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY /Auth_Service .
COPY config.py .
COPY database.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]