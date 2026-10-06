"""Live-site check for output/app_check.html (Problem 11).

Drives the RUNNING app (frontend http://localhost:5173 + backend :8000) in Microsoft Edge via
Playwright, takes a screenshot for each check into output/app_check_images/, and records the
agent's replies next to the database's real values in output/app_check_images/results.json.

Run from the hw4 folder with both servers running:
    .venv\\Scripts\\python.exe tests\\app_check_screenshots.py
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "app_check_images"
DB = ROOT / "data" / "campus_customs.db"
SITE = "http://localhost:5173"
VIEWPORT = {"width": 1440, "height": 900}

results: dict = {"run_at": datetime.now().isoformat(timespec="seconds"), "checks": {}}


def db(sql: str, *args):
    with sqlite3.connect(DB) as conn:
        return conn.execute(sql, args).fetchall()


def stock(pid: str) -> dict:
    return dict(db("SELECT size, quantity FROM inventory WHERE product_id = ?", pid))


def price(pid: str) -> float:
    return db("SELECT price FROM catalogue WHERE product_id = ?", pid)[0][0]


def new_page(browser) -> Page:
    ctx = browser.new_context(viewport=VIEWPORT, reduced_motion="reduce")  # stable, crisp screenshots
    ctx.add_init_script("sessionStorage.setItem('cc_dan_peeked', '1')")  # skip Dan's one-time peek bubble
    return ctx.new_page()


def open_chat(page: Page) -> None:
    if not page.locator(".chat-panel").count():
        page.click(".chat-launcher")
    page.wait_for_selector(".chat-input input")


def ask(page: Page, text: str) -> str:
    open_chat(page)
    before = page.locator(".chat-turn.assistant").count()
    page.fill(".chat-input input", text)
    page.press(".chat-input input", "Enter")
    page.wait_for_function(
        "n => document.querySelectorAll('.chat-turn.assistant').length > n && !document.querySelector('.typing')",
        arg=before,
        timeout=120_000,
    )
    page.wait_for_timeout(900)  # let cards render
    return page.locator(".chat-turn.assistant .bubble").last.inner_text()


def show_last_exchange(page: Page, nth_from_end: int = 1) -> None:
    """Scroll the chat so the chosen user question sits at the top, with Dan's answer below it."""
    page.evaluate(
        """n => {
            const box = document.querySelector('.chat-messages');
            const turns = [...document.querySelectorAll('.chat-turn.user')];
            const t = turns[turns.length - n];
            if (box && t) box.scrollTop += t.getBoundingClientRect().top - box.getBoundingClientRect().top - 6;
        }""",
        nth_from_end,
    )
    page.wait_for_timeout(300)


def panel(page: Page) -> dict | None:
    if not page.locator(".chat-results h2").count():
        return None
    return {
        "title": page.locator(".chat-results h2").inner_text(),
        "cards": page.locator(".chat-results a.card").evaluate_all("els => els.map(e => e.getAttribute('href'))"),
    }


def shot(page: Page, name: str) -> str:
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path))
    return f"app_check_images/{name}.png"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:  # installed Microsoft Edge (no download needed on Windows) ...
            browser = p.chromium.launch(channel="msedge", headless=True)
        except Exception:  # ... otherwise Playwright's Chromium (`python -m playwright install chromium`)
            browser = p.chromium.launch(headless=True)

        # 1. Chat checks inventory + price (guest, Home page)
        page = new_page(browser)
        page.goto(SITE + "/")
        q = "How much is the Basic Hoodie Big Yale, and how many are left in XL?"
        reply = ask(page, q)
        show_last_exchange(page)
        results["checks"]["inventory"] = {
            "question": q, "reply": reply, "panel": panel(page), "image": shot(page, "inventory"),
            "db": {"price": price("basic-hoodie-big-yale"), "stock": stock("basic-hoodie-big-yale")},
        }
        page.context.close()

        # 2. Category question -> dynamic product cards on the page
        page = new_page(browser)
        page.goto(SITE + "/about")
        q = "What hoodies do you have?"
        reply = ask(page, q)
        page.evaluate("document.querySelector('.chat-results')?.scrollIntoView({block: 'start'})")
        show_last_exchange(page)
        hoodies = [
            r[0] for r in db("SELECT garment_type FROM catalogue") if "hood" in r[0].lower()
        ]
        results["checks"]["category_cards"] = {
            "question": q, "reply": reply, "panel": panel(page), "image": shot(page, "category_cards"),
            "db": {"hoodies_in_catalogue": len(hoodies)},
        }
        # click a chat-added card -> single-item page still works
        page.click(".chat-results a.card >> nth=0")
        page.wait_for_selector(".detail-info h1")
        page.click(".chat-close")  # close the chat so the product details aren't covered
        page.wait_for_timeout(600)
        results["checks"]["category_cards"]["clicked_card"] = {
            "url": page.url, "h1": page.inner_text(".detail-info h1"), "image": shot(page, "category_card_click"),
        }
        page.context.close()

        # 3. Problem 9 usability: filter & sort on the Products page
        page = new_page(browser)
        page.goto(SITE + "/products")
        page.wait_for_selector(".filter-chip")
        page.click(".filter-chip:has-text('Hoodies')")
        page.select_option(".filter-controls select >> nth=0", "XL")
        page.select_option(".filter-controls select >> nth=1", "price_desc")
        page.wait_for_function(
            "document.querySelector('.result-count')?.innerText.includes('Hoodies · in stock in XL')"
        )
        page.wait_for_timeout(800)
        assert "category=hoodie" in page.url and "size=XL" in page.url and "sort=price_desc" in page.url, page.url
        page.hover(".grid a.card >> nth=0")  # show the hover "sizes in stock" strip
        page.wait_for_timeout(400)
        prices = page.locator(".grid .card-price").all_inner_texts()
        xl_hoodies = db(
            """SELECT COUNT(*) FROM catalogue c JOIN inventory i ON i.product_id = c.product_id
               WHERE i.size = 'XL' AND i.quantity > 0 AND lower(c.garment_type) LIKE '%hood%'"""
        )[0][0]
        results["checks"]["filters"] = {
            "url": page.url, "result_count": page.inner_text(".result-count"), "first_prices": prices[:4],
            "last_prices": prices[-2:], "image": shot(page, "filters"), "db": {"hoodies_in_stock_xl": xl_hoodies},
        }
        page.context.close()

        # 4. Sold-out size -> honest "sold out" + in-stock alternatives
        page = new_page(browser)
        page.goto(SITE + "/")
        q = "Is the Pierson College Crewneck available in large?"
        reply = ask(page, q)
        page.evaluate("document.querySelector('.chat-results')?.scrollIntoView({block: 'start'})")
        show_last_exchange(page)
        pan = panel(page)
        alt_ids = [h.split("/")[-1] for h in (pan or {}).get("cards", [])]
        results["checks"]["sold_out"] = {
            "question": q, "reply": reply, "panel": pan, "image": shot(page, "sold_out_alternatives"),
            "db": {pid: stock(pid).get("L") for pid in alt_ids},
        }
        page.context.close()

        # 5. Product-page context: "this"
        page = new_page(browser)
        page.goto(SITE + "/products/basic-hoodie-big-yale")
        page.wait_for_selector(".size-picker")
        q = "do you have this in pink?"
        reply = ask(page, q)
        page.click(".chat-results-actions .btn")  # "Hide" -> panel collapses to a slim bar
        page.evaluate("window.scrollTo(0, 0)")
        show_last_exchange(page)
        results["checks"]["page_context"] = {
            "question": q, "reply": reply, "image": shot(page, "page_context"),
            "db": {"colors": json.loads(db("SELECT colors FROM catalogue WHERE product_id='basic-hoodie-big-yale'")[0][0])},
        }
        page.context.close()

        # 6. Login + saved chat history restored after reload
        page = new_page(browser)
        before_rows = db("SELECT COUNT(*) FROM chat_messages WHERE user_id = 1")[0][0]
        page.goto(SITE + "/login")
        page.fill("input[type=email]", "test@campuscustoms.yale.edu")
        page.fill("input[type=password]", "password")
        page.click("form.auth-card button[type=submit]")
        page.wait_for_selector(".nav-user")
        open_chat(page)
        page.wait_for_function("!document.querySelector('.chat-note')")  # history loaded
        q = "Hi Dan! Do you know who I am? And is the Boola Boola T Shirt in stock in S?"
        reply = ask(page, q)
        page.reload()
        page.wait_for_selector(".nav-user")
        open_chat(page)
        page.wait_for_function(
            "q => [...document.querySelectorAll('.chat-turn.user')].some(t => t.innerText.includes(q))",
            arg="Do you know who I am?",
        )
        page.wait_for_timeout(800)
        show_last_exchange(page)
        after_rows = db("SELECT COUNT(*) FROM chat_messages WHERE user_id = 1")[0][0]
        last_saved = db(
            "SELECT role, substr(content, 1, 120), created_at FROM chat_messages WHERE user_id = 1 ORDER BY id DESC LIMIT 2"
        )
        results["checks"]["saved_history"] = {
            "question": q, "reply": reply, "header": page.inner_text(".chat-ident"),
            "image": shot(page, "saved_history"),
            "db": {"rows_before": before_rows, "rows_after": after_rows, "last_two_rows": last_saved,
                   "boola_S": stock("boola-boola-t-shirt").get("S")},
        }
        page.context.close()

        # 7. Safety: card number blocked + off-topic refusal
        page = new_page(browser)
        page.goto(SITE + "/")
        q1 = "Can I just pay here? My card is 4111 1111 1111 1111 exp 12/27"
        r1 = ask(page, q1)
        show_last_exchange(page)
        card_image = shot(page, "safety_card")
        q2 = "Can you write my economics essay for me?"
        r2 = ask(page, q2)
        show_last_exchange(page)
        results["checks"]["safety"] = {
            "card_question": q1, "card_reply": r1,
            "card_bubble_shown": page.locator(".chat-turn.user .bubble").nth(0).inner_text(),
            "card_visible_on_page": "4111" in page.inner_text("body"),
            "card_image": card_image,
            "offtopic_question": q2, "offtopic_reply": r2, "image": shot(page, "safety_offtopic"),
            "db": {"card_in_db_file": b"4111 1111" in DB.read_bytes() or b"4111111111111111" in DB.read_bytes()},
        }
        page.context.close()
        browser.close()

    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    t = time.time()
    main()
    print(f"done in {time.time() - t:.0f}s")
