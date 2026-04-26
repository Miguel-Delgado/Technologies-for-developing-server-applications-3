from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

app = FastAPI()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None
    is_subscribed: Optional[bool] = None

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("age must be a positive integer")
        return v


@app.post("/create_user")
def create_user(user: UserCreate):
    return user
