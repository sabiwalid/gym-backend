from pydantic import BaseModel, Field, EmailStr
from typing import List
from datetime import date


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=72) 
       
class SetCreate(BaseModel):
    reps: int = Field(gt=0)
    weight: float = Field(ge=0)


class SetResponse(SetCreate):
    id: int
    exercise_id: int

    class Config:
        from_attributes = True


class ExerciseCreate(BaseModel):
    name: str
    sets: List[SetCreate] = Field(default_factory=list)


class ExerciseResponse(BaseModel):
    id: int
    workout_id: int
    name: str
    sets: List[SetResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class WorkoutCreate(BaseModel):
    date: date
    exercises: List[ExerciseCreate] = Field(default_factory=list)


class WorkoutResponse(WorkoutCreate):
    id: int
    exercises: List[ExerciseResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
