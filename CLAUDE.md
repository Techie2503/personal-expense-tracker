# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Expense Tracker PWA: multi-user, Google OAuth login, FastAPI backend + vanilla JS frontend, with Google Sheets (in each user's own Drive) as the actual persistence layer.

## Commands

- **Run locally**: `chmod +x run_local.sh && ./run_local.sh` — creates a venv, installs `requirements.txt`, loads `.env`, then runs `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --reload` (default port 8000).
- **Manual run**:
  ```bash
  python3 -m venv venv && source venv/bin/activate
  pip install -r requirements.txt
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **App URLs**: `http://localhost:8000/` (Google login) → redirects to `/app` (main SPA) after sign-in. API docs (Swagger) at `/docs`. Health check: `curl http://localhost:8000/api/health`.
- **Seed default categories**: `python -m backend.seed` (there is no `/api/seed` HTTP endpoint despite README/QUICKSTART referencing one — that's stale docs).
- **No test suite and no linter/formatter** are configured in this repo.
- **Required env vars** (`.env` at repo root, gitignored — there is no `.env.example` despite it being referenced in README): `GOOGLE_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON) or `GOOGLE_SERVICE_ACCOUNT_JSON_KEY` (inline JSON, used on Render), `ENVIRONMENT` (`development`/`production`/`local`), `DATABASE_URL` (default `sqlite:///./expenses.db`), `PORT`.

## Architecture

### Google Sheets is the source of truth; SQLite is a disposable cache

This is the most important thing to understand about this codebase. On every FastAPI startup (`on_startup` in `backend/main.py`), `hydrate_all_users()` (`backend/hydration.py`) **wipes and rebuilds** each user's `Category1`/`Category2`/`Expense`/`IncomeCategory`/`Inflow` rows in SQLite from that user's Google Sheets. This exists because the deployment target (Render free tier) wipes the SQLite file on every redeploy — Sheets is the durable store, not the DB.

Every write endpoint in `backend/main.py` writes to SQLite first, then best-effort mirrors the change to Google Sheets inside a `try/except` — a Sheets failure never breaks the API response. A manual re-hydration can be triggered via `POST /api/sync/hydrate`.

### Backend layout (`backend/`, flat, no subpackages)

- `main.py` — FastAPI app instance, all `/api/*` routes, CORS, and static/frontend file serving.
- `models.py` — SQLModel table models (`User`, `Category1`, `Category2`, `Expense`, `IncomeCategory`, `Inflow`) plus Pydantic request/response schemas.
- `database.py` — engine creation and the `get_session()` FastAPI dependency; reads `DATABASE_URL`.
- `auth.py` — Google ID token verification (`verify_google_token`). When `ENVIRONMENT=local` and no `GOOGLE_CLIENT_ID` is set, it returns a dummy local user instead (dev bypass).
- `google_sheets_service.py` — all `gspread`/Google Drive API logic; the largest backend file.
- `hydration.py` — the Sheets → SQLite rebuild logic described above.
- `user_mapping.py` — a flat-file (`user_sheets_mapping.json`) backup mapping of `user_id` → per-user sheet IDs, separate from the `User` DB table.
- `seed.py` — standalone script (`python -m backend.seed`) that seeds the default two-level category taxonomy.

There are no migrations (no Alembic) — the schema is created via `SQLModel.metadata.create_all()` on startup.

### Dual Google credential model

- A **service account** (`GOOGLE_APPLICATION_CREDENTIALS` locally, or `GOOGLE_SERVICE_ACCOUNT_JSON_KEY` as an inline JSON string in production) performs all ongoing reads/writes to every user's sheets.
- A **user's OAuth access token**, captured at login, is used only once: to create that user's 4 spreadsheets inside their own Google Drive. The service account is then granted `writer` access to those files so it can operate on them afterward.
- Each user gets 4 sheets, created/found by naming convention: `{user_id} - Categories`, `{user_id} - Expenses`, `{user_id} - ExpenseTracker_IncomeCategories`, `{user_id} - ExpenseTracker_Cashflows`.

### Auth model (no cookies or server sessions)

`POST /api/auth/google` verifies the Google ID token and creates/updates the `User` row (provisioning sheets for new users). The frontend then stores the resulting user object — including `user_id` — in `localStorage`, and every subsequent API call passes `user_id` as a **query parameter**; there is no JWT/session-based authorization on protected routes.

### Frontend (`frontend/`, zero build step)

Plain HTML/CSS/vanilla JS PWA, served directly by FastAPI — no npm, no bundler, no framework. `main.py` mounts `frontend/` at `/static`, serves `login.html` at `GET /` (with `{{GOOGLE_CLIENT_ID}}` string-replaced in), and `index.html` at `GET /app`. `app.js` is a single ~1700-line file containing all frontend logic: `API_BASE = window.location.origin + '/api'`, an IndexedDB-backed offline expense queue that syncs on reconnect, Chart.js-based insights (monthly trend, C1 distribution, C2 breakdown), and CSV export (client-side only — no backend endpoint for it).

### Non-obvious bug-fix patterns worth knowing (from git history)

- Google Sheets stores booleans as the literal strings `"TRUE"`/`"FALSE"`; hydration code compares via `str(value).upper() == 'TRUE'` rather than relying on Python truthiness — a past source of bugs.
- Soft-deleting an `Expense` in the linked Google Sheet matches the row by **`date + amount + c2_name + created_at`** (four keys, since duplicate expenses are common) in `mark_expense_deleted` (`google_sheets_service.py`). `Inflow` rows instead carry an explicit `sheet_id` UUID column for exact-match deletes, since that model was added later specifically to avoid this fuzzy-matching problem.

## Sensitive files — never read into context or commit

`service-account.json`, `service-account-new.json`, `.env`, `user_sheets_mapping.json` — all present in the working tree, all gitignored.
