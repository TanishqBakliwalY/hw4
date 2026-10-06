# AI Prompts Log — Homework 4

This file logs the prompts I typed to the AI coding assistant while working on Homework 4, one section per problem, in the order I worked on them. It is a record of my own prompts. It is not the runtime prompt files in `prompts/` that the application scripts read.

---

## Setup (before Problem 1)

**Prompt 1:**
> We will be working in the homework 4. We are going to create a real customer website with a helpful chatbot. We will build a react + vite TS front end anda Python FastAPI backend, and a PydanticAI agent powering the chatbot. The site will use a provided SQLite database containing the product catalogue, inventory by size, and users, along with local product images. The chatbot should eventually be able to answer questions about merchandise and provide accurate product price and inventory information from the database, while also helping surface relevant products on the website. I'll also need to research the existing Campus Customs website at yalebulldogblue.com for its style and product information. There are additional assignment-specific requirements and problems that I'll provide later. For now, treat this only as context and don't start implementing anything until I give you the actual instructions/problems. For AI calls, I should use the provided PORTKEY_API_KEY or another available API key, and if using OpenAI through Portkey, I should use a model from the 5.6 or 6 series, using a stronger model when needed for harder agent tasks.

**Prompt 2:**
> Stick to gpt-5.6 luna mostly, ask me if you think we should switch to another model

**What was lacking after Prompt 1:** Prompt 1 allowed any 5.6- or 6-series model, so Prompt 2 set `gpt-5.6-luna` as the default and asked the assistant to check with me before switching.

**Prompt 3:**
> I have downloaded the data.zip. Unzip it

**Result:** Unzipped `data/` with `campus_customs.db` (tables `catalogue`, `inventory`, `users`, `chat_messages`) and 102 product images in `data/products/`.

---

## Problem 1 — AI Prompts Log

**Prompt 1:**
> For problem 1, we nned to create AI_prompts.md. Keep it updated as we work. This will be a log of what I type to you, and not the runtime files in prompts/ that the scripts will read. In this, keep one section for all problems. Each section must include the problem number and title. Atleast one prompt I typed. If a second prompt was needed, one sentence on what was lacking after the first prompt and evidence that I worked problem by problem

**Result:** Created this file and set up the per-problem structure. The assistant will add a new section for each problem as we work.

---

## Problem 2 — Understanding the Database (start of `output/harness.md`)

**Prompt 1:**
> For problem 2, we have to look at the database, campus_customs.db and understand the fields of each table. The minimum is catalogue, inventory and users. Let me know if you can understand more. Now start the file output/harness.md. Write down each table and its fields, and one short line on why each field matters for the campus customs shop or the chatbot. For more context, I need to build a Campus Customs e-commerce website. Users should be able to browse products, create an account, chat with the agent about Campus Customs merchandise, see relevant products appear on the page based on the conversation, and get accurate answers about product prices and stock. I should use the database as the source of truth for pricing and inventory and make sure the agent does not hallucinate this information. I also need to research yalebulldogblue.com to understand the Campus Customs website, its style, products, and information that should be included in the agent's prompt. We will keep growing this harness file in later problmes (models, tools, safety, specs etc)

**Result:** Profiled the database (schema, row counts, value ranges, out-of-stock counts, JSON formats). Created `output/harness.md`. It documents `catalogue`, `inventory`, `users` and the extra `chat_messages` table, gives a one-line reason each field matters, and lists data observations the agent must follow.

---

## Problem 3 — Scaffold the Website (React + Vite + TS front end, FastAPI product API)

**Prompt 1:**
> For problem 3, scaffold a react + vite + TS frontend for campus customs. Put a nav bar at the top that links to the main pages which are: Home, Products, About Us, Log In, Create Account. Pull campus customs-style wording from yalebulldogblue.com, for Home and About Us, but we have to write these pages in our own voice and not copy the original site text. On the products page show images from the catalogue, use the image paths in the database and basic product info (name, price, short description) Now we need to make each product open a single-item page, (large image on one side, full product text on the other -- description, price, sizes/stock when you have them). Click a card on Products should take the shopper there. Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet. Just a stub will call you backend later will be enough right now. We will need a small api soon to read the db, it is fine to start a simple fast api app in backend/main.py, just to serve products and images, and then gorw it into the agent backend in problem 5.

**Result:**
- Researched yalebulldogblue.com (brand, address, history, returns policy, navigation, navy colour scheme). Wrote original Home and About Us copy based on it.
- Built `frontend/` (React + Vite + TS) with a nav bar, all 5 pages, product cards that link to a two-column product page showing live stock by size, and a stub floating chat panel.
- Built `backend/main.py` (FastAPI, read-only database) to serve products, stock and images.
- Checked in the browser: 102 products load with images, stock on the product page matches the database, and the chat stub replies.
- Added website research and architecture sections to `output/harness.md`.

---

## Problem 4 — Create Account / Log In Flow with Secure Passwords

**Prompt 1:**
> For problem 4, we need to build a normal create-account / login flow. Create account: First Name, Last Name, email password (confirm password is a nice touch). Log In: Email and Password. New accounts go into the users table. We need to make sure that the passwords securely so hackers, both human and AI cannot access them. The seed db already has a test user which we can use while building. Email: test@campuscustoms.yale.edu Password: password. Validate that we can login as that user and that a brand new account that we create is also working. Update output/harness.md wth how the auth works (This should include what we store for a user and how passwords are protected)

**Prompt 2:**
> Is the previous command completed

**What was lacking after Prompt 1:** Prompt 1's requirements were complete, but the session was interrupted partway through, so I checked progress. The assistant confirmed the saved files and then finished the nav bar, testing and documentation.

**Result:**
- Backend: `backend/auth.py` (register, login, logout and `/me` routes, HttpOnly session cookie, brute-force limit), `backend/security.py` (PBKDF2-SHA256 with 600k iterations and a random salt per user, legacy seed-hash support with upgrade on login), `backend/db.py` (read-only vs writable connections, new `sessions` table).
- Front end: `AuthProvider` context, working Log In and Create Account forms (with confirm password), and a nav bar showing "Hi, {name}" and Log Out.
- Verified: the seed test user logs in, new accounts (via API and browser) are created and can log in again, and wrong passwords, duplicate emails, bad input and rate limiting are handled. No plaintext passwords are stored. Also fixed validation errors echoing the submitted password back.
- Added the full auth section (§4) to `output/harness.md`.

---

## Problem 5 — Shop Chatbot: PydanticAI Agent behind FastAPI

**Prompt 1:**
> Now in problem 5, we will build the shop chatbot as a pydantic ai agent behind fast api, plugged into our frontend chat widget. We will put the API app in the backend/main.py. This is file we run with Uvicorn. Keep the agent as these four files next to it (same as how it was done in Homework 3) * backend/prompts/prompt.md: This will be the system prompt. We will grow this same file later) * backend/agent.py - Agent entry/ wiring * backend/tools.py - tools the agent can call * backend/models.py - pydantic / pydanticAI structured types. In main.py, expose a chat route so a message from the website returns a reply from the agent. And whatever else you need for products/auth). Here will will need the AI model api key for the agent. Put campus customs voice and safety basics into prompts/prompt.md. We are going to expand tools and safety later. Also we will start or update types in models.py for chat replies or product cards as needed. Now in output/harness.md, not how the front end talks to fast api and how the agent is loaded (prompt file + model) Now make sure the backend runs from the backend folder like this: uvicorn main:app --reload --port 8000

**Result:**
- Built the four agent files: `prompts/prompt.md` (voice, store facts, grounding rules, safety basics), `agent.py` (Portkey + `gpt-5.6-luna`, prompt re-read each run, tools, `ChatReply` structured output), `tools.py` (`search_products`, `get_product_details`, read-only), `models.py` (product card, tool result, chat request/response and agent output types).
- Added `POST /api/chat` to `main.py` and switched to absolute imports so `uvicorn main:app --reload --port 8000` runs from `backend/`.
- Connected the chat widget: Markdown replies plus clickable product cards built from live database rows.
- Testing found that jailbreak-style messages returned a 502 because Portkey's Azure content filter blocked them. Fixed this so shoppers get a polite refusal. Also tightened the prompt so refusals don't name products that weren't looked up.
- Verified answers against the database (prices and stock by size), off-topic, privacy and injection refusals, the logged-in greeting, and the widget in the browser. Documented it all in `output/harness.md` §5.

**Prompt 2:**
> Is problem 5 done?

**What was lacking after Prompt 1:** Nothing was missing from the requirements. This was a completion check before moving on, and the assistant confirmed each Problem 5 requirement had been met.

---

## Problem 6 — Database Lookup Tools (description, price, stock by size)

**Prompt 1:**
> Now for problem 6, we need to give the agent tools that will look up real information from campus_customs.db. This will include: * Product description * Price * How many are in stock (by size when the customer asks). The agent must use the database, it should not invent prices or quantities. If a stock is out of stack, say so clrealy. Now expand prompts/prompt.md, so that agent knows to call these tools for price and stock questions. Add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for the lookup results and why. Give proper reasoning.

**Result:**
- `tools.py`: replaced the all-in-one `get_product_details` tool with three focused, read-only lookups: `get_product_description`, `get_price` (several products in one call, with an exact `price_display`) and `check_stock` (every size with quantity and an `in_stock` / `low_stock` / `sold_out` status, size normalization, `not_a_size`). Unknown products return `ProductNotFound` with `did_you_mean` suggestions.
- `models.py`: added `ProductDescription`, `PriceQuote` / `PriceLookup`, `SizeAvailability` / `StockLookup`, `ProductNotFound` and `StockStatus`.
- `agent.py`: registered the tools, added an output validator that forces a retry when a reply quotes a `$` price no tool returned, and logged tool calls.
- `prompt.md`: expanded grounding rules, added a "Which tool to call" table and "How to talk about stock" rules (sold out stated clearly).
- Verified 7 live questions against the database, plus a scripted fake model to prove the price check works. Wrote `output/harness.md` §6 explaining each tool and the reasoning behind every result field.

---

## Problem 7 — Chat Search Results as Dynamic Product Cards on the Page

**Prompt 1:**
> For problem 7, we will add a cool feature to this site, whenever a customer asks about a type of item, for example what hoodies do you have, the agent should search the catalougue and the website should dynamicall show those matching items as product cards (image, name, price, short info). This is an api contract, the agent returns stuructured product matches and then the front end renders them on the website. After the dynamic product cards are loaded by the new feature, we need to make sure that the same single item page behaviour we built in problem 3 still works, each product card, including the one the chat put on the page, should still open the detail view, large image and full info whernewver clicked. Update prompts/prompt.md and output/harness.md so it is clear how search results are reaching the page.

**Result:**
- API contract: the agent returns `ChatReply {reply, product_matches: {title, product_ids}}`. The validator checks the IDs came from this turn's tool results. `/api/chat` rebuilds the cards from live database rows and returns `{reply, matches: {title, products: ProductCard[]}}`.
- Added a normalized `category` (7 categories from 22 garment types) and a `category` filter on `search_products` (up to 30 results), so "what hoodies do you have?" returns all 27. Fixed a bug found in testing where keywords inside a category re-ordered results instead of filtering them.
- Front end: `ChatResultsProvider` (persisted in sessionStorage) and `ChatResultsPanel`, which renders the same `ProductCard` as the Products page at the top of every page. It collapses on product pages, the chat shows a "Showing N on the page" chip, and the product page scrolls to the top.
- Verified in the browser: 27 hoodie cards appeared on the About page. Clicking chat-added cards opened the full detail page (data matched the database), and Back, a second card, regular Products page cards, reload persistence, a single-product question, a general question and Clear all worked.
- Updated `prompts/prompt.md` ("Showing products on the page") and `output/harness.md` §7 (data flow diagram, contract table, changes, tests).

---

## Problem 8 — Saved Chat History, Customer Context and Page Context

**Prompt 1:**
> For problem 8, when a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting, (name, email). Put that in agent deps or an equivalent clear pattern, and tools the agent can call. Also pass enough page context that if someon is on a product page and asks sometihng like do you have this in pink the agent knows which item they mean. As an hint I have been told by my instructor, you put the code into the agent context. Guests can still chat, but history only needs to persist for logged in users. Now in the output/harness.md, document how the user chat history is stored, and what customer fields the agent sees, and how the page context is passed.

**Result:**
- History: uses the seed `chat_messages` table (new module `backend/chat_history.py`, plus an index). Each logged-in turn is saved in one transaction. For logged-in shoppers the server loads the last 20 messages from the database as agent memory. Added `GET /api/chat/history` (cards rebuilt live) and `DELETE /api/chat/history` ("New chat"). Guests can chat, but nothing is stored.
- Agent context: `ChatDeps {customer, page, viewed_product}` built server-side from the session cookie and sanitized page data. A dynamic `@agent.instructions` adds a "Current context" block. New context tools `get_my_account` and `get_current_page` read `ctx.deps`.
- Page context: the chat widget sends `{path, page_type, product_id, search_query, chat_results_title}`. The server checks `product_id` against the catalogue and cleans the text fields. "This" on a product page now resolves to the viewed item.
- Prompt: new "Who you're talking to and where they are" section and an updated privacy rule.
- Verified guest and logged-in flows by API and in the browser: saved and reloaded history (including seed rows), a follow-up resolved from database history after a fresh login, "this in pink / large" on a product page, and a fake product ID rejected. Also fixed the results panel expanding on reload over a product page. Documented in `output/harness.md` §8.

---

## Problem 9 — Usability & Agent Improvements (2 front end + 2 agent/backend)

**Prompt 1:**
> For problem 9. now that the core shop works, we need to improve it. We will choose and implement 2 front-end usability imrpovements, and 2 agent/backend imrpovements. Front end improvements should be things that make the site look better and make it easier to use, so think of UX. For agent/backend improvements we will think of things that make the agent output better, more accurate or safer. These can be additional agent tools, or things that make the agent run faster of cheaper. GIve me options for both of these, I will choose from them. Before or as we are building we will write output/usability.md. For each of the improvements we have to say What we added, Why it helps a campus customs shopper or the business. Then we need to make sure all the imrpovements actually show up in the running app.

**Prompt 2 (my choices, from the options the assistant offered):**
> Front end: "Filter & sort Products" and "Chat quick-starts + 'Ask about this'". Agent/backend: "In-stock alternatives tool" and "Input safety guardrails".

**What was lacking after Prompt 1:** Prompt 1 asked for options rather than a final choice, so a second step was needed to pick 2 front-end and 2 agent/backend improvements (Prompt 2).

**Result:**
- Wrote `output/usability.md` before building (what we're adding), then completed it with "why it helps" and in-app verification for each improvement.
- Front end 1: filter bar on Products (category chips, in stock in size, sort, clear, URL-synced, empty state) plus Home "Shop by category" tiles. Backend `/api/products` gained `category`, `size` and `sort`.
- Front end 2: chat quick-start chips (general, plus product-specific on product pages) and an "Ask our assistant" box on product pages (pre-fill or send), using a new `ChatUiProvider` context.
- Agent 1: `find_alternatives` tool (in-stock in size, similarity scoring with match reasons, residential-college matching). The prompt requires it after every "sold out".
- Agent 2: `guardrails.py`, which blocks card numbers (Luhn-checked), passwords and SSNs before the model (never sent, saved or logged; the UI hides the message), redacts guest history, and rate-limits chat to 10 per minute and 100 per hour.
- Verified every improvement in the running app (browser and API), including "Is my size in stock?" → L → sold out plus 3 in-stock residential-college alternatives, card number hidden and absent from the database and logs, and `429` after 10 messages per minute. Flagged a placeholder description in the source data (Benjamin Franklin T Shirt).

---

## Problem 10 — Creative Storefront Design (Handsome Dan theme)

**Prompt 1:**
> For problem 10 , Now we will add creative design to that the site feels like a real Campus Customs storefront, fonts, colour, hierarchy, motion product presentation, chat feel. Will get more points for imaginative and innovative ideas. one idea that I was thinking was, since yale's mascot is the bulldog handsome dan, the chatbot can have the them of handsome dan, with also the picture for the chatbot being like that. This should not however change the agent or chatbot experience too much. Give me other ideas as well, and then we can choose. Post that we will write output/design.md, what we changed and why it should help customers stick around and buy, keep it concrete and short.

**Prompt 2 (my choices, from the options the assistant offered):**
> Storefront: "Collegiate visual system", "'The Game' countdown hero", "Product presentation & motion". Chat theme: "Skin + light persona in replies".

**What was lacking after Prompt 1:** Prompt 1 asked for more ideas before deciding, so a second step was needed to pick which design ideas to build and how far to take the Handsome Dan theme (Prompt 2).

**Result:**
- Collegiate visual system: Graduate varsity display font, Georgia product names, Inter UI text; Yale blue + gold; felt texture; varsity title stripes; felt-pennant category tiles; stitched-patch prices; scrolling store ticker.
- "The Game" hero: live countdown to the 142nd Game (Sat Nov 21, 2026, Fenway Park, checked by web search), a waving YALE pennant, Dan, and "Shop game-day gear" / "Ask Handsome Dan" buttons.
- Product presentation and motion: staggered card reveal, a hover strip showing sizes in stock, live-stock badges, hover-to-zoom on product images, and a size picker with per-size stock that offers "Find me something similar in [size]" when sold out. The backend adds `sizes_in_stock` to cards.
- Handsome Dan: an original SVG bulldog as the launcher (peek animation plus a one-time speech bubble), chat header, reply avatars and paw-print typing. A light persona prompt allows at most one flourish and none in refusals, policy or sold-out answers.
- Fixed issues found while testing: the ticker wrongly said returns were "free", the chat header stacked vertically, "New chat" wrapped, decorative SVGs were read by screen readers, and cards needed a reveal fallback. Respects reduced motion.
- Verified in the browser and wrote `output/design.md` (what changed and why it helps people stay and buy).

---

## Problem 11 — Live App Check (`output/app_check.html`)

**Prompt 1:**
> I now need to test the live site and document it in output/app_check.html. a page which can be just doubleclick open. Here we have include clear screenshots and short captions for: Chat checking the inventory level of an item (honest stock/price from the db), The dynamic search-result cards appearing after a category questions. (eg hoodies), One of the usability features we added in prob 9. Make the html easy to grade, heading after each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png). How do we want to do this, do you want me to give you the screenshots or will you be able to do it? Also apart from this what other things should we check

**Prompt 2 (my choice of extra checks, from the options the assistant offered):**
> Sold-out + alternatives, Product page context: 'this', Login + saved chat history, Safety guardrail + off-topic refusal.

**What was lacking after Prompt 1:** Prompt 1 asked which extra checks to add, so a second step was needed to choose them (Prompt 2).

**Result:**
- The assistant took the screenshots itself with a reproducible Playwright script (`tests/app_check_screenshots.py`, using the installed Edge). It drives the running site, saves PNGs to `output/app_check_images/`, and records each agent reply next to the real database values in `results.json`.
- Built `output/app_check.html` (opens by double-click): a summary table, then 7 checks, each with a heading, screenshot(s) with relative links, a caption, "Proves:" text and database evidence. Required: inventory/price, hoodie category cards (plus clicking a chat-added card), filter & sort. Extras: sold-out + alternatives, "this" on a product page, login + saved history after reload, card-number guardrail + off-topic refusal.
- Bugs found and fixed while testing: fast filter clicks lost the category (the URL was rebuilt from stale state; fixed and stress-tested 5/5), and the product image was pushed 120px down by a Problem 10 CSS rule (fixed). Screenshots were re-taken and reviewed afterwards.

**Prompt 3:**
> one issue  I can see in the html is that the highlighted details like backend port, or model cannot be seen easily, so change that highlighting so that it is  visible

**What was lacking after Prompts 1–2:** the inline code chips (ports, model, file names) inherited white text on a light background in the dark header, so they were nearly invisible. They now use white text with a gold outline in the header and bold navy text everywhere else, checked by rendering the page.

**Prompt 4:**
> Also one more issue that I can see in the application is that the create account text is going a little outside the box it is in. Please fix that and update the screenshots as well for that

**What was lacking after Prompt 3:** the nav "Create Account" pill had no side padding (a generic `.nav-links a { padding: 0.3rem 0 }` rule overrode the button padding), so its label touched and overflowed the pill. Added a `.nav-links a.btn` rule (padding, no-wrap), checked that the label fits (scroll width = client width), re-took all 9 screenshots, and updated the `app_check.html` captions that changed (run time, history row counts, reply wording).

**Prompt 5:**
> can you run the app for me as well

**Result:** checked that both servers were running (backend health check `ok`, model `gpt-5.6-luna`; frontend `200`), opened the Home page in the preview, and gave the commands to run it myself.

**Prompt 6:**
> one issue in create account is this. The bar is going outside the box

**What was lacking after Prompt 5:** on Create Account, the First/Last name row used `1fr 1fr` grid columns, and text inputs have a built-in minimum width, so the Last name field overflowed the card. Changed to `minmax(0, 1fr)` columns with full-width inputs (single column under 420px). Verified that all 5 inputs stay inside the card at 1440, 768 and 375px widths.

---

## Problem 12 — Audit Trail, Safety Rules & Finished Harness

**Prompt 1:**
> For problem 12, now we need to keep an append only output/audit_trail.json of agent loop activity (time, tool name, short args/result, stop reason). Do not wipe it betweeen runs, Also think of some safety rules to give the agent and put them in prompts/prompt.md. Finish output/harness.md, so it is clear how the system works. * Model fields in models.py and why we chose them. * Tools and abilities * Safety rules * Specs (loop limits, result caps, models, how to run front + back)

**Result:**
- **Audit trail:** new `backend/audit.py` and `AuditEntry` / `StopReason` in `models.py`. `run_chat` uses `capture_run_messages()` to append one entry per tool call, validator retry and final step, with time, run_id, actor (no PII), page, request, tool name, short args/result, stop reason, duration and tokens. It's append-only: lock, read, append, atomic replace, and an unreadable file is renamed rather than deleted. Emails are masked and blocked messages redacted. Rate-limited and guardrail-blocked requests are audited too.
- **Loop limits:** `UsageLimits(request_limit=8, tool_calls_limit=12, total_tokens_limit=120_000)` plus 2 output retries, with a friendly reply when a limit is hit.
- **Safety rules:** 17 numbered rules (S1–S17) in four groups in `prompts/prompt.md`: truthful selling (no invented fit advice, no false urgency or promises), privacy & security, instructions & injection, scope & conduct (including a distress/self-harm response).
- **Verified live and recorded in the trail:** sold-out + alternatives, "runs small?" (no invented fit), hold + discount code (declined), distress message (988 / counseling), a fake "SYSTEM NOTE" injection (ignored, real price), card number (blocked and redacted), jailbreak (`content_filter`), 11 rapid messages (`rate_limited`), and a scripted runaway model stopped at 8 requests (`usage_limit`). All 6 stop reasons are present, and entries survived a backend restart. The trail also caught a real bug in the first version of the audit code (`result.usage` is a property), which was fixed.
- **Finished `output/harness.md`:** a new §0 one-page system overview with diagram, turn walkthrough and contents; §11 models and why each field was chosen; §12 tools and abilities; §13 safety layers, rules and verification; §14 specs (models, loop limits, result/input caps, how to run front + back, layout); §15 audit trail.

---

## Problem 13 — Publish as a Public GitHub Repo (`hw4/`)

**Prompt 1:**
> For the last problem, problem 13, I now need to put the code in a folder named hw4, and push it to a public github repository. I need to finally be able to submit the repo url, a link graders can open and clone. Do not put the real .env, campus customs.db or product images in the github repo. Use .gitignore. Include .env.example with placeholders only. I have attached the screenshot of the expected file layout. The agent itself is four files under backend/ : prompts/prompt.md, agent.py, tools.py, and models.py. README.md should explain how to run the front and back end after placing the datapack. For pushing it to a public github repo what needs to be done from my end.

**Result:**
- Moved the project into `Homework 4/hw4/`, matching the expected layout. The data pack sits in `hw4/data/` locally and is git-ignored. Recreated `.venv` from `requirements.txt` (with Playwright noted as test-only) and repointed the dev servers. Verified that health, products, images, a grounded chat answer and audit-trail appends all work from the new folder.
- Added a stricter `.gitignore` (`.env`/`.env.*` except `.env.example`, `data/`, `*.db`, `.venv/`, `node_modules/`, `dist/`, audit temp files), `.env.example` (placeholders only) and `README.md` (place the data pack, set the key, run back end + front end, try-it guide, troubleshooting, layout). `.env` loading is now `hw4/.env` first, with the nearest parent `.env` as a fallback.
- Updated harness paths and layout. Removed the Vite boilerplate `frontend/README.md`. The screenshot test falls back to Playwright Chromium when Edge isn't installed.
- `git init`, staged 66 files, and confirmed no `.env`, database, images, `.venv` or `node_modules` are tracked. A secret scan of every tracked file against the real `.env` values found no API keys (the only match was the public `yale.edu` domain in the test email).
- What I need to do: create an empty public GitHub repo and share its URL, then approve the push (Git Credential Manager sign-in).

---
