FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY /API_Gateway .
COPY config.py .  
COPY ./Enrolling_Service/schemas.py /app/Enrolling_Service/schemas.py
COPY ./Management_Service/schemas.py /app/Management_Service/schemas.py
COPY ./Auth_Service/schemas.py /app/Auth_Service/schemas.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]