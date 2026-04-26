import uuid
from fastapi import FastAPI, Cookie, Response
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# In-memory session store: token -> user info
sessions: dict[str, dict] = {}

# Fake user database
USERS = {
    "user123": {"password": "password123", "name": "User 123", "email": "user123@example.com"},
}


class LoginData(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(data: LoginData, response: Response):
    user = USERS.get(data.username)
    if not user or user["password"] != data.password:
        response.status_code = 401
        return {"message": "Invalid credentials"}

    token = str(uuid.uuid4())
    sessions[token] = {"username": data.username, "name": user["name"], "email": user["email"]}

    response.set_cookie(key="session_token", value=token, httponly=True)
    return {"message": "Login successful"}


@app.get("/user")
def get_user(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if session_token is None or session_token not in sessions:
        response.status_code = 401
        return {"message": "Unauthorized"}

    return sessions[session_token]
