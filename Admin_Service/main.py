from datetime import date, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
import httpx
import requests
import logging
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import redis

from config import (
    API_GATEWAY_URL,
    AUTH_SERVICE_URL,
    REDIS_HOST,
    REDIS_PORT
)


app = FastAPI()

redis_client = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=3)

COOKIE_TTL = 3600

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}


@app.get("courses/{operator_id}")
async def show_all_courses(operator_id: int):
    response = await requests.get(f"{API_GATEWAY_URL}/courses/{operator_id}")
    return response.json()


@app.post("/courses")
async def create_course(
    name: str = Form(...),
    description: str = Form(...),
    price: int = Form(...),
    start_date: List[str] = Form(...),
    end_date: List[str] = Form(...),
    start_time_hour: List[str] = Form(...),
    end_time_hour: List[str] = Form(...),
    user_id: str = Form(...),
):
    course = {
        "name": name,
        "description": description,
        "price": price,
        "operator_id": int(user_id)
    }
    schedule = []
    for start, end, start_time, end_time in zip(
        start_date,
        end_date,
        start_time_hour,
        end_time_hour
    ):
        schedule.append(
            {
                "start_date": start,
                "end_date": end,
                "start_time": start_time,
                "end_time": end_time
            }
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/courses",
            json={
                "course_data": course,
                "schedule_data": schedule
            }
        )

    return {"message": response.json()}


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def admin_login(email: str = Form(...), password: str = Form(...)):
    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "password",
            "username": email,
            "password": password
        }
        response = await client.post(f"{API_GATEWAY_URL}/login", json=data)
        response.raise_for_status()
        auth_cookie = response.json()
        if not auth_cookie:
            raise HTTPException(
                status_code=401,
                detail="Authentication cookie missing"
            )

        logging.error(auth_cookie)
        user_data = await client.get(
            f"{API_GATEWAY_URL}/me",
            params={"auth_cookie": auth_cookie}
        )
        user_data.raise_for_status()
        user = user_data.json()

        redis_client.setex(
            f"user:{user['id']}:auth_cookie",
            COOKIE_TTL,
            auth_cookie
        )

        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie("user_id", user['id'])
        response.set_cookie("username", user['username'])
        response.set_cookie("email", user['email'])
        return response


@app.get("/", response_class=HTMLResponse)
async def user_data_page(request: Request):
    user_detail = {
        "id": request.cookies.get("user_id"),
        "username": request.cookies.get("username"),
        "email": request.cookies.get("email"),
        "password": request.cookies.get("password")
    }
    return templates.TemplateResponse(
        "page_1.html",
        {
            "request": request,
            "active_page": 1,
            "user": user_detail
        }
    )


@app.get("/create-course", response_class=HTMLResponse)
async def create_course_page(request: Request):
    user_id = request.cookies.get("user_id")
    current_date = date.today()
    tomorrow_date = (current_date + timedelta(days=1)).isoformat()
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return templates.TemplateResponse(
        "page_2.html",
        {
            "request": request,
            "active_page": 2,
            "user": user_id,
            "tomorrow_date": tomorrow_date
        }
    )


@app.get("/my-courses", response_class=HTMLResponse)
async def my_courses_page(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_GATEWAY_URL}/courses_by_operator/{user_id}"
        )
        courses = response.json()
    return templates.TemplateResponse(
        "page_3.html",
        {
            "request": request,
            "active_page": 3,
            "courses": courses,
            "user": user_id
        }
    )


@app.get("/edit-course/{course_id}", response_class=HTMLResponse)
async def edit_course_page(request: Request, course_id: int):
    async with httpx.AsyncClient() as client:
        course = await client.get(f"{API_GATEWAY_URL}/courses/{course_id}")

    return templates.TemplateResponse(
        "course.html",
        {
            "request": request,
            "details": course.json()[0]
        }
    )


@app.post("/edit-course/{course_id}")
async def edit_course(
    course_id: int,
    name: str = Form(...),
    description: str = Form(...)
):
    course_data = {
        "name": name,
        "description": description
    }
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{API_GATEWAY_URL}/courses/{course_id}",
            json=course_data
        )


@app.post("/update-user")
async def update_user(
    user_id: str = Form(...),
    username: Optional[str] = Form(""),
    email: Optional[str] = Form(""),
    password: Optional[str] = Form("")
):
    auth_cookie = redis_client.getex(f"user:{user_id}:auth_cookie")
    auth_cookie = (
        auth_cookie.decode()
        if isinstance(auth_cookie, bytes)
        else auth_cookie
    )
    logging.error(f"auth_cookie: {auth_cookie}")
    update_data = {
        "username": username if username else None,
        "email": email if email else None,
        "password": password if password else None,
    }

    filtered_data = {
        key: value
        for key, value in update_data.items()
        if value is not None
    }

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{AUTH_SERVICE_URL}/users/me",
            json=filtered_data,
            cookies={"fastapiusersauth": auth_cookie}

        )
    return response.json()


@app.get("/calendar_courses", response_class=HTMLResponse)
async def calendar_courses(request: Request):
    user_id = request.cookies.get("user_id")
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user_id
        }
    )


@app.get("/schedule/{user_id}")
async def get_schedule(user_id: str):
    schedule_data = []
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_GATEWAY_URL}/courses_by_operator/{user_id}"
        )
        for course in response.json():
            course_id = course['id']
            course_schedule = await client.get(
                f"{API_GATEWAY_URL}/courses_schedule_operator/{course_id}"
            )
            schedule_data += course_schedule.json()['schedule']
    logging.error(schedule_data)
    return schedule_data
