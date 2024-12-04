FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY /Admin_Service .
COPY ./Management_Service/schemas.py /app/Management_Service/schemas.py
COPY config.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]