import re
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

ACCEPT_LANGUAGE_PATTERN = re.compile(
    r"^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})?(,\s*[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})?(;\s*q=[0-9](\.[0-9]+)?)?)*$"
)


@app.get("/headers")
def get_headers(request: Request):
    user_agent = request.headers.get("User-Agent")
    accept_language = request.headers.get("Accept-Language")

    if not user_agent:
        raise HTTPException(status_code=400, detail="Missing required header: User-Agent")
    if not accept_language:
        raise HTTPException(status_code=400, detail="Missing required header: Accept-Language")

    if not ACCEPT_LANGUAGE_PATTERN.match(accept_language):
        raise HTTPException(status_code=400, detail="Invalid Accept-Language header format")

    return {
        "User-Agent": user_agent,
        "Accept-Language": accept_language,
    }
