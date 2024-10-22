from fastapi import FastAPI

app = FastAPI()

@app.post("/notify")
async def notify(message: str):
    print(f"Уведомление: {message}")
    return {"status": "success", "message": "Уведомление отправлено."}
