"""CR-4: darbinieka reģistrācija un pieteikšanās (HTML formas + JSON API).

Palaišana: `make run` (uvicorn app.main:create_app --factory).
"""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.db import Database, EmailTaken

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "app.db"
SESSION_COOKIE = "session"
MIN_PASSWORD_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


def error_body(code: str, message: str, details: list[dict] | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


def page(title: str, content: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="lv">
<head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 24rem; margin: 3rem auto; }}
label {{ display: block; margin-top: 1rem; }}
input {{ width: 100%; padding: .4rem; box-sizing: border-box; }}
button {{ margin-top: 1rem; padding: .5rem 1rem; }}
.error {{ color: #b00020; }}
</style></head>
<body><h1>{html.escape(title)}</h1>
{content}
</body></html>""",
        status_code=status_code,
    )


def auth_form(action: str, button: str, email: str = "", error: str = "") -> str:
    message = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return f"""{message}
<form method="post" action="{action}">
  <label>E-pasts <input type="email" name="email" value="{html.escape(email)}" required></label>
  <label>Parole <input type="password" name="password" minlength="{MIN_PASSWORD_LENGTH}" required></label>
  <button type="submit">{button}</button>
</form>"""


REGISTER_TITLE = "Reģistrācija"
LOGIN_TITLE = "Pieteikšanās"
REGISTER_LINK = '<p>Nav konta? <a href="/auth/register">Reģistrēties</a></p>'
LOGIN_LINK = '<p>Jau ir konts? <a href="/auth/login">Pieteikties</a></p>'

FIELD_MESSAGES = {
    ("email", "REQUIRED"): "Ievadi e-pastu.",
    ("email", "INVALID_FORMAT"): "E-pasta formāts nav derīgs.",
    ("password", "REQUIRED"): "Ievadi paroli.",
    ("password", "TOO_SHORT"): f"Parolei jābūt vismaz {MIN_PASSWORD_LENGTH} rakstzīmes garai.",
}


async def read_credentials(request: Request) -> tuple[dict[str, str] | None, bool]:
    """Nolasa e-pastu un paroli no JSON vai formas. Atgriež (dati, vai_forma)."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    raw = await request.body()
    if content_type == FORM_CONTENT_TYPE:
        parsed = parse_qs(raw.decode("utf-8", errors="replace"))
        return {key: values[0] for key, values in parsed.items()}, True
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None, False
    if not isinstance(data, dict):
        return None, False
    return {key: value for key, value in data.items() if isinstance(value, str)}, False


def validate_credentials(data: dict[str, str], check_rules: bool) -> list[dict]:
    details = []
    email = data.get("email", "").strip()
    password = data.get("password", "")
    if not email:
        details.append({"field": "email", "issue": "REQUIRED"})
    elif check_rules and not EMAIL_PATTERN.fullmatch(email):
        details.append({"field": "email", "issue": "INVALID_FORMAT"})
    if not password:
        details.append({"field": "password", "issue": "REQUIRED"})
    elif check_rules and len(password) < MIN_PASSWORD_LENGTH:
        details.append({"field": "password", "issue": "TOO_SHORT"})
    return details


def create_app(db_path: str | Path | None = None) -> FastAPI:
    db = Database(db_path or os.environ.get("AUTH_DB_PATH") or DEFAULT_DB_PATH)
    app = FastAPI(title="Ezermalas pieteikumu sistēma")

    # /docs rāda līgumu (patiesības avotu), nevis automātiski ģenerētu shēmu.
    contract = yaml.safe_load((ROOT / "docs" / "openapi.yaml").read_text(encoding="utf-8"))
    app.openapi = lambda: contract

    @app.exception_handler(404)
    async def not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(error_body("NOT_FOUND", "Not found"), status_code=404)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            error_body("INTERNAL_ERROR", "Internal server error"), status_code=500
        )

    def invalid(is_form: bool, title: str, email: str, details: list[dict]) -> Response:
        if is_form:
            message = " ".join(FIELD_MESSAGES[(d["field"], d["issue"])] for d in details)
            return page(title, form_for(title, email, message), 400)
        return JSONResponse(
            error_body("VALIDATION_ERROR", "Request validation failed", details),
            status_code=400,
        )

    def form_for(title: str, email: str = "", error: str = "") -> str:
        if title == REGISTER_TITLE:
            return auth_form("/auth/register", "Reģistrēties", email, error) + LOGIN_LINK
        return auth_form("/auth/login", "Pieteikties", email, error) + REGISTER_LINK

    @app.get("/", include_in_schema=False)
    def home(request: Request) -> HTMLResponse:
        token = request.cookies.get(SESSION_COOKIE)
        email = db.session_email(token) if token else None
        if email:
            return page("Sākums", f"<p>Tu esi pieteicies kā <b>{html.escape(email)}</b>.</p>")
        return page("Sākums", "<p>Tu neesi pieteicies.</p>" + LOGIN_LINK + REGISTER_LINK)

    @app.get("/auth/register", include_in_schema=False)
    def register_form() -> HTMLResponse:
        return page(REGISTER_TITLE, form_for(REGISTER_TITLE))

    @app.get("/auth/login", include_in_schema=False)
    def login_form() -> HTMLResponse:
        return page(LOGIN_TITLE, form_for(LOGIN_TITLE))

    @app.post("/auth/register")
    async def register(request: Request) -> Response:
        data, is_form = await read_credentials(request)
        if data is None:
            return invalid(False, REGISTER_TITLE, "", [{"field": "body", "issue": "INVALID_JSON"}])
        details = validate_credentials(data, check_rules=True)
        if details:
            return invalid(is_form, REGISTER_TITLE, data.get("email", ""), details)

        email = data["email"].strip().lower()
        try:
            account_id = db.create_account(email, data["password"])
        except EmailTaken:
            if is_form:
                return page(
                    REGISTER_TITLE,
                    form_for(REGISTER_TITLE, email, "Konts ar šādu e-pastu jau eksistē."),
                    409,
                )
            return JSONResponse(
                error_body("EMAIL_TAKEN", "Email is already registered"), status_code=409
            )

        if is_form:
            return page(
                "Konts izveidots",
                f"<p>Konts <b>{html.escape(email)}</b> izveidots.</p>" + LOGIN_LINK,
                201,
            )
        return JSONResponse({"id": account_id, "email": email}, status_code=201)

    @app.post("/auth/login")
    async def login(request: Request) -> Response:
        data, is_form = await read_credentials(request)
        if data is None:
            return invalid(False, LOGIN_TITLE, "", [{"field": "body", "issue": "INVALID_JSON"}])
        # Pieteikšanās laikā pārbauda tikai, vai lauki ir aizpildīti.
        details = validate_credentials(data, check_rules=False)
        if details:
            return invalid(is_form, LOGIN_TITLE, data.get("email", ""), details)

        email = data["email"].strip().lower()
        account_id = db.authenticate(email, data["password"])
        if account_id is None:
            if is_form:
                return page(
                    LOGIN_TITLE,
                    form_for(LOGIN_TITLE, email, "Nepareizs e-pasts vai parole."),
                    401,
                )
            return JSONResponse(
                error_body("INVALID_CREDENTIALS", "Invalid email or password"),
                status_code=401,
            )

        if is_form:
            response: Response = page(
                "Pieteikšanās izdevusies",
                f'<p>Tu esi pieteicies kā <b>{html.escape(email)}</b>.</p><p><a href="/">Uz sākumu</a></p>',
            )
        else:
            response = JSONResponse({"id": account_id, "email": email})
        response.set_cookie(
            SESSION_COOKIE, db.create_session(account_id), httponly=True, samesite="lax"
        )
        return response

    return app
