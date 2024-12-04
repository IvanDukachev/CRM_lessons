from datetime import datetime
from sqlalchemy import ForeignKey, Integer, TIMESTAMP, Column, String, Table, Date, Time, UniqueConstraint

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
    Column("course_id", Integer, ForeignKey(course.c.id, ondelete="CASCADE"), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("start_time", Time, nullable=False),
    Column("end_time", Time, nullable=False),
    UniqueConstraint("course_id", "start_date", "start_time", name="unique_course_time"),
)
