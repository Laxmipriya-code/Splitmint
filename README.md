# SplitMint

SplitMint is a production-style expense splitting and balance management app with a thin React client, a FastAPI backend, PostgreSQL persistence, and an optional LangChain-powered assistant called MintSense.

## What’s included

- React frontend with React Router, React Query, and validated forms
- FastAPI backend with service/repository separation
- PostgreSQL-ready SQLAlchemy models and Alembic migrations
- Exact decimal money logic with `ROUND_HALF_UP`
- Equal, custom, and percentage split normalization
- Deterministic balance and settlement engine
- Group and participant lifecycle rules, including inactive historical participants
- Search and filter APIs for expense history
- LangChain orchestration for safe AI parsing and group summaries
- Backend tests for auth, groups, participants, expenses, rounding, balances, settlements, and AI validation
- Docker, docker compose, environment templates, and CI

## Architecture

### Backend

- `backend/app/api`: HTTP routes only
- `backend/app/services`: ledger logic, auth, groups, expenses, balances, AI orchestration
- `backend/app/db/models`: SQLAlchemy models
- `backend/app/db/repositories`: data access helpers
- `backend/app/schemas`: request and response contracts
- `backend/app/services/ledger.py`: split normalization rules
- `backend/alembic`: migration configuration and revisions

### Frontend

- `frontend/src/app`: route composition
- `frontend/src/lib`: auth/session and API client
- `frontend/src/pages`: page-level screens
- `frontend/src/components`: reusable UI and group workflow components

## Key assumptions

- Each account owns its own groups; groups are not shared across accounts.
- The authenticated user is represented as a participant inside every group.
- Groups support up to 4 active participants total, including the owner.
- Participant names are unique within a group to prevent ledger and AI ambiguity.
- Removing a participant hard-deletes them only when they have no history; otherwise they become inactive.
- AI suggestions never write directly to the database. The frontend only uses them to prefill forms.

## Money and ledger rules

- All persisted money values use `NUMERIC(12,2)` in PostgreSQL.
- Python money math uses `Decimal` and `ROUND_HALF_UP`.
- Equal and percentage splits are normalized so the final owed amounts always sum exactly to the expense total.
- Balances are recomputed from source expenses and splits, not from client-side math.
- Settlement suggestions are generated with a deterministic greedy simplification algorithm.

## Local development

### Prerequisites

- Python 3.12+
- Node 24+
- PostgreSQL 15+ (native local instance on `127.0.0.1:5432`) or a Supabase Postgres project

### 1. Backend setup

```bash
cd backend
python -m pip install -e .[dev]
copy .env.example .env
```

Update `backend/.env` and set all required runtime settings:

- `SPLITMINT_DATABASE_URL`
- `SPLITMINT_JWT_SECRET_KEY`
- `SPLITMINT_FRONTEND_ORIGIN`
- Optional: `SPLITMINT_MIGRATION_DATABASE_URL` (recommended when runtime uses a Supabase pooler URL)

Supabase setup notes:

- Runtime URL can be either direct DB host (`db.<project-ref>.supabase.co:5432`) or pooler host (`*.pooler.supabase.com:6543`).
- This backend auto-adds `sslmode=require` for Supabase hosts when it is missing.
- For Supabase transaction pooler URLs (port `6543`), the backend auto-disables psycopg prepared statements for runtime connections.
- You can override that behavior with `SPLITMINT_DB_DISABLE_PREPARED_STATEMENTS=true|false`.
- If runtime uses a pooler URL, set `SPLITMINT_MIGRATION_DATABASE_URL` to the direct DB URL so Alembic and startup migration checks use a stable migration target.

Run migrations and start the API:

```bash
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Supabase direct/session migration flow:

```bash
cd backend
python -m alembic upgrade head
python scripts/seed_sample_data.py
```

This runs all schema migrations against `SPLITMINT_MIGRATION_DATABASE_URL` when provided, otherwise `SPLITMINT_DATABASE_URL`.

If local data is in a bad state, perform a deterministic full reset:

```bash
cd backend
python scripts/reset_local_db.py
```

`reset_local_db.py` is intended for local databases. It refuses non-local targets unless you explicitly pass `--force-nonlocal`.

### 2. Frontend setup

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

The frontend expects the API at `http://localhost:8000/api/v1` by default.

## Docker

Run the full stack with Docker Compose:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- Postgres: `localhost:5432`

## Tests and verification

### Backend

```bash
cd backend
python -m ruff check alembic app tests
python -m pytest -q
```

The backend suite is PostgreSQL-first and includes real OpenAI integration tests.
Set `SPLITMINT_OPENAI_API_KEY` before running tests; the suite fails if it is missing.
Set `SPLITMINT_TEST_DATABASE_URL` (environment variable or `backend/.env`) to a dedicated PostgreSQL test database.
If you intentionally reuse runtime DB for tests, set `SPLITMINT_ALLOW_SHARED_TEST_DATABASE=true` (tests will truncate data).

### Frontend

```bash
cd frontend
npm run lint
npm run build
npm run test:e2e
```

`npm run test:e2e` runs the Playwright happy-flow smoke suite and expects the backend API to be reachable.

## MintSense

MintSense is optional and safe by default.

- Enable it with `SPLITMINT_AI_ENABLED=true`
- Provide `SPLITMINT_OPENAI_API_KEY`
- Optionally override `SPLITMINT_OPENAI_MODEL`

When AI is disabled, the app falls back to a conservative heuristic parser that still returns structured drafts with explicit confirmation requirements.

## API overview

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET|POST /api/v1/groups`
- `GET|PUT|DELETE /api/v1/groups/{group_id}`
- `POST /api/v1/groups/{group_id}/participants`
- `PUT|DELETE /api/v1/participants/{participant_id}`
- `GET|POST /api/v1/expenses`
- `GET|PUT|DELETE /api/v1/expenses/{expense_id}`
- `GET /api/v1/groups/{group_id}/balances`
- `GET /api/v1/groups/{group_id}/settlements`
- `POST /api/v1/ai/parse-expense`
- `POST /api/v1/ai/groups/{group_id}/summary`
- `GET /metrics`

## Verified in this workspace

- Backend import and lint checks
- Backend tests: `14 passed`
- Frontend lint
- Frontend production build
