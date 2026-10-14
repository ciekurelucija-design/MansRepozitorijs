"""CR-4: kontu un sesiju glabāšana SQLite datubāzē."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# scrypt parametri: n=2**14, r=8, p=1 (OWASP ieteiktais minimums)
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


class EmailTaken(Exception):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, n, r, p, salt, digest = stored.split("$")
    candidate = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
    )
    return hmac.compare_digest(candidate.hex(), digest)


# Izmanto, ja e-pasts nav atrasts, lai atbildes laiks neatklātu konta esamību.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_account(self, email: str, password: str) -> int:
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO accounts (email, password_hash) VALUES (?, ?)",
                    (email, hash_password(password)),
                )
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise EmailTaken(email) from exc

    def authenticate(self, email: str, password: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, password_hash FROM accounts WHERE email = ?", (email,)
            ).fetchone()
        if row is None:
            verify_password(password, _DUMMY_HASH)
            return None
        account_id, stored = row
        return account_id if verify_password(password, stored) else None

    def create_session(self, account_id: int) -> str:
        token = secrets.token_urlsafe(32)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token_hash, account_id) VALUES (?, ?)",
                (_hash_token(token), account_id),
            )
        return token

    def session_email(self, token: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT a.email FROM sessions s JOIN accounts a ON a.id = s.account_id "
                "WHERE s.token_hash = ?",
                (_hash_token(token),),
            ).fetchone()
        return row[0] if row else None
