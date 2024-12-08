import pytest
from httpx import AsyncClient

from config import ENROLLING_SERVICE_URL, MANAGEMENT_SERVICE_URL


course_id = None
enroll_id = None
schedule_id = None
user_id = 1


@pytest.mark.asyncio
async def test_create_course():
    global course_id, schedule_id
    course_data = {
        "name": "Java 3.0",
        "description": "asdgadfg",
        "price": 10032,
        "operator_id": 1
    }
    schedule_data = [
        {
            "start_date": "2024-12-10",
            "end_date": "2024-12-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00"
        }
    ]
    async with AsyncClient(base_url=MANAGEMENT_SERVICE_URL) as client:
        response = await client.post(
            "/courses",
            json={"course_data": course_data, "schedule_data": schedule_data}
        )
        assert response.status_code == 200
        response_data = response.json()
        course_id = response_data["course_id"]
        schedule_id = response_data["schedule_ids"][0]
        assert response_data["message"] == "Course and schedules processed successfully"
        assert len(response_data["valid_schedules"]) == 1

@pytest.mark.asyncio
async def test_get_course_by_id():
    global course_id
    async with AsyncClient(base_url=MANAGEMENT_SERVICE_URL) as client:
        response = await client.get(f"/courses/{course_id}")
        assert response.status_code == 200
        course_data = response.json()
        assert len(course_data) > 0
        assert course_data[0]["id"] == course_id



@pytest.mark.asyncio
async def test_enroll_user():
    global course_id, schedule_id, enroll_id
    enroll_data = {
        "user_id": user_id,
        "course_id": course_id,
        "schedule_id": schedule_id
    }

    async with AsyncClient(base_url=ENROLLING_SERVICE_URL) as client:
        response = await client.post("/enroll", json=enroll_data)
        enroll_id = response.json()["enroll_id"]
        assert response.status_code == 200
        assert response.json()["message"] == "Пользователь успешно зарегистрирован на курс"


@pytest.mark.asyncio
async def test_get_enrollments():
    async with AsyncClient(base_url=ENROLLING_SERVICE_URL) as client:
        response = await client.get("/enroll", params={"user_id": user_id})
        assert response.status_code == 200
        enrollments = response.json()
        assert len(enrollments) > 0
        for enrollment in enrollments:
            assert enrollment["user_id"] == user_id


@pytest.mark.asyncio
async def test_delete_enrollment():
    global enroll_id
    async with AsyncClient(base_url=ENROLLING_SERVICE_URL) as client:
        response = await client.delete(f"/enroll/{enroll_id}")
        assert response.status_code == 200
        response = await client.get("/enroll", params={"user_id": 1})
        assert response.status_code == 200
        assert not any(e["id"] == enroll_id for e in response.json())

@pytest.mark.asyncio
async def test_delete_course():
    async with AsyncClient(base_url=MANAGEMENT_SERVICE_URL) as client:
        response = await client.delete(f"/courses/{course_id}")
        assert response.status_code == 200
        response = await client.get(f"/courses/{course_id}")
        assert response.status_code == 200
        assert response.json() == []