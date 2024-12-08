from fastapi import HTTPException
import httpx

from config import ENROLLING_SERVICE_URL, MANAGEMENT_SERVICE_URL
from Enrolling_Service.schemas import EnrollCreate


async def create_enroll_for_user(request: EnrollCreate):
    """
    Запись пользователя на курс

    Отправляет запрос к enrolling service 
    для записи пользователя на курс

    Args:
        request (EnrollCreate): информация о записи,
        включающая user_id, course_id, и schedule_id

    Returns:
        dict: ответ от enrolling service в случае успеха

    Raises:
        HTTPException: если произошла ошибка при записи на курс
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ENROLLING_SERVICE_URL}/enroll",
                json={
                    "user_id": request.user_id,
                    "course_id": request.course_id,
                    "schedule_id": request.schedule_id
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Ошибка при записи на курс"
                )
        except httpx.RequestError as e:
            print(f"Error occurred while making request: {e}")
            raise HTTPException(
                status_code=500,
                detail="Ошибка соединения с Management Service"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Неизвестная ошибка {e}"
            )


async def fetch_enroll_by_user_id(user_id: int):
    """
    Получение списка записей для заданного user_id

    Args:
        user_id (int): ID пользователя,
        для которого нужно получить его записи на курсы

    Returns:
        list: список словарей,
        содержащий информацию о записях пользователя на курсы,
        включая название курса
    """
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENROLLING_SERVICE_URL}/enroll",
            params={"user_id": user_id}
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Время для выбранной даты не найдено"
            )
        enrolls = response.json()
        courses = {}
        for enroll in enrolls:
            course_id = enroll["course_id"]
            if course_id not in courses:
                course_response = await client.get(
                    f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}"
                )
                if course_response.status_code == 200:
                    courses[course_id] = course_response.json()[0]["name"]
                else:
                    courses[course_id] = {
                        "name": f"Неизвестный курс (ID {course_id})"
                    }
        for enroll in enrolls:
            course_id = enroll["course_id"]
            enroll["course_name"] = courses[course_id]
        return enrolls


async def delete_enroll_for_user(enroll_id: int):
    """
    Удаление записи на курс для пользователя

    Args:
        enroll_id (int): ID записи на курс

    Raises:
        HTTPException: Если произошла ошибка при удалении записи
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{ENROLLING_SERVICE_URL}/enroll/{enroll_id}"
        )
        if response.status_code == 200:
            return
        raise HTTPException(
            status_code=response.status_code,
            detail="Время для выбранной даты не найдено"
        )


async def fetch_enroll_by_schedule_id(schedule_id: int):
    
    """
    Получение списка пользователей, записанных на курс на определенные
    время и дату

    Args:
        schedule_id (int): ID расписания курса

    Returns:
        dict: словарь со списком пользователей
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENROLLING_SERVICE_URL}/enroll/{schedule_id}"
        )
    return response.json()
