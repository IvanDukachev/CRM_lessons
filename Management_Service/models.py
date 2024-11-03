from datetime import datetime
from sqlalchemy import ForeignKey, Integer, TIMESTAMP, Column, String, Table

from database import metadata
from Auth_Service.models import operator


course = Table(
    "course",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, unique=True, nullable=False),
    Column("description", String, nullable=False),
    Column("price", Integer, nullable=True),
    Column("operator_id", Integer, ForeignKey(operator.c.id), nullable=False),
    Column("created_at", TIMESTAMP, default=datetime.now),
    Column("updated_at", TIMESTAMP, onupdate=datetime.now),
)

schedule_course = Table(
    "schedule_course",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("course_id", Integer, ForeignKey(course.c.id), nullable=False),
    Column("date", TIMESTAMP, nullable=False),
    Column("start_time", TIMESTAMP, nullable=False),
    Column("end_time", TIMESTAMP, nullable=False),
)
