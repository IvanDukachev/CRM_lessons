import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi_users.exceptions import InvalidPasswordException, UserNotExists
from pydantic import BaseModel
from fastapi_users.password import PasswordHelper

from auth_database import User
from schemas import UserCreate, UserRead, UserUpdate
from manager import (
    auth_backend,
    current_active_user,
    fastapi_users,
    get_user_manager
)


app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    email: str
    password: str


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

password_helper = PasswordHelper()


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


@app.post("/auth/login")
async def login_user(
    login_request: LoginRequest,
    user_manager: User = Depends(get_user_manager),
):
    try:
        user = await user_manager.user_db.get_by_email(login_request.email)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        logging.error(f"{user.id} {user.email} {user.hashed_password}")
        valid = await user_manager.password_helper.verify(
            login_request.password,
            user.hashed_password
        )
        if not valid:
            raise HTTPException(status_code=400, detail="Invalid password")

        return {
            "id": user.id,
            "username": user.email
        }
    except (UserNotExists, InvalidPasswordException) as e:
        raise HTTPException(status_code=400, detail=str(e))
