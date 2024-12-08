from typing import List
from fastapi import APIRouter

from services.courses import (
    create_new_course,
    fetch_course_by_schedule,
    fetch_course_schedule,
    fetch_course_schedule_for_operator,
    fetch_course_times,
    fetch_courses_for_operator,
    fetch_courses_for_user,
    update_course_by_id,
    fetch_course_by_id,
)


router = APIRouter()


@router.get("/")
async def get_courses(user_id: int):
    return await fetch_courses_for_user(user_id)


@router.put("/{course_id}")
async def update_course(course_id: int, course_data: dict):
    await update_course_by_id(course_id, course_data)


@router.get("/{course_id}")
async def get_course_details(course_id: int):
    return await fetch_course_by_id(course_id)


@router.get("/operator/{operator_id}")
async def get_courses_by_operator(operator_id: int):
    return await fetch_courses_for_operator(operator_id)


@router.get("/schedule/operator/{course_id}")
async def get_course_schedule_operator(course_id: int):
    return await fetch_course_schedule_for_operator(course_id)


@router.get("/{course_id}/schedule")
async def get_course_schedule(course_id: int):
    return await fetch_course_schedule(course_id)


@router.get("/schedule/{schedule_id}")
async def get_course_by_schedule_id(schedule_id: int):
    return await fetch_course_by_schedule(schedule_id)


@router.get("/{course_id}/times")
async def get_course_times(course_id: int, date: str):
    return await fetch_course_times(course_id, date)


@router.post("/")
async def create_course(course_data: dict, schedule_data: List[dict]):
    return await create_new_course(course_data, schedule_data)


