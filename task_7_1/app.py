import jwt
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext

app = FastAPI()

SECRET_KEY = "rbac-jwt-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


# Role permissions (for reference/debug)
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {"create", "read", "update", "delete"},
    Role.USER: {"read", "update"},
    Role.GUEST: {"read"},
}


class UserInDB(BaseModel):
    username: str
    hashed_password: str
    role: Role


fake_users_db: dict[str, UserInDB] = {}
resources_db: dict[int, dict] = {1: {"id": 1, "title": "seed", "owner": "system"}}
_next_resource_id = 2


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: Role = Role.USER


class LoginRequest(BaseModel):
    username: str
    password: str


class ResourceCreate(BaseModel):
    title: str


class ResourceUpdate(BaseModel):
    title: str


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    username = payload.get("sub")
    if username is None or username not in fake_users_db:
        raise HTTPException(status_code=401, detail="Invalid token")
    return fake_users_db[username]


def require_roles(*allowed: Role):
    def checker(user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Access forbidden: insufficient role")
        return user
    return checker


@app.post("/register", status_code=201)
def register(data: RegisterRequest):
    if data.username in fake_users_db:
        raise HTTPException(status_code=409, detail="User already exists")
    fake_users_db[data.username] = UserInDB(
        username=data.username,
        hashed_password=pwd_context.hash(data.password),
        role=data.role,
    )
    return {"message": f"User {data.username} registered as {data.role.value}"}


@app.post("/login")
def login(data: LoginRequest):
    user = fake_users_db.get(data.username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not secrets.compare_digest(user.username, data.username):
        raise HTTPException(status_code=401, detail="Authorization failed")
    if not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Authorization failed")
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/protected_resource")
def protected_resource(user: UserInDB = Depends(require_roles(Role.ADMIN, Role.USER))):
    return {"message": f"Hello, {user.username}!", "role": user.role.value}


@app.post("/resources", status_code=201)
def create_resource(data: ResourceCreate, user: UserInDB = Depends(require_roles(Role.ADMIN))):
    global _next_resource_id
    rid = _next_resource_id
    _next_resource_id += 1
    resources_db[rid] = {"id": rid, "title": data.title, "owner": user.username}
    return resources_db[rid]


@app.get("/resources")
def list_resources(user: UserInDB = Depends(require_roles(Role.ADMIN, Role.USER, Role.GUEST))):
    return list(resources_db.values())


@app.put("/resources/{rid}")
def update_resource(rid: int, data: ResourceUpdate, user: UserInDB = Depends(require_roles(Role.ADMIN, Role.USER))):
    if rid not in resources_db:
        raise HTTPException(status_code=404, detail="Resource not found")
    resources_db[rid]["title"] = data.title
    return resources_db[rid]


@app.delete("/resources/{rid}")
def delete_resource(rid: int, user: UserInDB = Depends(require_roles(Role.ADMIN))):
    if rid not in resources_db:
        raise HTTPException(status_code=404, detail="Resource not found")
    del resources_db[rid]
    return {"message": f"Resource {rid} deleted"}
