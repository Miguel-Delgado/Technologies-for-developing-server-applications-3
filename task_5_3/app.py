import uuid
import time
from fastapi import FastAPI, Cookie, Response
from pydantic import BaseModel
from typing import Optional
from itsdangerous import URLSafeSerializer, BadSignature

app = FastAPI()

SECRET_KEY = "super-secret-key-change-in-production"
serializer = URLSafeSerializer(SECRET_KEY)

SESSION_LIFETIME = 300     # 5 minutes in seconds
RENEW_THRESHOLD = 180      # 3 minutes in seconds

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


def create_session_token(user_id: str, timestamp: float) -> str:
    payload = f"{user_id}.{int(timestamp)}"
    signature = serializer.dumps(payload)
    return signature


def verify_session_token(token: str) -> Optional[tuple[str, int]]:
    """Returns (user_id, timestamp) or None if invalid."""
    try:
        payload = serializer.loads(token)
        parts = payload.split(".", 1)
        if len(parts) != 2:
            return None
        user_id, ts_str = parts
        return user_id, int(ts_str)
    except (BadSignature, ValueError):
        return None


@app.post("/login")
def login(data: LoginData, response: Response):
    user = USERS.get(data.username)
    if not user or user["password"] != data.password:
        response.status_code = 401
        return {"message": "Invalid credentials"}

    now = time.time()
    token = create_session_token(user["user_id"], now)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False,
        max_age=SESSION_LIFETIME,
    )
    return {"message": "Login successful"}


@app.get("/profile")
def get_profile(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if session_token is None:
        response.status_code = 401
        return {"message": "Invalid session"}

    result = verify_session_token(session_token)
    if result is None:
        response.status_code = 401
        return {"message": "Invalid session"}

    user_id, last_active = result
    now = time.time()
    elapsed = now - last_active

    if elapsed >= SESSION_LIFETIME:
        response.status_code = 401
        return {"message": "Session expired"}

    user = next((u for u in USERS.values() if u["user_id"] == user_id), None)
    if user is None:
        response.status_code = 401
        return {"message": "Invalid session"}

    # Renew cookie only if elapsed >= 3 minutes (but less than 5 minutes)
    if RENEW_THRESHOLD <= elapsed < SESSION_LIFETIME:
        new_token = create_session_token(user_id, now)
        response.set_cookie(
            key="session_token",
            value=new_token,
            httponly=True,
            secure=False,
            max_age=SESSION_LIFETIME,
        )

    return {"user_id": user_id, "name": user["name"], "email": user["email"]}
