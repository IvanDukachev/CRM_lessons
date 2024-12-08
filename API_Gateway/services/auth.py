import httpx

from config import AUTH_SERVICE_URL
from Auth_Service.schemas import LoginRequest


async def user_login(request: LoginRequest):
    """
    Осуществляет вход в систему и возвращает куки оператора

    Args:
        request (LoginRequest): информация о пользователе,
        включащая в себя email, пароль и grant_type

    Returns:
        str: "fastapiusersauth" куки, полученные при входе в систему
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/auth/jwt/login",
            data=request.model_dump()
        )
    return response.cookies.get("fastapiusersauth")


async def user_verify(auth_cookie: str):
    """
    Получение данных о текущем операторе

    Args:
        auth_cookie (str): "fastapiusersauth" куки оператора,
        полученные при входе в систему

    Returns:
        dict: id, email and is_superuser поля о текущем операторе
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/users/me",
            cookies={"fastapiusersauth": auth_cookie}
        )
    return response.json()
