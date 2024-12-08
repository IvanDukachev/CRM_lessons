from fastapi import FastAPI, HTTPException
import httpx
import logging
from typing import List

from config import (
    AUTH_SERVICE_URL,
    MANAGEMENT_SERVICE_URL,
    ENROLLING_SERVICE_URL
)
from Enrolling_Service.schemas import EnrollCreate
from Auth_Service.schemas import LoginRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/courses")
async def get_courses(user_id: int):
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


@app.put("/courses/{course_id}")
async def update_course(course_id: int, course_data: dict):
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}",
            json=course_data
        )


@app.get("/courses/{course_id}")
async def get_course_details(course_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses/{course_id}"
        )
        return response.json()


@app.get("/courses_by_operator/{user_id}")
async def get_courses_by_operator(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses_by_operator/{user_id}"
        )
        return response.json()


@app.get("/courses_schedule_operator/{course_id}")
async def get_course_schedule_operator(course_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses_schedule_operator/{course_id}"
        )
        return response.json()


@app.get("/courses/{course_id}/schedule")
async def get_course_schedule(course_id: int):
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


@app.get("/courses_schedule/{schedule_id}")
async def get_course_by_schedule_id(schedule_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MANAGEMENT_SERVICE_URL}/courses_schedule/{schedule_id}"
        )
        return response.json()


@app.get("/courses/{course_id}/times")
async def get_course_times(course_id: int, date: str):
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


@app.post("/enroll")
async def user_enroll(request: EnrollCreate):
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


@app.get("/enroll")
async def get_user_enroll(user_id: int):
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


@app.delete("/enroll/{schedule_id}")
async def delete_enroll_for_user(schedule_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{ENROLLING_SERVICE_URL}/enroll/{schedule_id}"
        )
        if response.status_code == 200:
            return
        raise HTTPException(
            status_code=response.status_code,
            detail="Время для выбранной даты не найдено"
        )


@app.post("/login")
async def login(request: LoginRequest):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/auth/jwt/login",
            data=request.model_dump()
        )
    return response.cookies.get("fastapiusersauth")


@app.get("/me")
async def user_me(auth_cookie: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/users/me",
            cookies={"fastapiusersauth": auth_cookie}
        )
    return response.json()


@app.post("/courses")
async def create_course(
    course_data: dict,
    schedule_data: List[dict]
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MANAGEMENT_SERVICE_URL}/courses",
            json={
                "course_data": course_data,
                "schedule_data": schedule_data
            }
        )

    return response.json()


@app.get("/enroll/{schedule_id}")
async def get_enroll_by_schedule_id(schedule_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENROLLING_SERVICE_URL}/enroll/{schedule_id}"
        )
    return response.json()