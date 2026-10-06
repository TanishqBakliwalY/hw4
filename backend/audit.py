"""Append-only audit trail of agent-loop activity: output/audit_trail.json (Problem 12).

The file is a JSON array. Entries are only ever APPENDED: each write reads the existing array,
adds the new entries and atomically replaces the file (temp file + os.replace), so a crash can't
leave half a file and nothing is ever removed between runs. If the file is ever unreadable it is
moved aside (never deleted) and a new array is started.

Privacy: summaries are truncated and email addresses are masked; messages stopped by the
guardrail are recorded only as "[redacted: ...]".
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import AuditEntry

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_TEXT = 300  # cap for args/result summaries
MAX_REQUEST = 200  # cap for the shopper's message

_lock = threading.Lock()
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def short(value: Any, limit: int = MAX_TEXT) -> str:
    """Compact, email-masked, length-capped text for the trail."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = _EMAIL.sub("[email]", " ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append(entries: list[AuditEntry]) -> None:
    if not entries:
        return
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: list = []
        if AUDIT_PATH.exists():
            try:
                existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
                if not isinstance(existing, list):
                    raise ValueError("audit trail is not a JSON list")
            except (ValueError, json.JSONDecodeError):
                # Never wipe history: keep the unreadable file next to the new one.
                AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json"))
                existing = []
        existing.extend(e.model_dump() for e in entries)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)


def entries_from_messages(messages: list, base: dict) -> list[AuditEntry]:
    """Turn one run's PydanticAI messages into ordered audit entries (tool calls + validator retries)."""
    returns: dict[str, str] = {}
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if part.part_kind == "tool-return":
                returns[part.tool_call_id] = part.model_response_str()

    out: list[AuditEntry] = []
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if part.part_kind == "tool-call" and part.tool_name != "final_result":
                out.append(
                    AuditEntry(
                        **base,
                        timestamp=now(),
                        step=len(out) + 1,
                        event="tool_call",
                        tool_name=part.tool_name,
                        tool_args=short(part.args_as_json_str()),
                        tool_result=short(returns.get(part.tool_call_id, "(no result: run stopped)")),
                    )
                )
            elif part.part_kind == "retry-prompt":
                out.append(
                    AuditEntry(
                        **base,
                        timestamp=now(),
                        step=len(out) + 1,
                        event="validator_retry",
                        tool_name=getattr(part, "tool_name", None),
                        tool_result=short(part.model_response()),
                    )
                )
    return out
