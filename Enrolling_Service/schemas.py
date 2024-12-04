from pydantic import BaseModel


class EnrollCreate(BaseModel):
    user_id: int
    course_id: int
    schedule_id: int
