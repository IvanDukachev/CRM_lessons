from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class CourseCreate(BaseModel):
    name: str
    description: str
    price: Optional[int] = None
    operator_id: int


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    operator_id: Optional[int] = None


class ScheduleCreate(BaseModel):
    course_id: int
    date: datetime
    start_time: datetime
    end_time: datetime