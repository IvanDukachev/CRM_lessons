from fastapi import FastAPI
import logging

from routes import auth, enroll, courses


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(enroll.router, prefix="/enroll", tags=["Enroll"])
app.include_router(courses.router, prefix="/courses", tags=["Courses"])
