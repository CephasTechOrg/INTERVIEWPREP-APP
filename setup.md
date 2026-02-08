# Setup

This project uses Postgres + Alembic for schema, and a Next.js frontend.

## 1) Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 13+

## 2) Create the database

Create a Postgres database (example name: `interviewprep`).

```sql
CREATE DATABASE interviewprep;
```

## 3) Configure backend environment

From `backend/`, create or edit `backend/.env`:

```
# Required
ENV=dev
SECRET_KEY=your_secret
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@localhost:5432/interviewprep

# Optional but recommended
DEEPSEEK_API_KEY=...
SENDGRID_API_KEY=...
FROM_EMAIL=...
```

## 4) Install backend dependencies

```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 5) Run migrations (create tables)

Alembic migrations already exist in `backend/alembic/versions/`.

```bash
cd backend
alembic upgrade head
```

## 6) Seed questions (optional but recommended)

This project includes a seed script that can run migrations and load questions
from `data/questions/`.

```bash
cd backend
python seed.py --questions
```

Default behavior (no flags) runs migrations + question upsert:

```bash
cd backend
python seed.py
```

## 7) Start backend

```bash
cd backend
uvicorn app.main:app --reload
```

## 8) Start frontend (Next.js)

```bash
cd frontend-next
npm install
npm run dev
```

## Troubleshooting

- If migrations fail, verify `DATABASE_URL` and that Postgres is running.
- If you need to reset all tables (destructive):

```bash
cd backend
python seed.py --reset --questions
```

## Notes

- Migrations are managed by Alembic. Do not manually create tables.
- The `seed.py` script upserts questions and can be re-run safely.
