"""STK-HTMX-07: drive the app through httpx's TestClient, asserting BOTH response
modes (full page and fragment), the no-JS redirect path, and CSRF enforcement."""

import pytest
from fastapi.testclient import TestClient

from app.main import app, store


@pytest.fixture(autouse=True)
def fresh_store():
    store.reset()
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def csrf(client: TestClient) -> str:
    client.get("/")  # first response sets the csrf cookie
    return client.cookies["csrf_token"]


def test_full_page_has_layout_shell(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text  # full page (STK-HTMX-02)
    assert "todo-region" in r.text


def test_create_via_hx_returns_bare_fragment(client):
    token = csrf(client)
    r = client.post(
        "/todos",
        data={"title": "write tests", "csrf_token": token},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "<html" not in r.text  # fragment only (STK-HTMX-02)
    assert "write tests" in r.text


def test_create_without_js_redirects_303(client):
    token = csrf(client)
    r = client.post(
        "/todos",
        data={"title": "no-js path", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303  # POST/redirect/GET (STK-HTMX-03)
    followed = client.get("/")
    assert "no-js path" in followed.text  # visible on the full page after redirect


def test_toggle_flips_done_state_in_fragment(client):
    token = csrf(client)
    client.post("/todos", data={"title": "toggle me", "csrf_token": token})
    r = client.post(
        "/todos/1/toggle",
        data={"csrf_token": token},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "☑" in r.text


def test_wrong_csrf_token_is_403(client):
    csrf(client)
    r = client.post("/todos", data={"title": "forged", "csrf_token": "wrong"})
    assert r.status_code == 403  # STK-HTMX-04


def test_missing_title_is_422(client):
    token = csrf(client)
    r = client.post("/todos", data={"title": "   ", "csrf_token": token})
    assert r.status_code == 422


def test_toggle_unknown_todo_is_404(client):
    token = csrf(client)
    r = client.post("/todos/999/toggle", data={"csrf_token": token})
    assert r.status_code == 404
