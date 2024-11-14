FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./Management_Service .
COPY ./Auth_Service/models.py /app/Auth_Service/models.py
COPY database.py .
COPY config.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]