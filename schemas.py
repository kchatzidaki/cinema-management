from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str

class ProgramCreate(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ScreeningCreate(BaseModel):
    program_id: int
    film_title: str
    film_cast: str
    film_genres: str
    film_duration: int
    auditorium_name: str

class ScreeningUpdate(BaseModel):
    film_title: Optional[str] = None
    film_cast: Optional[str] = None
    film_genres: Optional[str] = None
    film_duration: Optional[int] = None
    auditorium_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class ScreeningReview(BaseModel):
    score: float
    comments: str

class ScreeningApproval(BaseModel):
    conditional_notes: Optional[str] = None