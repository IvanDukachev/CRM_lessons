from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, and_
from database import get_async_session
from models import enroll_course
from Management_Service.models import schedule_course
from schemas import EnrollCreate


app = FastAPI()


@app.post("/enroll")
async def enroll_user(
    enroll_data: EnrollCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Записывает пользователя на курс

    Args:
        enroll_data (EnrollCreate): Данные для записи на курс

    Returns:
        dict: Словарь с информацией о результате записи

    Raises:
        HTTPException: Если произошла ошибка при записи на курс
    """

    try:
        stmt = insert(enroll_course).values(**enroll_data.model_dump()).returning(enroll_course.c.id)
        result = await session.execute(stmt)
        enroll_id = result.scalar_one()
        await session.commit()

        return {
            "message": "Пользователь успешно зарегистрирован на курс",
            "enroll_id": enroll_id
        }
    except Exception as e:

        print(f"Ошибка при записи пользователя на курс: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка при записи на курс"
        )


@app.get("/enroll")
async def get_enroll(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Получить список курсов, на которые записан пользователь

    Аргументы:
        user_id (int): ID пользователя
    """
    
    today = datetime.now().date()
    query = (
        select(enroll_course)
        .join(
            schedule_course,
            enroll_course.c.schedule_id == schedule_course.c.id
        )
        .where(and_(
            enroll_course.c.user_id == user_id,
            schedule_course.c.end_date > today
        ))
    )

    result = await session.execute(query)
    return result.mappings().all()


@app.delete("/enroll/{enroll_id}")
async def delete_enroll_for_user(
    enroll_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Удалить запись на курс для пользователя
    
    Аргументы:
        enroll_id (int): ID записи на курс
    
    Возвращает:
        None
    """
    query = delete(enroll_course).where(enroll_course.c.id == enroll_id)
    await session.execute(query)
    await session.commit()


@app.get("/enroll/{schedule_id}")
async def get_users_for_schedule(
    schedule_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Получить список пользователей, записанных на данное расписание
    
    Аргументы:
        schedule_id (int): ID расписания
    Возвращает:
        dict: {"users": [user_id1, user_id2, ...]}
    """
    query = (
        select(enroll_course.c.user_id)
        .where(enroll_course.c.schedule_id == schedule_id)
    )
    result = await session.execute(query)
    users = {"users": [row[0] for row in result.fetchall()]}
    return users
