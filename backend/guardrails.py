"""Input safety guardrails that run BEFORE the model is called (Problem 9).

1. Sensitive-data screen: messages containing a payment card number, a password, or a US Social
   Security number are blocked -- they are never sent to the model provider, never written to
   chat_messages, and never logged. Earlier turns a guest's browser sends back are redacted too.
2. Chat rate limit: per logged-in user (or per IP for guests), to stop abuse and runaway API cost.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass

# ---------- sensitive-data screen ----------

# 13-19 digits, optionally separated by single spaces or dashes (e.g. 4111 1111 1111 1111).
_CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
# "my password is hunter2", "password: x", "pwd = x", "passcode is x"
_PASSWORD = re.compile(r"\b(?:password|passwd|passcode|pwd)\b\s*(?:is|=|:)\s*\S+", re.IGNORECASE)

BLOCKED_REPLY = {
    "card": (
        "For your security, please don't share card numbers in chat. I can't take payments here, and I've "
        "made sure that message wasn't stored or sent anywhere. Is there a product I can help you find?"
    ),
    "password": (
        "Please don't share passwords in chat. Campus Customs staff and this assistant will never ask for "
        "one. That message wasn't stored or sent anywhere. If you're worried someone knows your password, "
        "change it as soon as possible. Can I help you find some Yale gear?"
    ),
    "ssn": (
        "Please don't share Social Security or other ID numbers here. I don't need them, and that message "
        "wasn't stored or sent anywhere. How can I help you shop today?"
    ),
}
REDACTED_PLACEHOLDER = "[message removed: contained sensitive information]"


def _luhn_ok(digits: str) -> bool:
    total, double = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        double = not double
    return total % 10 == 0


def sensitive_kind(text: str) -> str | None:
    """Return "card" | "password" | "ssn" if the text contains that kind of sensitive data, else None."""
    for match in _CARD_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return "card"
    if _SSN.search(text):
        return "ssn"
    if _PASSWORD.search(text):
        return "password"
    return None


# ---------- rate limit ----------


@dataclass(frozen=True)
class Limit:
    max_messages: int
    window_seconds: int


CHAT_LIMITS = (Limit(10, 60), Limit(100, 60 * 60))  # 10 per minute burst, 100 per hour
_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limited(key: str) -> int | None:
    """Record one chat message for `key`; return seconds to wait if over a limit, else None."""
    now = time.monotonic()
    q = _hits[key]
    longest = max(l.window_seconds for l in CHAT_LIMITS)
    while q and q[0] <= now - longest:
        q.popleft()
    for limit in CHAT_LIMITS:
        recent = [t for t in q if t > now - limit.window_seconds]
        if len(recent) >= limit.max_messages:
            return int(recent[0] + limit.window_seconds - now) + 1
    q.append(now)
    return None
