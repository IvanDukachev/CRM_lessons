import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST=os.getenv("DB_HOST")
DB_PORT=os.getenv("DB_PORT")
DB_NAME=os.getenv("DB_NAME")
DB_USER=os.getenv("DB_USER")
DB_PASS=os.getenv("DB_PASS")
REDIS_HOST=os.getenv("REDIS_HOST")
REDIS_PORT=os.getenv("REDIS_PORT")
API_GATEWAY_URL=os.getenv("API_GATEWAY_URL")
AUTH_SERVICE_URL=os.getenv("AUTH_SERVICE_URL")
ENROLLING_SERVICE_URL=os.getenv("ENROLLING_SERVICE_URL")
MANAGEMENT_SERVICE_URL=os.getenv("MANAGEMENT_SERVICE_URL")
NOTIFICATION_SERVICE_URL=os.getenv("NOTIFICATION_SERVICE_URL")
TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
