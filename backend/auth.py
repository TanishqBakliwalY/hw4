"""Create-account / log-in / log-out / current-user routes.

Sessions: on login the browser gets a random token in an HttpOnly cookie;
the server stores only its SHA-256 in the `sessions` table.
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from db import write_conn
from security import (
    DUMMY_HASH,
    MAX_PASSWORD_LENGTH,
    hash_password,
    hash_token,
    needs_rehash,
    new_session_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "cc_session"
SESSION_DAYS = 7
# Set COOKIE_SECURE=1 when served over HTTPS so the cookie is never sent in clear text.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
MIN_PASSWORD_LENGTH = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Brute-force protection: at most 5 failed logins per email and 20 per IP in 15 minutes.
WINDOW_SECONDS = 15 * 60
MAX_FAILS_PER_EMAIL = 5
MAX_FAILS_PER_IP = 20
_failures: dict[str, deque[float]] = defaultdict(deque)

INVALID_LOGIN = "Invalid email or password."


# ---------- schemas ----------


def _clean_email(v: str) -> str:
    v = v.strip().lower()
    if len(v) > 254 or not EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v


class RegisterIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _clean_email(v)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class UserOut(BaseModel):
    """Public user profile. Deliberately has no password_hash field."""

    id: int
    first_name: str
    last_name: str
    name: str
    email: str


def _user_out(row: sqlite3.Row) -> UserOut:
    first = row["first_name"] or row["name"].split(" ")[0]
    last = row["last_name"] or " ".join(row["name"].split(" ")[1:])
    return UserOut(id=row["id"], first_name=first, last_name=last, name=row["name"], email=row["email"])


# ---------- rate limiting ----------


def _recent(key: str) -> deque[float]:
    q = _failures[key]
    cutoff = time.monotonic() - WINDOW_SECONDS
    while q and q[0] < cutoff:
        q.popleft()
    return q


def _check_rate_limit(email: str, ip: str) -> None:
    if len(_recent(f"email:{email}")) >= MAX_FAILS_PER_EMAIL or len(_recent(f"ip:{ip}")) >= MAX_FAILS_PER_IP:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again in 15 minutes.")


def _record_failure(email: str, ip: str) -> None:
    now = time.monotonic()
    _failures[f"email:{email}"].append(now)
    _failures[f"ip:{ip}"].append(now)


# ---------- sessions ----------


def _start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = new_session_token()
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, datetime('now', ?))",
        (hash_token(token), user_id, f"+{SESSION_DAYS} days"),
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,  # JavaScript (and any injected script) can't read it
        samesite="lax",  # not sent on cross-site POSTs (CSRF protection)
        secure=COOKIE_SECURE,
        path="/",
    )


def current_user_optional(cc_session: str | None = Cookie(default=None)) -> UserOut | None:
    if not cc_session:
        return None
    with write_conn() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.email, u.first_name, u.last_name
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > datetime('now')
            """,
            (hash_token(cc_session),),
        ).fetchone()
    return _user_out(row) if row else None


def current_user(user: UserOut | None = Depends(current_user_optional)) -> UserOut:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return user


# ---------- routes ----------


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response) -> UserOut:
    with write_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (
                    f"{body.first_name} {body.last_name}",
                    body.email,
                    hash_password(body.password),
                    body.first_name,
                    body.last_name,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")
        user_id = cur.lastrowid
        _start_session(conn, response, user_id)
        row = conn.execute(
            "SELECT id, name, email, first_name, last_name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return _user_out(row)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response) -> UserOut:
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(email, ip)

    with write_conn() as conn:
        row = conn.execute(
            "SELECT id, name, email, first_name, last_name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        # Always run one hash check so unknown emails take as long as wrong passwords.
        ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH) and row is not None
        if not ok:
            _record_failure(email, ip)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

        if needs_rehash(row["password_hash"]):  # upgrade legacy seed hashes to current strength
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), row["id"]))
        _failures.pop(f"email:{email}", None)
        _start_session(conn, response, row["id"])
    return _user_out(row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    if cc_session:
        with write_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(cc_session),))
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(current_user)) -> UserOut:
    return user
