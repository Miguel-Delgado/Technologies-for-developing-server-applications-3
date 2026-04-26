import re
from datetime import datetime
from fastapi import FastAPI, Response
from pydantic import field_validator
from fastapi.datastructures import Headers
from typing import Annotated
from fastapi import Header, HTTPException

app = FastAPI()

ACCEPT_LANGUAGE_PATTERN = re.compile(
    r"^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})?(,\s*[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})?(;\s*q=[0-9](\.[0-9]+)?)?)*$"
)


class CommonHeaders:
    def __init__(
        self,
        user_agent: Annotated[str | None, Header(alias="user-agent")] = None,
        accept_language: Annotated[str | None, Header(alias="accept-language")] = None,
    ):
        if not user_agent:
            raise HTTPException(status_code=400, detail="Missing required header: User-Agent")
        if not accept_language:
            raise HTTPException(status_code=400, detail="Missing required header: Accept-Language")
        if not ACCEPT_LANGUAGE_PATTERN.match(accept_language):
            raise HTTPException(status_code=400, detail="Invalid Accept-Language header format")

        self.user_agent = user_agent
        self.accept_language = accept_language


from fastapi import Depends


@app.get("/headers")
def get_headers(headers: Annotated[CommonHeaders, Depends(CommonHeaders)]):
    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language,
    }


@app.get("/info")
def get_info(headers: Annotated[CommonHeaders, Depends(CommonHeaders)], response: Response):
    response.headers["X-Server-Time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent": headers.user_agent,
            "Accept-Language": headers.accept_language,
        },
    }
