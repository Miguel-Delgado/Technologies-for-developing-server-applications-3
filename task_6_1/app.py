import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()

VALID_USERNAME = "admin"
VALID_PASSWORD = "secret123"


def auth_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    username_ok = secrets.compare_digest(credentials.username, VALID_USERNAME)
    password_ok = secrets.compare_digest(credentials.password, VALID_PASSWORD)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/login")
def login(user: str = Depends(auth_user)):
    return {"message": "You got my secret, welcome"}
