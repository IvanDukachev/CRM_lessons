from typing import Optional
from pydantic import BaseModel
from datetime import date, time


class CourseCreate(BaseModel):
    name: str
    description: str
    price: Optional[int] = 0
    operator_id: int


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ScheduleCreate(BaseModel):
    start_date: date
    end_date: date
    start_time: time
    end_time: time
    