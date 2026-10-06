"""Password hashing and session tokens (Python standard library only).

Stored hash formats (users.password_hash):
  * current: pbkdf2_sha256$<iterations>$<salt>$<hex digest>   -- new accounts
  * legacy:  pbkdf2_sha256$<salt>$<hex digest>                -- seed users, 120,000 iterations

Legacy hashes still verify, and are upgraded to the current format the next
time that user logs in successfully.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
LEGACY_ITERATIONS = 120_000  # iteration count used by the seed database
SALT_BYTES = 16
MAX_PASSWORD_LENGTH = 128  # caps hashing cost per request


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${ITERATIONS}${salt}${_pbkdf2(password, salt, ITERATIONS)}"


def _parse(stored: str) -> tuple[int, str, str] | None:
    parts = stored.split("$")
    if parts[0] != ALGORITHM:
        return None
    if len(parts) == 4 and parts[1].isdigit():
        return int(parts[1]), parts[2], parts[3]
    if len(parts) == 3:
        return LEGACY_ITERATIONS, parts[1], parts[2]
    return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if parsed is None:
        return False
    iterations, salt, digest = parsed
    # constant-time comparison so response timing doesn't leak how close a guess was
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), digest)


def needs_rehash(stored: str) -> bool:
    parsed = _parse(stored)
    return parsed is None or parsed[0] < ITERATIONS


# A real hash of a random password: used to spend the same time on unknown
# emails as on wrong passwords, so attackers can't tell which emails exist.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only a SHA-256 of the session token is stored, so a leaked DB can't be replayed as cookies."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
