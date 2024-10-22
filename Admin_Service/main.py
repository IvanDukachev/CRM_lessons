from fastapi import FastAPI

app = FastAPI()

# Пример данных пользователей
users = ["Alice", "Bob", "Charlie"]

@app.get("/users")
async def get_users():
    return users
