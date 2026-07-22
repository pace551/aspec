"""Scaffold smoke tests — the STK-HTMX-07 shape: drive the app through TestClient,
assert BOTH response modes. Extend per feature; never delete the mode assertions."""

from fastapi.testclient import TestClient

from app.main import app


def make_client() -> TestClient:
    return TestClient(app)


def csrf(client: TestClient) -> str:
    client.get("/")  # sets the csrf cookie
    return client.cookies["csrf_token"]


def test_full_page_has_layout_shell():
    client = make_client()
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text  # full page, not a fragment (STK-HTMX-02)


def test_hx_request_gets_bare_fragment():
    client = make_client()
    token = csrf(client)
    r = client.post(
        "/echo",
        data={"message": "hi", "csrf_token": token},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "<html" not in r.text  # fragment only (STK-HTMX-02)
    assert "You said: hi" in r.text


def test_no_js_post_redirects_303():
    client = make_client()
    token = csrf(client)
    r = client.post(
        "/echo",
        data={"message": "hi", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303  # POST/redirect/GET no-JS path (STK-HTMX-03)


def test_missing_csrf_token_is_403():
    client = make_client()
    client.get("/")
    r = client.post("/echo", data={"message": "hi", "csrf_token": "wrong"})
    assert r.status_code == 403  # STK-HTMX-04
