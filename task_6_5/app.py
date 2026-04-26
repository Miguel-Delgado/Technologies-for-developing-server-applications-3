import jwt
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

SECRET_KEY = "jwt-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

fake_users_db: dict[str, str] = {}  # username -> hashed_password


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def find_user(username: str) -> str | None:
    """Returns hashed_password or None. Uses compare_digest for username match."""
    for stored_name, hashed in fake_users_db.items():
        if secrets.compare_digest(stored_name, username):
            return hashed
    return None


@app.post("/register", status_code=201)
@limiter.limit("1/minute")
def register(request: Request, data: RegisterRequest):
    if find_user(data.username) is not None:
        raise HTTPException(status_code=409, detail="User already exists")
    fake_users_db[data.username] = pwd_context.hash(data.password)
    return {"message": "New user created"}


@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest):
    hashed = find_user(data.username)
    if hashed is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not pwd_context.verify(data.password, hashed):
        raise HTTPException(status_code=401, detail="Authorization failed")
    token = create_access_token({"sub": data.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/protected_resource")
def protected_resource(payload: dict = Depends(verify_token)):
    return {"message": "Access granted", "user": payload.get("sub")}
