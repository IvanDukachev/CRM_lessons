from fastapi import FastAPI
import httpx

app = FastAPI()

USER_SERVICE_URL = "http://management_service:8004"
NOTIFICATION_SERVICE_URL = "http://notification_service:8005"

@app.get("/users")
async def get_users():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/users")
        return response.json()

@app.post("/send_notification")
async def send_notification(message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NOTIFICATION_SERVICE_URL}/notify", 
            json={"message": message}
        )
        return response.json()
