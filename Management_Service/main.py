import logging
from typing import List
from fastapi import Depends, FastAPI,  HTTPException
from sqlalchemy import join, select, insert, delete, update, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
import httpx

from database import get_async_session
from schemas import CourseCreate, CourseUpdate, ScheduleCreate
from models import course, schedule_course


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/courses")
async def get_courses(session: AsyncSession=Depends(get_async_session)):
    """
    Retrieve a list of courses that have not yet started.

    This endpoint joins the `course` and `schedule_course` tables to filter out courses 
    whose schedules have a start date greater than today's date. It returns a distinct list
    of such courses.

    Args:
        session (AsyncSession): The database session dependency for executing queries.

    Returns:
        List[Mapping]: A list of mappings representing the courses with future start dates.
    """
    today = date.today()

    query = (
        select(course)
        .join(schedule_course, course.c.id == schedule_course.c.course_id)
        .where(schedule_course.c.start_date > today)
        .distinct()
    )
    result = await session.execute(query)
    return result.mappings().all()

@app.post("/courses")
async def create_course(
    course_data: CourseCreate,
    schedule_data: List[ScheduleCreate],
    session: AsyncSession = Depends(get_async_session),
):
    """
    Create a new course with its schedules.

    This endpoint first validates the course data, then validates each schedule in the list
    against existing schedules in the database. If a schedule conflicts with an existing one, it
    will not be created and will be added to the list of conflicted schedules. If a schedule
    is valid, it will be added to the list of valid schedules and will be created in the database.

    Args:
        course_data (CourseCreate): The course data to be created.
        schedule_data (List[ScheduleCreate]): A list of schedule data to be created.

    Returns:
        dict: A dictionary containing the following keys:

            * message: A success message.
            * valid_schedules: A list of valid schedules created.
            * conflicted_schedules: A list of schedules that conflict with existing ones.
            * schedules: A list of ISO-formatted timestamps of the valid schedules created.
            * notifications: A string indicating whether notifications were sent successfully.

    Raises:
        HTTPException: If the course with the same name already exists.
        HTTPException: If any of the schedules conflict with existing ones.
        HTTPException: If there is an unexpected error.
    """
    try:
        async with session.begin():
            existing_course = await session.execute(
                select(course).filter(course.c.name == course_data.name)
            )
            if existing_course.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail="Course with this name already exists"
                )

            query = insert(course).values(**course_data.model_dump())
            result = await session.execute(query)
            course_id = result.inserted_primary_key[0]

        valid_schedules = []
        conflicted_schedules = []
        occupied_intervals = {}

        for schedule in schedule_data:
            if schedule.end_date < schedule.start_date:
                conflicted_schedules.append(
                    {
                        **schedule.model_dump(),
                        "reason": "End date is earlier than start date"
                    }
                )
                continue

            start_date = schedule.start_date
            start_time = schedule.start_time
            end_time = schedule.end_time

            if start_date not in occupied_intervals:
                occupied_intervals[start_date] = []

            conflict = False
            for interval in occupied_intervals[start_date]:
                if (start_time < interval["end_time"]) and \
                    (end_time > interval["start_time"]):
                    conflict = True
                    break

            if conflict:
                conflicted_schedules.append(
                    {
                        **schedule.model_dump(),
                        "msg": "Time conflict with an already valid schedule"
                    }
                )
            else:
                valid_schedules.append(
                    {
                        **schedule.model_dump(),
                        "course_id": course_id
                    }
                )
                occupied_intervals[start_date].append(
                    {
                        "start_time": start_time,
                        "end_time": end_time
                    }
                )

        inserted_schedule_ids = []
        for schedule in valid_schedules:
            try:
                async with session.begin():
                    query = (
                        insert(schedule_course)
                        .values(schedule)
                        .returning(schedule_course.c.id)
                    )
                    result = await session.execute(query)
                    schedule_id = result.scalar_one()
                    inserted_schedule_ids.append(schedule_id)
            except IntegrityError:
                conflicted_schedules.append(
                    {
                        **schedule.model_dump(),
                        "reason": "Database integrity error"
                    }
                )
                continue

        schedules = []
        if inserted_schedule_ids:
            for schedule_time in valid_schedules:
                date_time = datetime.combine(
                    schedule_time["start_date"],
                    schedule_time["start_time"]
                )
                schedules.append(f"{date_time.isoformat()}+05:00")

            logging.error(f"NOTIFICATION - {schedules}")
            async with httpx.AsyncClient() as client:
                notification_response = await client.post(
                    "http://notification_service:8005/send_notification/",
                    json={
                        "course_id": course_id,
                        "schedule_ids": inserted_schedule_ids,
                        "schedule_time_str": schedules,
                    },
                )
                if notification_response.status_code != 200:
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"Failed to send notifications: "
                            f"{notification_response.text}"
                        ),
                    )

        return {
            "message": "Course and schedules processed successfully",
            "valid_schedules": valid_schedules,
            "conflicted_schedules": conflicted_schedules,
            "schedules": schedules,
            "notifications": (
                "Sent successfully" 
                if inserted_schedule_ids 
                else "No notifications sent"
            ),
        }

    except IntegrityError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Integrity error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/courses/{course_id}")
async def get_course_by_id(
    course_id: int,
    session: AsyncSession=Depends(get_async_session)
):
    
    """
    Retrieve a course by its ID.

    Аргументы:
        course_id (int): ID курса для получения информации

    Возвращает:
        List[Mapping]: список маппингов, представляющих курс с заданным ID
    """

    query = select(course).where(course.c.id == course_id)
    result = await session.execute(query)
    return result.mappings().all()

@app.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    session: AsyncSession=Depends(get_async_session)
):
    """
    Обновление курса по ID

    Аргументы:
        course_id (int): ID курса для обновления
        course_data (CourseUpdate): данные о курсе для обновления

    Возвращает:
        None
    """

    logging.error(f"Course data: {course_data}")
    query = (
        update(course)
        .where(course.c.id == course_id)
        .values(**course_data.model_dump())
    )
    await session.execute(query)
    await session.commit()

@app.get("/courses_by_operator/{operator_id}")
async def get_course_by_id(
    operator_id: int,
    session: AsyncSession=Depends(get_async_session)
):
    
    """
    Аргументы:
        operator_id (int): ID оператора, которому принадлежат курсы.

    Возвращает:
        List[Mapping]: список маппингов представляющих 
        курсы для заданного оператора.
    """

    query = select(course).where(course.c.operator_id == operator_id)
    result = await session.execute(query)
    return result.mappings().all()

@app.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    session: AsyncSession=Depends(get_async_session)
):
    """
    Этот эндпоинт удаляет запись о курсе из бд по ID

    Аргументы:
        course_id (int): ID курса, который нужно удалить

    Возвращает:
        None
    """
    query = delete(course).where(course.c.id == course_id)
    await session.execute(query)
    await session.commit()

@app.get("/courses/{course_id}/schedule")
async def get_schedule_for_course(
    course_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Этот эндпоинт возвращает список уникальных дат начала для расписания курса.

    Аргументы:
        course_id (int): ID курса для которого нужно получить расписание

    Возвращает:
        dict: словарь, содержащий список уникальных дат начала
    """
    query = (
        select(
            distinct(schedule_course.c.start_date)
        )
        .where(schedule_course.c.course_id == course_id)
    )
    result = await session.execute(query)
    
    unique_dates = {"start_date": [row[0] for row in result.fetchall()]}
    return unique_dates

@app.get("/courses_schedule/{schedule_id}")
async def get_course_details(
    schedule_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Этот эндпоинт возвращает подробные данные по расписанию с заданным ID.

    Аргументы:
        schedule_id (int): ID расписания для получения деталей по расписанию

    Возвращает:
        dict: содержащий название курса, начальную дату, конечную дату, 
        начальное время и конечное время словарь

    Raises:
        HTTPException: если не было найдено расписания с переданным ID
    """
    query = (
        select(
            course.c.name.label("course_name"),
            schedule_course.c.start_date,
            schedule_course.c.end_date,
            schedule_course.c.start_time,
            schedule_course.c.end_time,
        )
        .join(
            schedule_course,
            schedule_course.c.course_id == course.c.id
        )
        .where(
            schedule_course.c.id == schedule_id
        )
    )
    result = await session.execute(query)
    record = result.fetchone()
    
    if not record:
        raise HTTPException(status_code=404, detail="Расписание не найдено")

    return {
        "course_name": record.course_name,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "start_time": record.start_time,
        "end_time": record.end_time,
    }


@app.get("/courses/{course_id}/times")
async def get_course_times(
    course_id: int, 
    date: str, 
    session: AsyncSession = Depends(get_async_session)
):
    """
    Этот эндпоинт получает все доступные времена для курса на определенную дату
    Он выбирает все расписания, соответствующие заданному ID курса и дате

    Args:
        course_id (int): ID курса, на которое необходимо найти время
        date (str): дата (в формате 'YYYY-MM-DD'),
        на которую необходимо найти время

    Возвращает:
        dict: словарь с доступными временами и их id

    Raises:
        HTTPException: если не было найдено доступное время для курса и даты
    """
    date = datetime.strptime(date, "%Y-%m-%d").date()
    query = select(
        schedule_course.c.id,
        schedule_course.c.start_time).where(
            (schedule_course.c.course_id == course_id) & 
            (schedule_course.c.start_date == date)
        )
    result = await session.execute(query)
    times = result.fetchall() 
    if not times:
        raise HTTPException(
            status_code=404,
            detail="Доступное время не найдено"
        )
    return {
        "times": [
            {
                "id": row.id,
                "start_time": row.start_time
            } 
            for row in times
        ]
    }

@app.get("/courses_schedule_operator/{course_id}")
async def get_course_times(
    course_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    """
    Соединяет таблицы `course` и `schedule_course` 
    для получения необходимой информации

    Аргументы:
        course_id (int): ID курса, на который нужно получить расписание

    Возвращает:
        dict: словарь со списком дат и времен начала/окончания курса

    Raises:
        HTTPException: если не найдены расписания для курса
    """
    query = (
        select(
            course.c.name,
            schedule_course.c.start_date,
            schedule_course.c.end_date,
            schedule_course.c.start_time,
            schedule_course.c.end_time
        )
        .select_from(
            join(
                schedule_course,
                course,
                schedule_course.c.course_id == course.c.id
            )
        )
        .where(schedule_course.c.course_id == course_id))

    result = await session.execute(query)
    times = result.fetchall()

    if not times:
        raise HTTPException(
            status_code=404,
            detail="Расписание для указанного курса не найдено"
        )

    schedule_data = [
        {
            "course_name": row.name,
            "start_date": row.start_date,
            "end_date": row.end_date,
        }
        for row in times
    ]
    logging.error(schedule_data)
    return {"schedule": schedule_data}
