from fastapi import APIRouter

from services.auth import user_login, user_verify
from Auth_Service.schemas import LoginRequest


router = APIRouter()


@router.post("/login")
async def login(request: LoginRequest):
    return await user_login(request)


@router.get("/me")
async def user_me(auth_cookie: str):
    return await user_verify(auth_cookie)
