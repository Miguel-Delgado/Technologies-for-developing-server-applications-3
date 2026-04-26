import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

MODE = os.getenv("MODE", "DEV").upper()
DOCS_USER = os.getenv("DOCS_USER", "docs_admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "docs_secret")

if MODE not in ("DEV", "PROD"):
    raise RuntimeError(f"Invalid MODE={MODE!r}, expected DEV or PROD")

if MODE == "PROD":
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
else:
    # DEV: disable default docs and expose custom protected ones
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

security = HTTPBasic()


def verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    user_ok = secrets.compare_digest(credentials.username, DOCS_USER)
    pass_ok = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid docs credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


if MODE == "DEV":
    @app.get("/openapi.json", include_in_schema=False)
    def openapi(user: str = Depends(verify_docs_credentials)):
        return JSONResponse(app.openapi())

    @app.get("/docs", include_in_schema=False)
    def docs(user: str = Depends(verify_docs_credentials)):
        return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")


@app.get("/")
def root():
    return {"mode": MODE, "message": "API is running"}


@app.get("/ping")
def ping():
    return {"pong": True}
