"""STK-HTMX scaffold app.

Patterns demonstrated (delete this docstring in real projects):
- HX-Request branching: fragment for htmx, full page otherwise (STK-HTMX-02)
- progressive enhancement: real <form> POST + 303 redirect no-JS path (STK-HTMX-03)
- CSRF double-submit cookie via a dependency on state-changing routes (STK-HTMX-04)
"""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

CSRF_COOKIE = "csrf_token"


def is_hx(request: Request) -> bool:
    """True when htmx made the request (STK-HTMX-02 branching)."""
    return request.headers.get("hx-request") == "true"


def issue_csrf(request: Request) -> str:
    """Token rendered into forms; middleware below mirrors it into the cookie."""
    return request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)


async def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    """Double-submit check (STK-HTMX-04): hidden form field must equal the cookie.
    htmx submits the enclosing form's fields, so both paths carry the token."""
    if not secrets.compare_digest(csrf_token, request.cookies.get(CSRF_COOKIE, "")):
        raise HTTPException(status_code=403, detail="CSRF token mismatch")


@app.middleware("http")
async def set_csrf_cookie(request: Request, call_next):
    response = await call_next(request)
    if CSRF_COOKIE not in request.cookies:
        response.set_cookie(CSRF_COOKIE, issue_csrf(request), httponly=False, samesite="lax")
    return response


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"csrf_token": issue_csrf(request)})


@app.post("/echo", dependencies=[Depends(verify_csrf)])
async def echo(request: Request, message: str = Form(...)):
    """Replace with real actions. Shows the two response modes."""
    message = message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")
    if is_hx(request):
        return templates.TemplateResponse(request, "partials/echo.html", {"message": message})
    return RedirectResponse("/", status_code=303)  # no-JS path (STK-HTMX-03)
