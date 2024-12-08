from fastapi import APIRouter

from services.enroll import (
    fetch_enroll_by_schedule_id,
    fetch_enroll_by_user_id,
    create_enroll_for_user,
    delete_enroll_for_user
)
from Enrolling_Service.schemas import EnrollCreate


router = APIRouter()


@router.get("/")
async def get_user_enroll(user_id: int):
    return await fetch_enroll_by_user_id(user_id)


@router.get("/{schedule_id}")
async def get_enroll_by_schedule_id(schedule_id: int):    
    return await fetch_enroll_by_schedule_id(schedule_id)


@router.post("/")
async def user_enroll(request: EnrollCreate):
    return await create_enroll_for_user(request)


@router.delete("/{enroll_id}")
async def unsubscribe_user(enroll_id: int):
    return await delete_enroll_for_user(enroll_id)
