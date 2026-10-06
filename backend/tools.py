"""Tools the agent can call, plus the catalogue queries they share with the product API.

Every price and stock number the agent quotes must come from these functions,
which read data/campus_customs.db through a READ-ONLY connection. The only tool that
reads the users table is get_my_account, and it can only see the logged-in shopper's
own row (the user id comes from the server-side session via ctx.deps, never from the model).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from pydantic_ai import RunContext

from db import read_conn
from models import (
    MAX_PAGE_MATCHES,
    AlternativeHit,
    AlternativesResult,
    Category,
    ChatDeps,
    CurrentPageInfo,
    CustomerProfile,
    PriceLookup,
    PriceQuote,
    ProductCard,
    ProductDescription,
    ProductDetail,
    ProductNotFound,
    ProductSearchHit,
    ProductSearchResult,
    SizeAvailability,
    SizeStock,
    StockLookup,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_RESULTS = 10  # cap for get_price

PRODUCT_SELECT = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
           GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_csv
    FROM catalogue c
    LEFT JOIN inventory i ON i.product_id = c.product_id
"""

# ---------- shared catalogue queries ----------


def category_of(garment_type: str) -> Category:
    """Normalize the 22 free-text garment_type values into 7 shopper-facing categories."""
    g = garment_type.lower()
    if "hood" in g:
        return "hoodie"
    if "quarter-zip" in g:
        return "quarter-zip"
    if "jacket" in g:
        return "jacket"
    if "t-shirt" in g:
        return "t-shirt"
    if "performance shirt" in g:
        return "long-sleeve shirt"
    if "mockneck" in g:
        return "mockneck"
    return "crewneck"


def _image_url(image_file_path: str) -> str:
    # DB stores "products/<id>.jpg"; the API serves it at /images/products/<id>.jpg
    return f"/images/{image_file_path}"


def _card(row: sqlite3.Row) -> ProductCard:
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=category_of(row["garment_type"]),
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        image_url=_image_url(row["image_file_path"]),
        total_stock=row["total_stock"],
        sizes_in_stock=sorted(
            (row["sizes_csv"] or "").split(",") if row["sizes_csv"] else [],
            key=lambda sz: SIZE_ORDER.index(sz) if sz in SIZE_ORDER else len(SIZE_ORDER),
        ),
    )


def _all_rows() -> list[sqlite3.Row]:
    with read_conn() as conn:
        return conn.execute(PRODUCT_SELECT + " GROUP BY c.product_id ORDER BY c.name").fetchall()


def _inventory(conn: sqlite3.Connection, product_ids: list[str]) -> dict[str, list[SizeStock]]:
    if not product_ids:
        return {}
    marks = ",".join("?" * len(product_ids))
    rows = conn.execute(
        f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({marks})", product_ids
    ).fetchall()
    out: dict[str, list[SizeStock]] = {pid: [] for pid in product_ids}
    for r in rows:
        out[r["product_id"]].append(SizeStock(size=r["size"], quantity=r["quantity"]))
    for sizes in out.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))
    return out


SortOrder = Literal["relevance", "name", "price_asc", "price_desc"]


def list_products(
    q: str | None = None,
    category: Category | None = None,
    size: str | None = None,
    sort: SortOrder = "relevance",
) -> list[ProductCard]:
    """Products page: optional keyword search, category, "in stock in size", and sort order."""
    rows = _all_rows()
    if category:
        rows = [r for r in rows if category_of(r["garment_type"]) == category]
    if q:
        rows = [r for r, _ in _rank(rows, q)]  # relevance order
    if size:
        wanted = normalize_size(size)
        with read_conn() as conn:
            inv = _inventory(conn, [r["product_id"] for r in rows])
        rows = [r for r in rows if any(s.size == wanted and s.quantity > 0 for s in inv[r["product_id"]])]
    if sort == "name" or (sort == "relevance" and not q):
        rows = sorted(rows, key=lambda r: r["name"])
    elif sort == "price_asc":
        rows = sorted(rows, key=lambda r: (r["price"], r["name"]))
    elif sort == "price_desc":
        rows = sorted(rows, key=lambda r: (-r["price"], r["name"]))
    return [_card(r) for r in rows]


def get_product(product_id: str) -> ProductDetail | None:
    with read_conn() as conn:
        row = conn.execute(
            PRODUCT_SELECT + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)
        ).fetchone()
        if row is None:
            return None
        inventory = _inventory(conn, [product_id])[product_id]
    return ProductDetail(**_card(row).model_dump(), search_tags=json.loads(row["search_tags"]), inventory=inventory)


def get_cards(product_ids: list[str]) -> list[ProductCard]:
    """Live product cards for the given IDs, in the given order; unknown IDs are dropped."""
    if not product_ids:
        return []
    marks = ",".join("?" * len(product_ids))
    with read_conn() as conn:
        rows = conn.execute(
            PRODUCT_SELECT + f" WHERE c.product_id IN ({marks}) GROUP BY c.product_id", product_ids
        ).fetchall()
    by_id = {r["product_id"]: _card(r) for r in rows}
    return [by_id[pid] for pid in dict.fromkeys(product_ids) if pid in by_id]


# ---------- keyword search ----------

STOPWORDS = {
    "a", "an", "and", "any", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my", "of",
    "or", "show", "some", "the", "to", "with", "you", "your", "want", "looking", "need", "something",
    "under", "below", "less", "than", "cheap", "price", "size", "stock", "available",
    "yale", "campus", "customs", "merch",  # appear on almost every product, so they don't help ranking
}
SYNONYMS = {
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt",
    "hoody": "hoodie", "hoodies": "hoodie", "hooded": "hoodie",
    "quarterzip": "quarter-zip", "1/4": "quarter-zip",
    "grey": "gray",
}


CATEGORY_WORDS = {
    "hoodie", "sweatshirt", "t-shirt", "shirt", "crewneck", "crew-neck", "jacket", "quarter-zip", "zip",
    "quarter", "mockneck", "long-sleeve", "long", "sleeve", "pullover", "top", "clothe", "item", "apparel",
}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9/'-]+", text.lower())
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        w = SYNONYMS.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _rank(rows: list[sqlite3.Row], query: str) -> list[tuple[sqlite3.Row, int]]:
    """Score rows by keyword matches (name/tags 3, type/colours 2, description 1), best first.

    Rows matching no keyword are dropped; an empty query keeps every row (alphabetical).
    """
    terms = _tokens(query)
    if not terms:
        return [(r, 0) for r in rows]
    ranked = []
    for r in rows:
        name, gtype = r["name"].lower(), r["garment_type"].lower()
        tags, colors, desc = r["search_tags"].lower(), r["colors"].lower(), r["description"].lower()
        score = 0
        for t in terms:
            if t in name or t in tags:
                score += 3
            elif t in gtype or t in colors:
                score += 2
            elif t in desc:
                score += 1
        if score:
            ranked.append((r, score))
    ranked.sort(key=lambda x: (-x[1], x[0]["name"]))
    return ranked


# ---------- agent tools ----------


def search_products(
    query: str = "",
    category: Category | None = None,
    max_price: float | None = None,
    size_in_stock: str | None = None,
    limit: int = 8,
) -> ProductSearchResult:
    """Search the Campus Customs catalogue. Results are what the website shows as product cards.

    For "what hoodies / tees / jackets do you have?" pass `category` (query can be empty) and a
    high `limit` so the shopper sees the whole range. Add keywords to narrow or re-order results.

    Args:
        query: Keywords such as colour, college, sport or design (e.g. "navy", "Branford", "baseball").
            May be empty when `category` is given.
        category: One of t-shirt, long-sleeve shirt, crewneck, mockneck, hoodie, quarter-zip, jacket.
        max_price: Only return products at or below this USD price.
        size_in_stock: Only return products with stock in this size (XS, S, M, L, XL, XXL).
        limit: Maximum products to return (1-30).
    """
    limit = max(1, min(limit, MAX_PAGE_MATCHES))
    size = normalize_size(size_in_stock) if size_in_stock else None
    rows = _all_rows()
    if category:
        rows = [r for r in rows if category_of(r["garment_type"]) == category]
        # Words that only restate the category ("hoodies", "crewneck sweatshirt") would filter out
        # products whose text happens not to repeat them, so drop them; remaining keywords
        # (colour, college, sport...) still filter within the category.
        query = " ".join(t for t in _tokens(query) if t not in CATEGORY_WORDS)
    ranked = _rank(rows, query)
    rows = [r for r, _ in ranked if max_price is None or r["price"] <= max_price]

    with read_conn() as conn:
        inv = _inventory(conn, [r["product_id"] for r in rows])
    hits = []
    for r in rows:
        in_stock = [s.size for s in inv[r["product_id"]] if s.quantity > 0]
        if size and size not in in_stock:
            continue
        hits.append(
            ProductSearchHit(
                product_id=r["product_id"],
                name=r["name"],
                garment_type=r["garment_type"],
                category=category_of(r["garment_type"]),
                colors=json.loads(r["colors"]),
                price=r["price"],
                total_stock=r["total_stock"],
                sizes_in_stock=in_stock,
            )
        )
    return ProductSearchResult(query=query, category=category, total_matches=len(hits), products=hits[:limit])


# ---------- lookup helpers (Problem 6) ----------

LOW_STOCK_MAX = 5  # same threshold the product page uses for "Only N left"

SIZE_ALIASES = {
    "XS": "XS", "XSMALL": "XS", "EXTRASMALL": "XS",
    "S": "S", "SMALL": "S", "SM": "S",
    "M": "M", "MEDIUM": "M", "MED": "M",
    "L": "L", "LARGE": "L", "LG": "L",
    "XL": "XL", "XLARGE": "XL", "EXTRALARGE": "XL",
    "XXL": "XXL", "2XL": "XXL", "XXLARGE": "XXL", "2XLARGE": "XXL", "EXTRAEXTRALARGE": "XXL", "DOUBLEXL": "XXL",
}


def normalize_size(size: str) -> str | None:
    key = re.sub(r"[^A-Z0-9]", "", size.upper())
    return SIZE_ALIASES.get(key)


def _status(qty: int) -> str:
    if qty == 0:
        return "sold_out"
    return "low_stock" if qty <= LOW_STOCK_MAX else "in_stock"


def _resolve(product_ref: str) -> sqlite3.Row | ProductNotFound:
    """Find a catalogue row by exact product_id, or by exact (case-insensitive) product name."""
    ref = product_ref.strip()
    with read_conn() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (ref,)).fetchone()
        if row is None:
            row = conn.execute("SELECT * FROM catalogue WHERE lower(name) = lower(?)", (ref,)).fetchone()
    if row is not None:
        return row
    suggestions = search_products(ref.replace("-", " "), limit=3).products
    return ProductNotFound(
        product_ref=ref,
        message=f"No product matches '{ref}'. Use a product_id from search_products (see did_you_mean).",
        did_you_mean=suggestions,
    )


# ---------- lookup tools (Problem 6) ----------


def get_product_description(product_id: str) -> ProductDescription | ProductNotFound:
    """Look up what a product is: its catalogue description, garment type, colours and design tags.

    Use for "what does it look like / what colours / tell me about" questions. Does not include price or stock.

    Args:
        product_id: product_id from search_products (e.g. "basic-hoodie-big-yale"); an exact product name also works.
    """
    row = _resolve(product_id)
    if isinstance(row, ProductNotFound):
        return row
    return ProductDescription(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        tags=json.loads(row["search_tags"]),
    )


def get_price(product_ids: list[str]) -> PriceLookup:
    """Look up the current price of one or more products from the catalogue.

    ALWAYS call this before stating or comparing prices. Quote price_display exactly.

    Args:
        product_ids: 1-10 product_ids from search_products (exact product names also work).
    """
    quotes, missing = [], []
    for ref in list(dict.fromkeys(product_ids))[:MAX_RESULTS]:
        row = _resolve(ref)
        if isinstance(row, ProductNotFound):
            missing.append(row)
            continue
        quotes.append(
            PriceQuote(
                product_id=row["product_id"],
                name=row["name"],
                price=row["price"],
                price_display=f"${row['price']:,.2f}",
            )
        )
    return PriceLookup(prices=quotes, not_found=missing)


def check_stock(product_id: str, size: str | None = None) -> StockLookup | ProductNotFound:
    """Look up live inventory for a product: units on hand for every size, and whether each is sold out.

    ALWAYS call this before saying whether something is in stock or how many are left.
    Pass `size` when the shopper asks about a specific size.

    Args:
        product_id: product_id from search_products (an exact product name also works).
        size: Optional size the shopper asked about: XS, S, M, L, XL, XXL (also accepts "medium", "2XL", etc.).
    """
    row = _resolve(product_id)
    if isinstance(row, ProductNotFound):
        return row
    pid = row["product_id"]
    with read_conn() as conn:
        sizes = _inventory(conn, [pid])[pid]
    availability = [SizeAvailability(size=s.size, quantity=s.quantity, status=_status(s.quantity)) for s in sizes]

    requested = requested_status = requested_qty = None
    if size:
        requested = normalize_size(size)
        match = next((a for a in availability if a.size == requested), None)
        if match is None:
            requested, requested_status = size.strip(), "not_a_size"
        else:
            requested_status, requested_qty = match.status, match.quantity

    return StockLookup(
        product_id=pid,
        name=row["name"],
        requested_size=requested,
        requested_size_status=requested_status,
        requested_size_quantity=requested_qty,
        sizes=availability,
        sizes_in_stock=[a.size for a in availability if a.quantity > 0],
        sold_out_sizes=[a.size for a in availability if a.quantity == 0],
        total_units=sum(a.quantity for a in availability),
        checked_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


# ---------- alternatives tool (Problem 9) ----------

GENERIC_TAG_MIN = 8  # tags on 8+ products ("Yale", "crewneck", "navy sweatshirt"...) don't identify a design
RESIDENTIAL_COLLEGES = [
    "benjamin franklin", "berkeley", "branford", "davenport", "ezra stiles", "grace hopper", "jonathan edwards",
    "morse", "pauli murray", "pierson", "saybrook", "silliman", "timothy dwight", "trumbull",
]


def _theme(row: sqlite3.Row) -> str | None:
    """Broad design family, so e.g. one residential-college crewneck can stand in for another."""
    text = (row["name"] + " " + row["search_tags"]).lower()
    if any(c in text for c in RESIDENTIAL_COLLEGES):
        return "residential college"
    if "school of" in text or "school" in row["name"].lower():
        return "graduate/professional school"
    return None


def _generic_tags(rows: list[sqlite3.Row]) -> set[str]:
    counts: dict[str, int] = {}
    for r in rows:
        for t in {t.lower() for t in json.loads(r["search_tags"])}:
            counts[t] = counts.get(t, 0) + 1
    return {t for t, n in counts.items() if n >= GENERIC_TAG_MIN}


def find_alternatives(
    product_id: str, size: str | None = None, max_price: float | None = None, limit: int = 6
) -> AlternativesResult | ProductNotFound:
    """Find similar products that ARE in stock, to suggest when an item or the shopper's size is sold out.

    Call this whenever check_stock shows the shopper's size (or the whole product) is sold out, or when the
    shopper asks for "something similar", "other options" or "what else is like this".
    Similarity: same category, same college / sport / design tags, shared colours, close price.

    Args:
        product_id: The product to find alternatives for (product_id or exact name).
        size: The shopper's size (XS, S, M, L, XL, XXL; "medium" etc. accepted). Only items in stock in it are returned.
        max_price: Optional budget in USD.
        limit: Maximum alternatives (1-10).
    """
    base = _resolve(product_id)
    if isinstance(base, ProductNotFound):
        return base
    limit = max(1, min(limit, 10))
    wanted = normalize_size(size) if size else None
    rows = _all_rows()
    generic = _generic_tags(rows)
    with read_conn() as conn:
        inv = _inventory(conn, [r["product_id"] for r in rows])

    base_id, base_cat = base["product_id"], category_of(base["garment_type"])
    base_tags = {t.lower() for t in json.loads(base["search_tags"])} - generic
    base_colors = {c.lower() for c in json.loads(base["colors"])}
    base_theme = _theme(base)
    base_stock = {s.size: s.quantity for s in inv[base_id]}
    base_qty = base_stock.get(wanted, 0) if wanted else sum(base_stock.values())

    scored = []
    for r in rows:
        pid = r["product_id"]
        if pid == base_id or (max_price is not None and r["price"] > max_price):
            continue
        stock = {s.size: s.quantity for s in inv[pid]}
        if (wanted and stock.get(wanted, 0) == 0) or sum(stock.values()) == 0:
            continue
        reasons, score = [], 0
        cat = category_of(r["garment_type"])
        if cat == base_cat:
            score += 5
            reasons.append(f"same category ({cat})")
        shared_tags = base_tags & {t.lower() for t in json.loads(r["search_tags"])}
        if shared_tags:
            score += 3 * min(len(shared_tags), 2)
            reasons.append("also " + ", ".join(sorted(shared_tags)[:2]))
        if base_theme and _theme(r) == base_theme:
            score += 2
            reasons.append(f"also a {base_theme} design")
        shared_colors = base_colors & {c.lower() for c in json.loads(r["colors"])}
        if shared_colors:
            score += 1
            reasons.append("shares colour " + ", ".join(sorted(shared_colors)[:2]))
        if abs(r["price"] - base["price"]) <= 10:
            score += 1
            reasons.append("similar price")
        if cat != base_cat and not shared_tags and not (base_theme and _theme(r) == base_theme):
            continue  # must be the same kind of item, or the same college/sport/design family
        scored.append((score, r, stock, reasons))

    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    alternatives = [
        AlternativeHit(
            product_id=r["product_id"],
            name=r["name"],
            category=category_of(r["garment_type"]),
            price=r["price"],
            price_display=f"${r['price']:,.2f}",
            colors=json.loads(r["colors"]),
            requested_size_quantity=stock.get(wanted) if wanted else None,
            sizes_in_stock=[sz for sz in SIZE_ORDER if stock.get(sz, 0) > 0],
            match_reasons=reasons,
        )
        for _, r, stock, reasons in scored[:limit]
    ]
    return AlternativesResult(
        for_product_id=base_id,
        for_product_name=base["name"],
        requested_size=wanted,
        original_status=_status(base_qty),
        alternatives=alternatives,
        note=(
            "All alternatives are in stock"
            + (f" in size {wanted}" if wanted else "")
            + ". Best matches first."
            if alternatives
            else "No similar in-stock items found; try search_products with broader keywords."
        ),
    )


# ---------- context tools (Problem 8): who is chatting, what page they're on ----------


def get_my_account(ctx: RunContext[ChatDeps]) -> CustomerProfile:
    """Get the logged-in shopper's own account details (name, email, member since, saved chat count).

    Use when the shopper asks about their account ("what email am I using?", "do you know who I am?").
    Returns logged_in=false for guests. Never reveals any other customer's information.
    """
    customer = ctx.deps.customer
    if customer is None:
        return CustomerProfile(
            logged_in=False,
            message="The shopper is a guest. They can log in or create an account to save their chat history.",
        )
    with read_conn() as conn:
        saved = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (customer.user_id,)
        ).fetchone()[0]
    return CustomerProfile(
        logged_in=True,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        member_since=customer.member_since,
        saved_chat_messages=saved,
        message="Account details for the logged-in shopper only. Their chat history is saved to their account.",
    )


def get_current_page(ctx: RunContext[ChatDeps]) -> CurrentPageInfo:
    """Get the page the shopper is looking at right now, including the product on screen.

    Use when the shopper says "this", "it", "this one" or "here" without naming a product: on a product
    page, viewing_product is the item they mean. Then use check_stock / get_price on its product_id.
    """
    page, viewing = ctx.deps.page, None
    if ctx.deps.viewed_product:
        found = get_product_description(ctx.deps.viewed_product.product_id)
        viewing = found if isinstance(found, ProductDescription) else None
    return CurrentPageInfo(
        path=page.path,
        page_type=page.page_type,
        viewing_product=viewing,
        search_query=page.search_query,
        chat_results_title=page.chat_results_title,
    )

