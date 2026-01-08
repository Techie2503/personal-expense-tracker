Goal: Produce a complete, runnable GitHub repository for an Expense Tracker app that I can run locally and deploy to Render without manual code edits. The repo must include a Python backend (FastAPI) and a frontend (HTML/CSS/Vanilla JS) implemented as a PWA (installable on phone). The frontend must be served by FastAPI (so one service to run). The app must support offline-first expense entry using IndexedDB and auto-sync queued entries when online. Provide charts (monthly trend, C1 distribution, C2 breakdown) using Chart.js. Provide a "Manage Categories" screen to add/disable C1 and C2. Use SQLite for storage. Include a seed script to pre-populate the canonical C1/C2 taxonomy (the one I provided earlier). Provide a README with exact local run commands and step-by-step Render deploy instructions including attaching a persistent disk and setting DATABASE_URL to `sqlite:////data/expenses.db`. The produced repo should be runnable as-is.

Project constraints and expectations:
- Python 3.10+ compatible.
- Use FastAPI for the backend and SQLModel (or SQLAlchemy+Pydantic) for models. Use simple create_all migrations (no Alembic required).
- The DB file default for local dev: `sqlite:///./expenses.db`. For production on Render the recommended env var will be `sqlite:////data/expenses.db`.
- The backend must serve the frontend static files (so launching the backend serves the site at `/`).
- CORS enabled for development.
- REST API endpoints (full list below).
- The frontend must be a PWA: include `manifest.json`, `service-worker.js` (basic caching + background sync for queued entries), and `indexedDB` code for offline queue and sync.
- Charts implemented with Chart.js (loaded via CDN).
- The app must include a seed endpoint / script to populate the canonical C1 and C2 taxonomy (list provided below).
- Provide a `requirements.txt`, `Procfile` or start command, Dockerfile (optional but include it), `.gitignore` (ignore `expenses.db`), and a `README.md` with all commands and Render steps (including disk attach and env var).
- Make the default port configurable via env var $PORT (used for Render).
- Provide a small `test_seed_and_run.sh` or `run_local.sh` script that: creates a virtualenv, installs requirements, sets DATABASE_URL=sqlite:///./expenses.db, runs the backend with uvicorn (--reload optional) so I can check locally.

Seed C1/C2 taxonomy (create these C1 rows and their C2 subcategories):
C1: Food -> [Eat Outside, Groceries, Office Food, Snacks, Beverages]
C1: Transport -> [Scooty Petrol, Maintenance, Parking, Cab/Auto, Public Transport]
C1: Health & Fitness -> [Gym Membership, Trainer, Protein Powder, Supplements, Skincare, Doctor/Medical]
C1: Education & Career -> [Courses, ChatGPT/AI Tools, Books, Certifications, Workshops]
C1: Home & Living -> [Cooking Supplies, Utilities, Rent, Maintenance, Household Items]
C1: Family & Relationships -> [Parents Support, Medical for Family, Gifts, Festivals, Occasions]
C1: Lifestyle -> [Shopping, Entertainment, Cafes, Hobbies, Self-care]
C1: Subscriptions & Tools -> [Streaming, Cloud Services, Software, Productivity Apps]
C1: Travel -> [Transport, Stay, Food (Travel), Local Travel, Activities]
C1: Miscellaneous -> [One-off Expenses, Unplanned, Unknown]

API endpoints (must implement):
- GET  /api/categories                -> returns list of C1 {id, name, active}
- POST /api/categories               -> create new C1 {name} (return created)
- PUT  /api/categories/{id}          -> update C1 (name, active)
- GET  /api/categories/{c1_id}/c2    -> list C2 for a given C1
- POST /api/categories/{c1_id}/c2    -> create new C2 under C1
- PUT  /api/categories/c2/{id}       -> update C2 (name, active)
- GET  /api/expenses                 -> list expenses, supports optional query params: start_date, end_date, limit, offset
- POST /api/expenses                 -> create expense (payload: date, amount, c1_id, c2_id, payment_mode, notes, person(optional), need_vs_want(optional))
- GET  /api/expenses/{id}            -> get single expense
- DELETE /api/expenses/{id}          -> delete expense (soft delete optional)
- GET  /api/insights/monthly        -> aggregated monthly totals for last 12 months
- GET  /api/insights/c1-distribution-> total per C1 (for pie chart)
- GET  /api/insights/c2-breakdown?c1_id= -> totals per C2 for the given C1
- GET  /api/expenses/top?limit=10    -> top N expenses
- POST /api/seed                      -> seeds the DB with the taxonomy above and a few sample expenses (idempotent)

Backend behavior & extra features:
- Use environment variable DATABASE_URL with sensible default for local dev.
- On server startup, auto-create tables and run seed if DB is empty (or seed only when `/api/seed` is called).
- Serve static files from `frontend/` at root (so visiting `/` loads the PWA).
- Include basic input validation and error responses.
- Provide CORS for local dev.
- Provide logging to stdout.
- Add a small admin-esque endpoint or page for "Manage Categories" frontend that uses the category endpoints.

Frontend features:
- A responsive mobile-first UI (simple, clean) with screens:
  1. Add Expense (single quick form: date prefilled, amount, C1 dropdown -> auto-populate C2 dropdown, payment mode, notes, save button). Takes <10 seconds to add.
  2. Expense List (paginated), with ability to delete and edit an expense.
  3. Charts / Insights screen with:
     - Monthly trend (line) – last 12 months
     - C1 distribution (pie)
     - C2 breakdown (bar) for selected C1
     - Top 10 expenses table
  4. Manage Categories (add C1, add C2 under selected C1, toggle active/disable)
  5. Settings: button to "Sync now" queued offline data
- Use IndexedDB (a small wrapper library code included) to store expenses when offline, queue them, and automatically push them to POST /api/expenses when network is available. Show UI status: "Offline — saved locally" vs "Synced".
- The service worker must cache the app shell and enable the app to be installed. Implement a basic background sync approach (if the browser supports SyncManager) and robust fallback: periodic sync attempt when app loads if network available.
- Use Chart.js for charts (CDN link). Charts should fetch data from the insights endpoints.
- Provide accessible dropdowns for C1->C2 with ability to add a new C2 inline (creates via POST and then selects it).
- Provide small client-side form validation.

Repo structure & scripts:
- `backend/` (FastAPI app)
- `frontend/` (index.html, app.js, styles.css, manifest.json, service-worker.js)
- `requirements.txt`
- `Dockerfile` (optional but included)
- `run_local.sh` (create venv, pip install -r requirements.txt, export DATABASE_URL=sqlite:///./expenses.db, uvicorn backend.main:app --host 0.0.0.0 --port 8000)
- `.gitignore` (ignore `expenses.db`, `venv`, `__pycache__`)
- `README.md` with:
  - Local run steps and how to use the app
  - How to seed DB
  - How to test offline behavior
  - Exact Render deploy steps:
    1. Connect GitHub repo to Render as a Web Service (Python).
    2. Use start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
    3. Build command: `pip install -r requirements.txt`
    4. Attach a persistent disk to the service and set the mount point to `/data`.
    5. Set env var `DATABASE_URL=sqlite:////data/expenses.db`
    6. Set any other environment variables (none required).
    7. After deploy, open the app URL, test `Add to Home Screen`.
  - Note to set Render health check / restart policy if needed.

Extra deliverables:
- A single-file SQLite DB sample `sample_data/expenses_sample.db` optional (not added to git), and instructions how to upload it to Render if I want to pre-populate production DB.
- A short troubleshooting section for common issues (CORS, port, persistent disk path).
- A LICENSE (MIT).
- Make code readable, well-commented (especially IndexedDB and service worker sections) because I may inspect quickly.

Important: The repo must be ready to run and deploy *without me editing code*. If any secrets or env vars are needed, explain them in README and provide defaults so local dev works with no env set. Use sensible defaults.

Deliverable format expected from you (Cursor):
- Create the repository file tree with each file content.
- Ensure all code files are complete and syntactically correct.
- At the end of the output, also print the exact three commands I should run locally in my laptop terminal (after cloning) to check the app quickly:
  1) create venv & install,
  2) set env var and run,
  3) open browser URL (http://localhost:8000).
- Also print the exact Render UI steps again as a brief checklist I can copy to Render deploy screen.

Do not ask me any clarifying questions — just generate the repo as described and include the README and the quick-check commands. Thank you.
