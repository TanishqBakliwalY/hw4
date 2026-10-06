"""Pydantic / PydanticAI structured types shared by the API, the tools, and the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ---------- products (API responses + product cards) ----------

# Normalized from the 22 free-text catalogue.garment_type values (see tools.category_of).
Category = Literal["t-shirt", "long-sleeve shirt", "crewneck", "mockneck", "hoodie", "quarter-zip", "jacket"]
MAX_PAGE_MATCHES = 30  # largest category (crewneck) has 28 products


class SizeStock(BaseModel):
    size: str = Field(description="One of XS, S, M, L, XL, XXL")
    quantity: int = Field(ge=0, description="Units in stock for this size (0 = sold out)")


class ProductCard(BaseModel):
    """A product as shown on a card: on the Products page or under a chat reply."""

    product_id: str
    name: str
    garment_type: str
    category: Category
    description: str
    colors: list[str]
    price: float = Field(description="Price in USD, from catalogue.price")
    image_url: str
    total_stock: int = Field(description="Sum of inventory.quantity across sizes")
    sizes_in_stock: list[str] = Field(default_factory=list, description="Sizes with quantity > 0, XS→XXL")


class ProductDetail(ProductCard):
    search_tags: list[str]
    inventory: list[SizeStock]


# ---------- tool results (what the agent sees) ----------


class ProductSearchHit(BaseModel):
    """Compact search result returned to the agent by search_products."""

    product_id: str
    name: str
    garment_type: str
    category: Category
    colors: list[str]
    price: float
    total_stock: int
    sizes_in_stock: list[str]


class ProductSearchResult(BaseModel):
    query: str
    category: Category | None = None
    total_matches: int
    products: list[ProductSearchHit]


# ---------- lookup tool results (Problem 6) ----------

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class ProductNotFound(BaseModel):
    """Returned instead of a lookup result when the product reference doesn't match the catalogue."""

    found: Literal[False] = False
    product_ref: str = Field(description="What the agent asked for")
    message: str
    did_you_mean: list[ProductSearchHit] = Field(
        default_factory=list, description="Closest catalogue matches, so the agent can retry with a real product_id"
    )


class ProductDescription(BaseModel):
    """get_product_description result: what the product is and looks like (no price/stock)."""

    found: Literal[True] = True
    product_id: str
    name: str
    garment_type: str
    description: str = Field(description="Catalogue description, verbatim from catalogue.description")
    colors: list[str] = Field(description="Every colour in this product's single colourway")
    tags: list[str] = Field(description="catalogue.search_tags: college, sport, design keywords")


class PriceQuote(BaseModel):
    product_id: str
    name: str
    price: float = Field(description="USD, verbatim from catalogue.price")
    price_display: str = Field(description='Formatted price to quote exactly, e.g. "$68.00"')


class PriceLookup(BaseModel):
    """get_price result for one or more products."""

    currency: Literal["USD"] = "USD"
    prices: list[PriceQuote]
    not_found: list[ProductNotFound] = Field(default_factory=list)


class SizeAvailability(BaseModel):
    size: str = Field(description="XS, S, M, L, XL or XXL")
    quantity: int = Field(ge=0, description="Units on hand, verbatim from inventory.quantity")
    status: StockStatus = Field(description="sold_out = 0, low_stock = 1-5, in_stock = 6+")


class StockLookup(BaseModel):
    """check_stock result: live inventory for one product, optionally focused on one size."""

    found: Literal[True] = True
    product_id: str
    name: str
    requested_size: str | None = Field(description="Normalized size the shopper asked about, if any")
    requested_size_status: StockStatus | Literal["not_a_size"] | None = Field(
        description="Status of requested_size; not_a_size if the shopper's size isn't one we stock"
    )
    requested_size_quantity: int | None = None
    sizes: list[SizeAvailability] = Field(description="Every size, in XS→XXL order, including sold-out ones")
    sizes_in_stock: list[str]
    sold_out_sizes: list[str]
    total_units: int = Field(description="Sum of quantity across all sizes")
    checked_at: str = Field(description="UTC time the database was read (stock can change)")


# ---------- agent output ----------


class ProductMatches(BaseModel):
    """Products the website should show as cards on the page (agent -> API contract)."""

    title: str = Field(
        max_length=60,
        description='Short heading for the cards, e.g. "Hoodies", "Navy crewnecks under $60", "Basic Hoodie Big Yale"',
    )
    product_ids: list[str] = Field(
        min_length=1,
        max_length=MAX_PAGE_MATCHES,
        description="product_id values copied from THIS turn's tool results, most relevant first",
    )


class ChatReply(BaseModel):
    """Structured output the agent must return on every turn."""

    reply: str = Field(
        description="The message shown to the shopper, in Markdown. Prices and stock must come from tool results."
    )
    product_matches: ProductMatches | None = Field(
        default=None,
        description=(
            "Products to display as cards on the website for this reply. Set it whenever the reply is about "
            "specific products or a search/browse request; null for general questions or refusals."
        ),
    )


# ---------- alternatives tool (Problem 9) ----------


class AlternativeHit(BaseModel):
    product_id: str
    name: str
    category: Category
    price: float
    price_display: str
    colors: list[str]
    requested_size_quantity: int | None = Field(
        default=None, description="Units in stock in the requested size (None if no size was requested)"
    )
    sizes_in_stock: list[str]
    match_reasons: list[str] = Field(description='Why it is similar, e.g. "same category (hoodie)", "also Branford"')


class AlternativesResult(BaseModel):
    """find_alternatives result: in-stock substitutes for a product (optionally in one size)."""

    found: Literal[True] = True
    for_product_id: str
    for_product_name: str
    requested_size: str | None
    original_status: str = Field(
        description="Stock of the original item in the requested size (or overall): in_stock / low_stock / sold_out"
    )
    alternatives: list[AlternativeHit]
    note: str


# ---------- who is chatting + where they are (Problem 8) ----------


class CustomerContext(BaseModel):
    """The logged-in shopper, loaded server-side from the users table via the session cookie.

    Deliberately excludes password_hash and anything about other customers.
    """

    user_id: int
    first_name: str
    last_name: str
    name: str
    email: str
    member_since: str = Field(description="users.created_at (UTC)")


class PageContext(BaseModel):
    """Where the shopper is on the website when they send a message (sent by the front end)."""

    path: str = Field(default="/", max_length=300, description='Current URL path, e.g. "/products/basic-hoodie-big-yale"')
    page_type: Literal["home", "products", "product", "about", "login", "create-account", "other"] = "other"
    product_id: str | None = Field(default=None, max_length=120, description="Set when on a single-product page")
    search_query: str | None = Field(default=None, max_length=200, description="Products page ?q= search, if any")
    chat_results_title: str | None = Field(
        default=None, max_length=80, description="Title of the chat product cards currently shown on the page"
    )


class ViewedProduct(BaseModel):
    """Server-verified version of PageContext.product_id (name looked up in the DB, never trusted from the client)."""

    product_id: str
    name: str


@dataclass
class ChatDeps:
    """Per-request agent dependencies: who is chatting and what page they're on.

    Built by main.py for every /api/chat call and available to instructions and tools via ctx.deps.
    """

    customer: CustomerContext | None = None
    page: PageContext = field(default_factory=PageContext)
    viewed_product: ViewedProduct | None = None


class CustomerProfile(BaseModel):
    """get_my_account tool result: the logged-in shopper's own account details."""

    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = None
    saved_chat_messages: int = 0
    message: str


class CurrentPageInfo(BaseModel):
    """get_current_page tool result: where the shopper is and which product "this" refers to."""

    path: str
    page_type: str
    viewing_product: ProductDescription | None = Field(
        default=None, description='The product on screen; what "this" / "it" means on a product page'
    )
    search_query: str | None = None
    chat_results_title: str | None = None


# ---------- audit trail (Problem 12) ----------

StopReason = Literal[
    "completed",  # agent produced a validated ChatReply
    "usage_limit",  # hit a loop limit (requests / tool calls / tokens)
    "content_filter",  # provider safety filter refused the message
    "guardrail_blocked",  # our pre-model screen blocked card/password/SSN data
    "rate_limited",  # too many messages from this user/IP
    "error",  # model/API/other failure
]


class AuditEntry(BaseModel):
    """One line of output/audit_trail.json: a step of the agent loop (or a request stopped before it).

    Text fields are short summaries with emails masked; sensitive messages are never recorded.
    """

    timestamp: str = Field(description="UTC ISO-8601 time the entry was written")
    run_id: str = Field(description="Groups the entries of one chat request")
    step: int = Field(description="Order within the run: 1..n tool calls, then the final entry")
    event: Literal["tool_call", "validator_retry", "final"] = "tool_call"
    actor: str = Field(description='"user:<id>" or "guest" (no names or emails)')
    page: str = Field(default="/", description="Path the shopper was on")
    request: str = Field(description="Shopper's message, truncated (or a redaction note)")
    tool_name: str | None = Field(default=None, description="Tool called, final_result for the answer, or None")
    tool_args: str | None = Field(default=None, description="Short JSON of the tool arguments")
    tool_result: str | None = Field(default=None, description="Short summary of what the tool returned")
    stop_reason: StopReason = Field(description="How this run ended (same value on every entry of the run)")
    model: str
    duration_ms: int | None = Field(default=None, description="Whole-run time (final entry)")
    input_tokens: int | None = None
    output_tokens: int | None = None


# ---------- chat API ----------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    product_ids: list[str] = Field(
        default_factory=list, max_length=MAX_PAGE_MATCHES, description="Products shown with this assistant turn"
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Used for guests only; logged-in shoppers' history is loaded from the database.
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext = Field(default_factory=PageContext)


class PageMatches(BaseModel):
    """API -> front end: product cards rebuilt from live DB rows for ProductMatches.product_ids."""

    title: str
    products: list[ProductCard]


class ChatResponse(BaseModel):
    reply: str
    matches: PageMatches | None = None
    saved: bool = Field(default=False, description="True when the turn was stored in chat_messages (logged in)")
    blocked: Literal["card", "password", "ssn"] | None = Field(
        default=None, description="Set when the message was stopped by the input guardrail (never sent or saved)"
    )


class ChatHistoryMessage(BaseModel):
    """GET /api/chat/history item: one stored message, with product cards rebuilt live."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    matches: PageMatches | None = None
    created_at: str
