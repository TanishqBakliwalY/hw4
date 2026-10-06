# Campus Customs: Yale storefront + "Handsome Dan" shopping agent

Homework 4 for *AI Foundations for Managers*. A Campus Customs (Yale apparel) e-commerce site:

- **Front end:** React + Vite + TypeScript (`frontend/`). Home with "The Game" countdown hero, Products with filters and sort, product pages with a live-stock size picker, About, Log In, Create Account.
- **Back end:** Python FastAPI (`backend/main.py`). Products and images API, accounts (salted PBKDF2 passwords, HttpOnly sessions), chat API.
- **Agent:** a PydanticAI agent, **Handsome Dan**, powered by `gpt-5.6-luna` via Portkey. It answers from the SQLite database (prices, stock by size, descriptions), shows matching products as cards on the page, suggests in-stock alternatives, remembers logged-in shoppers' chats, and follows input and output safety guardrails.

The agent is four files in `backend/`:

| File | Role |
|---|---|
| `backend/prompts/prompt.md` | System prompt: voice, persona, grounding rules, tool guide, safety rules S1–S17 |
| `backend/agent.py` | Agent wiring: Portkey model, prompt + per-request context, tools, output validator, loop limits, audit |
| `backend/tools.py` | Tools the agent can call (read-only database): search, description, price, stock, alternatives, account, current page |
| `backend/models.py` | Pydantic / PydanticAI structured types (tool results, `ChatReply`, API types, `AuditEntry`) |

Full documentation is in **[`output/harness.md`](output/harness.md)**: how it works, models, tools, safety, specs and audit trail. Also see [`output/usability.md`](output/usability.md), [`output/design.md`](output/design.md), [`output/app_check.html`](output/app_check.html) (live-app screenshots; open locally) and [`output/audit_trail.json`](output/audit_trail.json).

---

## 1. Requirements

- **Python 3.11+** (developed on 3.14)
- **Node.js 20+** and npm (developed on Node 24)
- A **Portkey API key** with access to OpenAI `gpt-5.6-luna`
- The **data pack** (not in this repo): `campus_customs.db` and the `products/` image folder

## 2. Place the data pack

The database and product images are **not committed** (see `.gitignore`). Put them here:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/            # images referenced by the catalogue (e.g. basic-hoodie-big-yale.jpg)
```

The backend adds what it needs on first start (a `sessions` table for logins and an index on `chat_messages`). Existing data is not changed.

## 3. Add your API key

```bash
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY=...`. **Never commit `.env`**; it is git-ignored.

## 4. Run the back end (FastAPI + agent), port 8000

From the `hw4/` folder, create a virtual environment and install packages (first time only):

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

Then start the API **from the `backend/` folder**:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Check it works: <http://127.0.0.1:8000/api/health> should return `{"status":"ok","model":"gpt-5.6-luna"}`.

## 5. Run the front end (React), port 5173

In a **second terminal**, from `hw4/frontend`:

```bash
cd frontend
npm install        # first time only
npm run dev
```

Open **<http://localhost:5173>**. The Vite dev server forwards `/api` and `/images` to the backend on port 8000, so both must be running.

## 6. Try it

- Browse **Products**: filter by category, "In stock in" size and sort. Click any card for its product page.
- Click **Handsome Dan** (bottom-right) and ask, for example:
  - "What hoodies do you have?" → cards appear on the page
  - "How much is the Basic Hoodie Big Yale, and how many are left in XL?"
  - "Is the Pierson College Crewneck available in large?" → sold out, plus in-stock alternatives
  - On a product page: "do you have this in pink?"
- **Log in** with the data pack's test account `test@campuscustoms.yale.edu` / `password`, or **Create Account**. Logged-in chats are saved and reload when you come back.
- The agent's activity is appended to `output/audit_trail.json`.

## 7. Optional checks

```bash
cd frontend && npm run build          # type-check + production build
```

Live end-to-end screenshot check (both servers running; uses installed Edge, or Playwright's Chromium):

```bash
python -m playwright install chromium   # only needed if Microsoft Edge isn't installed
python tests/app_check_screenshots.py   # from hw4/; writes output/app_check_images/
```

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| Chat says the assistant isn't configured (503) | `PORTKEY_API_KEY` is missing from `hw4/.env`. Restart the backend after adding it. |
| Products don't load / "Is the backend running on port 8000?" | Start the backend from `backend/` and check `data/campus_customs.db` exists. |
| Images missing | Put the images in `data/products/`. |
| "You're sending messages very quickly" | Chat is rate-limited to 10 messages per minute per user/IP. Wait a minute. |
| Backend changes not picked up on Windows | `--reload` occasionally hangs. Stop it with Ctrl+C and start it again. |

## Repository layout

```
hw4/
├── AI_prompts.md          # log of the prompts used to build this, problem by problem
├── requirements.txt       # Python packages
├── .env.example           # placeholder config; copy to .env
├── .gitignore             # keeps .env, data/, .venv/, node_modules/ out of git
├── README.md
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app; run with: uvicorn main:app --reload --port 8000
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   ├── prompts/
│   │   └── prompt.md
│   └── auth.py · security.py · db.py · chat_history.py · guardrails.py · audit.py   # web app around the agent
├── tests/
│   └── app_check_screenshots.py
└── output/
    ├── harness.md
    ├── design.md
    ├── usability.md
    ├── app_check.html
    ├── app_check_images/  # screenshots linked from app_check.html
    └── audit_trail.json
```

Local only (not in git): `data/` (data pack), `.env` (real key), `.venv/`, `frontend/node_modules/`.
