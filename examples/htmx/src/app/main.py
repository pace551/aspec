"""todomini — STK-HTMX worked example.

- HX-Request branching: fragment for htmx, full page otherwise (STK-HTMX-02)
- progressive enhancement: real <form> POST + 303 redirect no-JS path (STK-HTMX-03)
- CSRF double-submit cookie via dependency on state-changing routes (STK-HTMX-04)
- hx-indicator on every in-flight request (STK-HTMX-05, see templates)
- no JSON API: the hypermedia is the API (STK-HTMX-06)
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

CSRF_COOKIE = "csrf_token"


@dataclass
class Todo:
    id: int
    title: str
    done: bool = False


@dataclass
class TodoStore:
    """In-memory store — real projects swap in SQLite without touching routes."""

    todos: dict[int, Todo] = field(default_factory=dict)
    _ids: count = field(default_factory=lambda: count(1))

    def add(self, title: str) -> Todo:
        todo = Todo(id=next(self._ids), title=title)
        self.todos[todo.id] = todo
        return todo

    def toggle(self, todo_id: int) -> Todo:
        todo = self.todos.get(todo_id)
        if todo is None:
            raise KeyError(todo_id)
        todo.done = not todo.done
        return todo

    def all(self) -> list[Todo]:
        return list(self.todos.values())

    def reset(self) -> None:
        """Test hook: fresh state per test without re-importing the app."""
        self.todos.clear()
        self._ids = count(1)


store = TodoStore()


def is_hx(request: Request) -> bool:
    """True when htmx made the request (STK-HTMX-02 branching)."""
    return request.headers.get("hx-request") == "true"


def issue_csrf(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)


async def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    """Double-submit check (STK-HTMX-04): hidden form field must equal the cookie."""
    if not secrets.compare_digest(csrf_token, request.cookies.get(CSRF_COOKIE, "")):
        raise HTTPException(status_code=403, detail="CSRF token mismatch")


@app.middleware("http")
async def set_csrf_cookie(request: Request, call_next):
    response = await call_next(request)
    if CSRF_COOKIE not in request.cookies:
        response.set_cookie(CSRF_COOKIE, issue_csrf(request), httponly=False, samesite="lax")
    return response


def list_context(request: Request) -> dict:
    return {"todos": store.all(), "csrf_token": issue_csrf(request)}


def list_fragment(request: Request) -> HTMLResponse:
    """The ONE list markup, rendered as a fragment for htmx swaps (STK-HTMX-02)."""
    return templates.TemplateResponse(request, "partials/todo_list.html", list_context(request))


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", list_context(request))


@app.post("/todos", dependencies=[Depends(verify_csrf)])
async def create_todo(request: Request, title: str = Form(...)):
    title = title.strip()
    if not title or len(title) > 200:
        raise HTTPException(status_code=422, detail="title must be 1-200 characters")
    store.add(title)
    if is_hx(request):
        return list_fragment(request)
    return RedirectResponse("/", status_code=303)  # no-JS path (STK-HTMX-03)


@app.post("/todos/{todo_id}/toggle", dependencies=[Depends(verify_csrf)])
async def toggle_todo(request: Request, todo_id: int):
    try:
        store.toggle(todo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such todo") from None
    if is_hx(request):
        return list_fragment(request)
    return RedirectResponse("/", status_code=303)
