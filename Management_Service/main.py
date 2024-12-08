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
    Получение списка курсов, которые еще не начались

    Этот эндпоинт соединяет таблицы `course` и `schedule_course` 
    для фильтрации курсов, у которых дата начала расписания
    больше текущей даты. Он возвращает уникальный список таких курсов

    Returns:
        List[Mapping]: список маппингов,
        представляющих курсы с будущими датами начала
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
    Создание нового курса со списком расписаний

    Этот эндпоинт ожидает JSON-объект с двумя ключами:
        `course_data` и `schedule_data`
    `course_data` должен содержать имя и описание курса
    `schedule_data` должен быть списком словарей,
        каждый из которых содержит дату и время
        начала и окончания валидного расписания

    Сначла проводится проверка на наличие курса с таким же именем
    Если такой курс уже существует, то возвращается ошибка 400
    В противном случае, происходит попытка вставить курс в базу данных

    Далее проверяется наличие конфликтов между расписаниями
    Если конфликтов нет, то расписание добавляется в
    список `valid_schedules`
    Если конфликт есть, то расписание добавляется в
    список `conflicted_schedules`

    В конце происходит вставка списка `valid_schedules` в базу данных и
    отправка уведомлений для каждого расписания с
    помощью сервиса уведомлений. 
    Если отправить уведомлений не удалось, то возвращается ошибка 500

    Args:
        course_data (CourseCreate): 
            информация о курсе, который нужно создать
        schedule_data (List[ScheduleCreate]): 
            список расписаний для курса

    Returns:
        dict: словарь, включающий следующие ключи:
            - `message`: сообщение уведомляющее о результатах операции
            - `valid_schedules`: список словарей с
                информацией о валидных расписаниях
            - `conflicted_schedules`: список словарей с информацией
                о конфликтующих расписаниях
            - `schedules`: список времен начала валидных расписаний в
                формате ISO
            - `notifications`: строка уведомляющая о результатах
                операции об отправке уведомлений
            - `course_id`: ID курса
            - `schedule_ids`: список ID расписаний
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
                            "reason": (
                                "Time conflict with an already valid schedule"
                            ),
                        }
                    )
                else:
                    valid_schedules.append(schedule.model_dump())
                    occupied_intervals[start_date].append(
                        {
                            "start_time": start_time,
                            "end_time": end_time
                        }
                    )

            if not valid_schedules:
                raise HTTPException(
                    status_code=400,
                    detail="No valid schedules provided"
                )

            query = (
                insert(course)
                .values(**course_data.model_dump())
                .returning(course.c.id)
            )
            result = await session.execute(query)
            course_id = result.scalar_one()

            inserted_schedule_ids = []
            schedules = []
            for schedule in valid_schedules:
                schedule["course_id"] = course_id
                query = (
                    insert(schedule_course)
                    .values(schedule)
                    .returning(schedule_course.c.id)
                )
                result = await session.execute(query)
                schedule_id = result.scalar_one()
                inserted_schedule_ids.append(schedule_id)
                date_time = datetime.combine(
                    schedule["start_date"],
                    schedule["start_time"]
                )
                schedules.append(f"{date_time.isoformat()}+05:00")

            if inserted_schedule_ids:
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
            "course_id": course_id,
            "schedule_ids": inserted_schedule_ids
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
    Получение описания курса по его ID

    Args:
        course_id (int): ID курса для получения информации

    Returns:
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

    Args:
        course_id (int): ID курса для обновления
        course_data (CourseUpdate): данные о курсе для обновления

    Returns:
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

@app.get("/courses/operator/{operator_id}")
async def get_course_by_id(
    operator_id: int,
    session: AsyncSession=Depends(get_async_session)
):
    """
    Получение списка курсов по ID оператора

    Args:
        operator_id (int): ID оператора, которому принадлежат курсы.

    Returns:
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

    Args:
        course_id (int): ID курса, который нужно удалить

    Returns:
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

    Args:
        course_id (int): ID курса для которого нужно получить расписание

    Returns:
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

@app.get("/courses/schedule/{schedule_id}")
async def get_course_details(
    schedule_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Этот эндпоинт возвращает подробные данные по расписанию с заданным ID.

    Args:
        schedule_id (int): ID расписания для получения деталей по расписанию

    Returns:
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

    Returns:
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

@app.get("/courses/schedule/operator/{course_id}")
async def get_course_times(
    course_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    """
    Соединяет таблицы `course` и `schedule_course` 
    для получения необходимой информации

    Args:
        course_id (int): ID курса, на который нужно получить расписание

    Returns:
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
