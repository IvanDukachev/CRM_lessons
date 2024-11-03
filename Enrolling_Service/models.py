from datetime import datetime
from sqlalchemy import ForeignKey, Integer, TIMESTAMP, Column, String, Table

from database import metadata
from Management_Service.models import *


enroll_course = Table(
    "enroll_course",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False),
    Column("course_id", Integer, ForeignKey(course.c.id), nullable=False),
    Column("schedule_id", Integer, ForeignKey(schedule_course.c.id), nullable=False),
    Column("enroll_time", TIMESTAMP, default=datetime.now),
)
