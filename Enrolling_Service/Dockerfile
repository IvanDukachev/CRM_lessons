FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./Enrolling_Service .
COPY ./Management_Service/models.py /app/Management_Service/models.py
COPY ./Auth_Service/models.py /app/Auth_Service/models.py
COPY database.py .
COPY config.py .
COPY conftest.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]