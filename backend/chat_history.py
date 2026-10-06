"""Persistent chat history for logged-in shoppers, stored in the seed `chat_messages` table.

    chat_messages(id, user_id -> users.id, role 'user'|'assistant', content,
                  products_json, created_at)

products_json keeps the seed format: a JSON list of product-card snapshots shown with an
assistant reply (NULL for user messages). On reload only the product_id values are used and
cards are rebuilt from live catalogue/inventory rows, so old snapshots never show stale prices.
"""

from __future__ import annotations

import json

import tools
from db import write_conn
from models import ChatHistoryMessage, ChatTurn, CustomerContext, PageMatches

HISTORY_FOR_AGENT = 20  # most recent messages sent to the model as context
HISTORY_FOR_UI = 100  # most recent messages shown in the chat widget
EARLIER_RESULTS_TITLE = "Products from this chat"


def load_customer(user_id: int) -> CustomerContext | None:
    with write_conn() as conn:
        row = conn.execute(
            "SELECT id, name, email, first_name, last_name, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    parts = row["name"].split(" ")
    return CustomerContext(
        user_id=row["id"],
        first_name=row["first_name"] or parts[0],
        last_name=row["last_name"] or " ".join(parts[1:]),
        name=row["name"],
        email=row["email"],
        member_since=row["created_at"],
    )


def _product_ids(products_json: str | None) -> list[str]:
    if not products_json:
        return []
    try:
        data = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    items = data.get("products", []) if isinstance(data, dict) else data
    return [p["product_id"] for p in items if isinstance(p, dict) and "product_id" in p]


def _recent_rows(user_id: int, limit: int):
    with write_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, products_json, created_at FROM chat_messages
            WHERE user_id = ? ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def recent_turns(user_id: int) -> list[ChatTurn]:
    """The shopper's last messages as model history (server-side, so the client can't rewrite it)."""
    return [
        ChatTurn(role=r["role"], content=r["content"][:4000], product_ids=_product_ids(r["products_json"])[:30])
        for r in _recent_rows(user_id, HISTORY_FOR_AGENT)
        if r["role"] in ("user", "assistant")
    ]


def history_for_ui(user_id: int) -> list[ChatHistoryMessage]:
    out = []
    for r in _recent_rows(user_id, HISTORY_FOR_UI):
        if r["role"] not in ("user", "assistant"):
            continue
        cards = tools.get_cards(_product_ids(r["products_json"]))
        out.append(
            ChatHistoryMessage(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                matches=PageMatches(title=EARLIER_RESULTS_TITLE, products=cards) if cards else None,
                created_at=r["created_at"],
            )
        )
    return out


def save_turn(user_id: int, user_message: str, reply: str, matches: PageMatches | None) -> None:
    """Store the shopper's message and the assistant's reply together (one transaction)."""
    products_json = json.dumps([p.model_dump() for p in matches.products]) if matches else json.dumps([])
    with write_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, user_message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, products_json),
        )


def clear_history(user_id: int) -> int:
    with write_conn() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
