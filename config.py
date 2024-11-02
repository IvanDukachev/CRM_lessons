import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
API_GATEWAY_URL=os.getenv("API_GATEWAY_URL")
TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
MANAGEMENT_SERVICE_URL = "http://management_service:8004"
NOTIFICATION_SERVICE_URL = "http://notification_service:8005"