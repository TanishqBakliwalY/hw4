"""Campus Customs API: the FastAPI app served by Uvicorn.

  Problem 3: product catalogue, per-size inventory and product images.
  Problem 4: account creation / login (auth.py).
  Problem 5: shop chatbot (POST /api/chat -> PydanticAI agent in agent.py).
  Problem 8: saved chat history for logged-in shoppers + customer/page context for the agent.
  Problem 9: product filters/sort, find_alternatives tool, input guardrails (guardrails.py).
  Problem 12: append-only audit trail (audit.py -> output/audit_trail.json) + agent loop limits.

Run from the backend folder:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import re
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded

import audit
import chat_history
import guardrails
import tools
from agent import AgentConfigError, model_name, run_chat
from auth import UserOut, current_user, current_user_optional
from auth import router as auth_router
from db import DATA_DIR, init_db
from models import (
    AuditEntry,
    Category,
    ChatDeps,
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    PageContext,
    PageMatches,
    ProductCard,
    ProductDetail,
    ViewedProduct,
)

log = logging.getLogger("campus_customs")
# Show our own INFO logs (e.g. which tools the agent called) without turning on noisy library logs.
if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)

# Only the product image folder is exposed -- never the whole data/ folder,
# which also contains the database file.
IMAGES_DIR = DATA_DIR / "products"

USAGE_LIMIT_REPLY = (
    "Woof, that one needed more lookups than I can do in a single answer. Could you ask about one or two "
    "products at a time? For example: \"Is the Basic Hoodie Big Yale in stock in M?\""
)

CONTENT_FILTER_REPLY = (
    "Sorry, I can't help with that. I'm Handsome Dan, the Campus Customs shopping assistant, so I can help you "
    "find Yale apparel, check prices and sizes, or answer questions about the store."
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Campus Customs API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI echoes the rejected "input" by default -- that would send passwords back in error responses.
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


app.include_router(auth_router)

app.mount("/images/products", StaticFiles(directory=IMAGES_DIR), name="product-images")


# ---------- products ----------


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": model_name()}


@app.get("/api/products", response_model=list[ProductCard])
def list_products(
    q: str | None = Query(None, max_length=200, description="Keywords matched against name, type, colours, tags and description"),
    category: Category | None = Query(None, description="Normalized garment category"),
    size: Literal["XS", "S", "M", "L", "XL", "XXL"] | None = Query(None, description="Only products in stock in this size"),
    sort: tools.SortOrder = Query("relevance", description="relevance | name | price_asc | price_desc"),
) -> list[ProductCard]:
    return tools.list_products(q.strip() if q else None, category, size, sort)


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> ProductDetail:
    product = tools.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ---------- chat ----------

_UNSAFE_TEXT = re.compile(r"[^\w\s\-.,'&$/?=%:#()!]")
_SAFE_PATH = re.compile(r"^/[\w\-./?=&%]*$")


def _clean(text: str | None, limit: int) -> str | None:
    """Page context comes from the browser and is shown to the model: keep it short, single-line, plain."""
    if not text:
        return None
    text = _UNSAFE_TEXT.sub("", " ".join(text.split()))[:limit].strip()
    return text or None


def _build_deps(page: PageContext, user: UserOut | None) -> ChatDeps:
    """Agent context: the customer comes from the session cookie (server-side); page details are
    sanitized, and the viewed product is only accepted if it exists in the catalogue."""
    customer = chat_history.load_customer(user.id) if user else None
    page = PageContext(
        path=page.path if _SAFE_PATH.match(page.path or "") else "/",
        page_type=page.page_type,
        product_id=page.product_id,
        search_query=_clean(page.search_query, 100),
        chat_results_title=_clean(page.chat_results_title, 60),
    )
    viewed = None
    if page.product_id:
        product = tools.get_product(page.product_id)
        if product:
            viewed = ViewedProduct(product_id=product.product_id, name=product.name)
    return ChatDeps(customer=customer, page=page, viewed_product=viewed)


def _audit_stop(base: dict, stop_reason: str, result: str) -> None:
    """Record a request that was stopped before the agent loop ran (no model call was made)."""
    try:
        audit.append([
            AuditEntry(**base, timestamp=audit.now(), step=1, event="final", tool_result=result,
                       stop_reason=stop_reason, model=model_name(), duration_ms=0)
        ])
    except Exception:
        log.exception("Could not write audit trail")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest, request: Request, user: UserOut | None = Depends(current_user_optional)
) -> ChatResponse:
    message = body.message.strip()
    kind = guardrails.sensitive_kind(message)
    # Audit context for this request; sensitive messages are never written to the trail.
    audit_base = {
        "run_id": uuid.uuid4().hex[:10],
        "actor": f"user:{user.id}" if user else "guest",
        "page": body.page.path if _SAFE_PATH.match(body.page.path or "") else "/",
        "request": f"[redacted: message contained {kind} data]" if kind else audit.short(message, audit.MAX_REQUEST),
    }

    # Guardrail 1: rate limit per account (or per IP for guests) before any model cost is incurred.
    key = f"user:{user.id}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
    wait = guardrails.rate_limited(key)
    if wait:
        _audit_stop(audit_base, "rate_limited", f"429: wait {wait}s")
        raise HTTPException(429, f"You're sending messages very quickly. Please wait {wait} seconds and try again.")

    # Guardrail 2: card numbers / passwords / SSNs never reach the model, the database or the logs.
    if kind:
        log.warning("Guardrail blocked a message containing %s data (%s)", kind, key)
        _audit_stop(audit_base, "guardrail_blocked", f"blocked {kind}; fixed safety reply sent")
        return ChatResponse(reply=guardrails.BLOCKED_REPLY[kind], blocked=kind)

    deps = _build_deps(body.page, user)
    # Logged-in shoppers: history comes from the database (trusted, survives reloads/devices).
    # Guests: the browser sends its in-memory history, which is never stored; any sensitive
    # data in it is redacted before it reaches the model.
    if user:
        history = chat_history.recent_turns(user.id)
    else:
        history = [
            t.model_copy(update={"content": guardrails.REDACTED_PLACEHOLDER}) if guardrails.sensitive_kind(t.content) else t
            for t in body.history
        ]
    try:
        output = await run_chat(message, history, deps, audit_base)
    except UsageLimitExceeded as e:
        log.warning("Agent loop limit reached: %s", e)
        return ChatResponse(reply=USAGE_LIMIT_REPLY)
    except AgentConfigError as e:
        log.error("Chat unavailable: %s", e)
        raise HTTPException(503, "The shopping assistant isn't configured yet. Please try again later.")
    except ModelHTTPError as e:
        # The model provider's content filter (e.g. jailbreak / prompt-injection shields) rejected the
        # message before the model answered. Treat it as a refusal rather than a server error.
        if "content_filter" in str(e.body):
            log.warning("Message blocked by provider content filter")
            return ChatResponse(reply=CONTENT_FILTER_REPLY)
        log.exception("Model API error")
        raise HTTPException(502, "Sorry, the assistant ran into a problem. Please try again.")
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(502, "Sorry, the assistant ran into a problem. Please try again.")

    # API contract: the agent returns product_matches {title, product_ids}; the API rebuilds each
    # card from live DB rows (so prices/stock are current and unknown ids are dropped) and the
    # front end renders them on the page as clickable ProductCards.
    matches = None
    if output.product_matches:
        cards = tools.get_cards(output.product_matches.product_ids)
        if cards:
            matches = PageMatches(title=output.product_matches.title, products=cards)

    saved = False
    if user:
        chat_history.save_turn(user.id, message, output.reply, matches)
        saved = True
    return ChatResponse(reply=output.reply, matches=matches, saved=saved)


@app.get("/api/chat/history", response_model=list[ChatHistoryMessage])
def get_chat_history(user: UserOut | None = Depends(current_user_optional)) -> list[ChatHistoryMessage]:
    """The logged-in shopper's saved conversation (oldest first). Guests have no saved history."""
    return chat_history.history_for_ui(user.id) if user else []


@app.delete("/api/chat/history", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_history(user: UserOut = Depends(current_user)) -> None:
    chat_history.clear_history(user.id)
