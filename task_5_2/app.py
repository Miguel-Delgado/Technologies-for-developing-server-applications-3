import uuid
from fastapi import FastAPI, Cookie, Response
from pydantic import BaseModel
from typing import Optional
from itsdangerous import URLSafeSerializer, BadSignature

app = FastAPI()

SECRET_KEY = "super-secret-key-change-in-production"
serializer = URLSafeSerializer(SECRET_KEY)

# Fake user database
USERS = {
    "user123": {
        "password": "password123",
        "name": "User 123",
        "email": "user123@example.com",
        "user_id": str(uuid.uuid4()),
    },
}


class LoginData(BaseModel):
    username: str
    password: str


def create_session_token(user_id: str) -> str:
    # itsdangerous produces: <data>.<signature> under the hood
    return serializer.dumps(user_id)


def verify_session_token(token: str) -> Optional[str]:
    try:
        user_id = serializer.loads(token)
        return user_id
    except BadSignature:
        return None


@app.post("/login")
def login(data: LoginData, response: Response):
    user = USERS.get(data.username)
    if not user or user["password"] != data.password:
        response.status_code = 401
        return {"message": "Invalid credentials"}

    token = create_session_token(user["user_id"])
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=3600)
    return {"message": "Login successful"}


@app.get("/profile")
def get_profile(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if session_token is None:
        response.status_code = 401
        return {"message": "Unauthorized"}

    user_id = verify_session_token(session_token)
    if user_id is None:
        response.status_code = 401
        return {"message": "Unauthorized"}

    # Find user by user_id
    user = next((u for u in USERS.values() if u["user_id"] == user_id), None)
    if user is None:
        response.status_code = 401
        return {"message": "Unauthorized"}

    return {"user_id": user_id, "name": user["name"], "email": user["email"]}
