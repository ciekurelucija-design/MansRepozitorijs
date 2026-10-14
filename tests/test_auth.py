"""CR-4: pieņemšanas kritēriji (AC1–AC9) reģistrācijai un pieteikšanai."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

EMAIL = "darbinieks@example.com"
PASSWORD = "drosa-parole-123"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def client(db_path):
    return TestClient(create_app(db_path))


def register(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_ac1_register_valid(client):
    response = register(client)
    assert response.status_code == 201
    assert response.json()["email"] == EMAIL
    assert "password" not in response.json()


def test_ac2_register_duplicate_email(client, db_path):
    register(client)
    response = register(client, email=EMAIL.upper())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 1


@pytest.mark.parametrize("email", ["", "bez-et", "a@b", "a b@example.com"])
def test_ac3_register_invalid_email(client, email):
    response = register(client, email=email)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["field"] == "email"


def test_ac4_register_short_password(client, db_path):
    response = register(client, password="1234567")
    assert response.status_code == 400
    assert response.json()["error"]["details"] == [
        {"field": "password", "issue": "TOO_SHORT"}
    ]
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0


def test_ac5_login_valid_sets_session(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL
    cookie = response.headers["set-cookie"].lower()
    assert "session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert EMAIL in client.get("/").text


def test_ac6_ac7_login_failures_are_indistinguishable(client):
    register(client)
    wrong_password = login(client, password="nepareiza-parole")
    unknown_email = login(client, email="nav@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "set-cookie" not in wrong_password.headers


def test_ac8_password_not_stored_in_plain_text(client, db_path):
    register(client)
    with sqlite3.connect(db_path) as conn:
        (stored,) = conn.execute("SELECT password_hash FROM accounts").fetchone()
    assert PASSWORD not in stored
    assert stored.startswith("scrypt$")


def test_ac9_account_survives_restart(db_path):
    register(TestClient(create_app(db_path)))
    restarted = TestClient(create_app(db_path))
    assert login(restarted).status_code == 200


def test_invalid_json_returns_400(client):
    response = client.post(
        "/auth/login", content="nav json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_html_forms_are_served(client):
    for path in ("/auth/register", "/auth/login"):
        response = client.get(path)
        assert response.status_code == 200
        assert f'action="{path}"' in response.text


def test_html_form_flow(client):
    created = client.post("/auth/register", data={"email": EMAIL, "password": PASSWORD})
    assert created.status_code == 201
    assert "text/html" in created.headers["content-type"]

    failed = client.post("/auth/login", data={"email": EMAIL, "password": "nepareiza"})
    assert failed.status_code == 401
    assert "Nepareizs e-pasts vai parole" in failed.text

    logged_in = client.post("/auth/login", data={"email": EMAIL, "password": PASSWORD})
    assert logged_in.status_code == 200
    assert "Tu esi pieteicies" in client.get("/").text


def test_html_form_escapes_input(client):
    response = client.post(
        "/auth/register", data={"email": "<script>x</script>", "password": PASSWORD}
    )
    assert response.status_code == 400
    assert "<script>" not in response.text


def test_unknown_route_uses_error_schema(client):
    response = client.get("/nav-tada-cela")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
