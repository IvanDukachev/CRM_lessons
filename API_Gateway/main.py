from fastapi import FastAPI
import httpx

from config import MANAGEMENT_SERVICE_URL, NOTIFICATION_SERVICE_URL

app = FastAPI()

@app.get("/users")
async def get_users():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MANAGEMENT_SERVICE_URL}/users")
        return response.json()

@app.post("/send_notification")
async def send_notification(message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NOTIFICATION_SERVICE_URL}/notify", 
            json={"message": message}
        )
        return response.json()
