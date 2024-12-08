from typing import List

from fastapi import HTTPException
import httpx

from config import ENROLLING_SERVICE_URL, MANAGEMENT_SERVICE_URL


async def fetch_courses_for_user(user_id: int):
    """
    Получение списка доступных для записи курсов для пользователя

    Args:
        user_id (int): ID пользователя,
        которому нужно получить доступные курсы

    Returns:
        List[dict]: список словарей с курсами,
        на которые пользователь еще не записан
    """
    async with httpx.AsyncClient() as client:
        courses_response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses"
        )
        courses = courses_response.json()

        enrollments_response = await client.get(
            f"{ENROLLING_SERVICE_URL}/enroll",
            params={"user_id": user_id}
        )
        enrolled_courses = enrollments_response.json()

        enrolled_course_ids = {
            enrollment['course_id'] for enrollment in enrolled_courses
        }
        available_courses = [
            course
            for course in courses
            if course['id'] not in enrolled_course_ids
        ]

        return available_courses


async def update_course_by_id(course_id: int, course_data: dict):
    """
    Обновление курса по его ID

    Args:
        course_id (int): ID курса для обновления
        course_data (dict): информация о курсе для обновления

    Returns:
        None
    """
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}",
            json=course_data
        )


async def fetch_course_by_id(course_id: int):
    """
    Получение информации о курсе

    Args:
        course_id (int): ID курса, 
        для которого нужно получить информацию

    Returns:
        dict: словарь с информацией о курсе
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}"
        )
        return response.json()


async def fetch_courses_for_operator(operator_id: int):
    """
    Получение списка курсов для оператора

    Args:
        operator_id (int): ID оператора которому нужно получить курсы

    Returns:
        List[dict]: список словарей,
        включающий информацию о курсах,
        связанных с указанным оператором
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/operator/{operator_id}"
        )
        return response.json()


async def fetch_course_schedule_for_operator(course_id: int):
    """
    Получение расписания курса для оператора

    Args:
        course_id (int): ID курса для которого нужно получить расписание

    Returns:
        dict: словарь включающий информацию о расписании курса
        для оператора

    Raises:
        HTTPException: if the course schedule is not found
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/schedule/operator/{course_id}"
        )
        return response.json()


async def fetch_course_schedule(course_id: int):
    """
    Получение расписания курса

    Args:
        course_id (int): ID курса, для которого
        нужно получить расписание 

    Returns:
        dict: словарь, включающий информацию о расписании курса

    Raises:
        HTTPException: если расписание для курса не было найдено
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}/schedule"
        )
        if response.status_code == 200:
            return response.json()
        raise HTTPException(
            status_code=response.status_code,
            detail="Расписание для курса не найдено"
        )


async def fetch_course_by_schedule(schedule_id: int):
    """
    Получение деталей курса по ID расписания

    Args:
        schedule_id (int): ID расписание

    Returns:
        dict: детали курса

    Raises:
        HTTPException: если курс с переданным ID расписания не найден
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/schedule/{schedule_id}"
        )
        return response.json()


async def fetch_course_times(course_id: int, date: str):
    """
    Получение доступных времен для заданного курса на заданную дату

    Args:
        course_id (int): ID курса
        date (str): дата курса в формате 'YYYY-MM-DD'

    Returns:
        List[Mapping]: список маппингов, каждый содержит начальное и
        конечное время свободного времени

    Raises:
        HTTPException: если нет доступного времени у
        курса для выбранной даты
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}/times",
            params={"date": date}
        )
        if response.status_code == 200:
            return response.json()
        raise HTTPException(
            status_code=response.status_code,
            detail="Время для выбранной даты не найдено"
        )


async def create_new_course(
        course_data: dict,
        schedule_data: List[dict]
):
    """
    Создание нового курса с расписанием

    Args:
        course_data (dict): информация о курсе для его создания
        schedule_data (List[dict]): список расписаний для курса

    Returns:
        dict: Словарь с информацией о созданном курсе
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MANAGEMENT_SERVICE_URL}/courses",
            json={
                "course_data": course_data,
                "schedule_data": schedule_data
            }
        )

    return response.json()
