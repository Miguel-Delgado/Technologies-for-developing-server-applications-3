from fastapi import FastAPI
from pydantic import BaseModel
from database import get_db_connection, init_db

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


class User(BaseModel):
    username: str
    password: str


@app.post("/register")
def register(user: User):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (user.username, user.password),
    )
    conn.commit()
    conn.close()
    return {"message": "User registered successfully!"}
