# Campus Customs: Usability & Agent Improvements (Problem 9)

We chose four improvements from a shortlist: **two front-end usability (UX) improvements** and **two agent/backend improvements**. For each one, this file covers **what we added**, **why it helps** a Campus Customs shopper or the business, and **how we confirmed it in the running app** (React front end on :5173, FastAPI + PydanticAI backend on :8000).

| # | Type | Improvement | Status |
|---|---|---|---|
| 1 | Front end | Filter & sort on the Products page (plus "Shop by category" on Home) | ✅ Built and verified in the app |
| 2 | Front end | Chat quick-starts + "Ask our assistant about this item" | ✅ Built and verified in the app |
| 3 | Agent / backend | In-stock alternatives tool, `find_alternatives` | ✅ Built and verified in the app |
| 4 | Agent / backend | Input safety guardrails (sensitive-data screen + chat rate limit) | ✅ Built and verified in the app |

*Options we considered but didn't pick: stock badges on product cards, "You may also like" on product pages, a stock-claim checker in the output validator, and catalogue caching / token-budget trimming for speed and cost.*

---

## 1. Filter & sort on the Products page *(front end)*

### What we added
- A **filter bar** on `/products`:
  - **Category chips:** All · Hoodies · T-shirts · Crewnecks · Quarter-zips · Jackets · Long sleeve · Mocknecks.
  - **"In stock in [size]"** menu (XS–XXL), which hides items sold out in that size.
  - **Sort menu:** Featured, Price low→high, Price high→low, Name A–Z.
  - **Clear all filters** link.
- Filters combine with the existing search box. The page title and result line update to match (e.g. **"Shop Hoodies"**, *"21 items · Hoodies · in stock in XL"*).
- A friendly **empty state** suggests trying another size or asking the assistant.
- Every filter is stored in the **URL** (e.g. `/products?category=hoodie&size=XL&sort=price_desc`), so Back/Forward, bookmarks and shared links reopen the same view.
- **"Shop by category"** tiles on the Home page link straight into the filtered Products page.
- **Backend:** `GET /api/products` gained `category`, `size` and `sort` parameters (`tools.list_products`). They use the same 7 categories as the agent's search (§7 of the harness), and the size filter reads **live inventory**.
- Files: `frontend/src/pages/Products.tsx`, `frontend/src/catalog.ts`, `frontend/src/pages/Home.tsx`, `frontend/src/api.ts`, `backend/tools.py`, `backend/main.py`, CSS in `index.css`.

### Why it helps
- **Shoppers:** the catalogue has 102 items under 22 inconsistent garment-type labels. Before, the only way to narrow it was keyword search. Now "hoodies in my size, cheapest first" takes **two clicks**.
- **Fewer dead ends:** the size filter uses real stock, so shoppers don't open product pages only to find their size sold out (145 of 612 product-size combinations are out of stock).
- **Parents and gift buyers** can sort by price to stay on budget.
- **Business:** faster discovery means more product-page views and fewer people leaving. Shareable filtered URLs ("all quarter-zips") can be used in emails or social posts.

### Verified in the running app
| Action | Result |
|---|---|
| Home → **Hoodies** tile | Opened `/products?category=hoodie`: "Shop Hoodies", **27 items**, Hoodies chip active |
| "In stock in" → **XL** | **21 items** · in stock in XL (matches the API: 21 of 27 hoodies have XL > 0) |
| Sort → **Price: high to low** | Prices run $88.00 → … → $45.00, confirmed in descending order. URL `?category=hoodie&size=XL&sort=price_desc` |
| Click the first card, then browser **Back** | Product page opened. Back returned to the same filtered view (21 items, same URL) |

---

## 2. Chat quick-starts + "Ask our assistant about this item" *(front end)*

### What we added
- **Quick-start chips** in the chat panel, so shoppers can tap instead of typing:
  - Anywhere (shown while the chat is empty): *What hoodies do you have?* · *Gift ideas under $40* · *Show me residential college gear* · *What's in stock in XL?*
  - On a product page (always shown, labelled "Ask about this item:"): *Is this in stock in M?* · *What colours does this come in?* · *Anything similar in stock?*
- An **"Ask our assistant" box on every product page** with three buttons:
  - **💬 Ask our assistant** opens the chat with *"About the {product name}: "* pre-filled.
  - **Is my size in stock?** opens the chat with *"Is this in stock in my size? I wear "* pre-filled and the cursor ready.
  - **Show similar items** sends the question straight away.
- The input placeholder changes to "Ask about this item…" on product pages.
- **How it works:** a small `ChatUiProvider` context (`chatUi.tsx`) lets any page call `ask(text, send)` to open the chat and send or pre-fill a message. The page context from Problem 8 tells the agent which product "this" means.
- Files: `frontend/src/chatUi.tsx`, `frontend/src/components/ChatWidget.tsx`, `frontend/src/pages/ProductDetail.tsx`, `frontend/src/main.tsx`, CSS in `index.css`.

### Why it helps
- **Shoppers:** many people don't know what a shop chatbot can do, or don't want to type on a phone. Starter questions show what to ask and answer it in one tap.
- **On a product page,** the most common questions (my size? colours? something similar?) are one click away, right next to the size table.
- **Business:** the assistant was hidden behind a small 💬 button. These buttons put it where buying decisions happen, which drives use of the feature that turns "sold out" into a sale (improvement 3). A pre-filled question also means it's about the right product, giving more accurate answers.

### Verified in the running app
| Action | Result |
|---|---|
| Guest on Home, open chat | Header "Guest chat · log in to save your history". 4 general quick-start chips shown |
| Tap **Gift ideas under $40** | Sent immediately. Reply plus **25 cards** on the page ("Yale gifts under $40"). Chips hidden once the conversation started |
| Pierson College Crewneck page | "Ask our assistant" box with 3 buttons. Chat chips labelled "Ask about this item:" |
| Click **Is my size in stock?** (chat was closed) | Chat opened, input pre-filled *"Is this in stock in my size? I wear "*, and the input was focused |
| Type "L" and send | "The Pierson College Crewneck is **sold out in L**. Similar options in your size: Davenport ($58.00, 12 left in L), Saybrook (2 left), Jonathan Edwards (8 left)." 4 cards on the page |

---

## 3. In-stock alternatives tool, `find_alternatives` *(agent / backend)*

### What we added
- A new agent tool in `backend/tools.py`:
  `find_alternatives(product_id, size=None, max_price=None, limit=6) → AlternativesResult`.
- **How it works:**
  1. It reads **live inventory** and keeps only products **in stock in the shopper's size** (or in stock at all), under an optional budget.
  2. It scores each candidate for similarity: same category (+5), shared *distinctive* tags such as a college, sport or "The Game" (+3 each, up to 2), same design family (+2: residential college, or graduate/professional school), a shared colour (+1), and price within $10 (+1).
  3. Tags used by 8 or more products ("Yale", "crewneck", "navy sweatshirt") are ignored as generic.
  4. A candidate must be the same kind of item or share a college/sport/design.
- **Typed result** (`models.py`): `AlternativesResult {for_product_id, for_product_name, requested_size, original_status, alternatives[], note}`. Each `AlternativeHit` includes `price` / `price_display`, `requested_size_quantity`, `sizes_in_stock` and **`match_reasons`** (e.g. `"same category (crewneck)"`, `"also a residential college design"`), so the agent can explain *why* it suggests something.
- **Prompt** (`prompts/prompt.md`): when anything is **sold out**, the agent must say so clearly, then **always call `find_alternatives`**. It offers the top 2–3 with their stock in that size and shows them as cards, original product first, titled e.g. "In stock in L instead". New "Which tool to call" row: *"Sold out / anything similar?" → `find_alternatives`*.
- The price check from Problem 6 still applies: alternatives come with `price` fields, so any price the agent quotes is still verified.

### Why it helps
- **Shoppers:** before, "sold out in L" was a dead end. Now the answer comes with real in-stock options in their size, chosen to match what they wanted. A Pierson student gets other residential-college crewnecks, not a random T-shirt.
- **More accurate than the model guessing:** similarity and stock are computed in code from the database, so the agent can't recommend something that is also sold out.
- **Business:** recovers sales that would otherwise be lost. With 145 sold-out product-size combinations, this happens often.

### Verified in the running app
| Test | Result |
|---|---|
| API: "Is the Pierson College Crewneck available in large?" | "**sold out in L**. In stock in L instead: **Davenport College Crewneck** ($58.00, 12 left), **Saybrook College Crewneck** ($58.00, 2 left), **Jonathan Edwards College Crewneck** ($58.00, 8 left). Still available in XS, S, M, XXL." Cards: Pierson + 3 alternatives, titled "In stock in L instead" |
| Database check | Pierson L = 0. Davenport L = 12, Saybrook L = 2, Jonathan Edwards L = 8 ✅ |
| Browser: product page → "Is my size in stock?" → "L" | Same grounded alternatives, 4 cards on the page (see improvement 2) |
| Direct tool call `find_alternatives('basic-hoodie-big-yale', 'XL', max_price=70)` | Yale Uncle Hoodie (XL 5), The Forest School Hoodie (XL 12), Yale Grandpa Hoodie (XL 2), all ≤ $70 and in stock in XL |

---

## 4. Input safety guardrails *(agent / backend)*

### What we added
A new module, `backend/guardrails.py`, that runs in `/api/chat` **before the model is called**:

1. **Sensitive-data screen:** blocks messages containing:
   - a **payment card number** (13–19 digits, spaces/dashes allowed, **checked with the Luhn algorithm** so order numbers and prices don't trigger it),
   - a **password** ("my password is…", "password: …", "pwd=…"; a harmless "bus pass is expired" is *not* blocked),
   - a **US Social Security number** (`123-45-6789`).

   A blocked message is **never sent to the AI provider, never written to `chat_messages`, and never logged** (the log records only the type, e.g. `Guardrail blocked a message containing card data`). The shopper gets a clear explanation instead, e.g. *"For your security, please don't share card numbers in chat. I can't take payments here…"*. The API returns `blocked: "card" | "password" | "ssn"`, and the chat widget **replaces the shopper's message on screen** with *"🔒 Message hidden…"*, so it isn't re-sent as guest history. Any sensitive data in guest history sent by the browser is also redacted on the server.
2. **Chat rate limit:** at most **10 messages per minute and 100 per hour**, per logged-in account (or per IP for guests). It's checked before any model call. Over the limit, the shopper gets `429` with *"You're sending messages very quickly. Please wait N seconds and try again."*.

Files: `backend/guardrails.py`, `backend/main.py`, `backend/models.py` (`ChatResponse.blocked`), `frontend/src/components/ChatWidget.tsx`, `frontend/src/api.ts`.

### Why it helps
- **Shoppers:** people do paste card details or passwords into support chats ("can I just pay here?"). This protects them: the data never leaves our server, isn't stored in their saved chat history, and they're told why.
- **Business:**
  - Keeps card data out of chat logs and away from a third-party AI provider, which matters for payment-card security rules and privacy law.
  - Prevents password exposure.
  - The rate limit stops scripted abuse and **runaway AI costs**, since every message is a paid model call.
  - Blocked messages cost nothing (0.0s, no model call).
- **Safer agent:** these checks run in code, so they work even if a prompt tricks the model.

### Verified in the running app
| Test | Result |
|---|---|
| Logged in as Grace: "Can I just pay here? my card is 4111 1111 1111 1111 exp 12/27" | `blocked: "card"`, reply in **0.0s** (no model call), `saved: false` |
| "my password is Cobol1959! can you check my account" | `blocked: "password"`, not saved |
| "my bus pass is expired, any gifts for a commuter?" | **Not** blocked, normal answer with 4 cards, saved |
| Grace's saved history afterwards | Grew by **2 messages** (only the bus-pass turn). The card and password messages weren't stored |
| Database file / server log searched for "4111" | **0 matches** in both. The log shows only "Guardrail blocked a message containing card data (ip:127.0.0.1)" |
| 12 rapid messages from one guest IP | Responses 1–10: `200`. 11–12: **`429`**, "Please wait 60 seconds and try again." |
| Browser (guest): send a card number in the chat | Shopper's bubble replaced with "🔒 Message hidden: it looked like it contained private information, so it was not sent or saved." The safety reply was shown, and **"4111" appears nowhere on the page** |

---

### Data note found while testing
The provided catalogue row for **Benjamin Franklin T Shirt** has a placeholder description ("Campus Customs product photo… Vision blocked; filename-based stub."), visible on its product card. This is a problem in the source data, not the app. It should be fixed in `campus_customs.db` by the content owner.
