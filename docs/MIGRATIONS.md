# Database Migrations (Alembic)

This project uses Alembic for versioned schema changes.

## Current Migration Chain

Migration files live in `backend/alembic/versions/`:

- `9f4a0b4b7a1a_initial_schema.py`
- `6b1c4df2c3e8_add_user_profile_fields.py`
- `a8c3e5f7b9d1_add_rag_and_feedback_tables.py`
- `5d8533fcfb18_add_chat_threads_table.py`

`5d8533fcfb18` is the current `head`.

## Quick Start

Run from `backend/`:

```bash
alembic upgrade head
```

That is enough for most local/dev setups if migrations already exist.

## First-Time Setup

If this is a fresh clone and DB:

1. Start Postgres (for example with `docker-compose up -d` from repo root).
2. Ensure `backend/.env` has `DATABASE_URL` and `SECRET_KEY`.
3. Apply migrations:

```bash
cd backend
alembic upgrade head
```

Optional helper:

```bash
python scripts/init_migrations.py
```

Use this mainly for guided checks; it is interactive.

## Day-to-Day Workflow

After SQLAlchemy model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Then validate:

```bash
alembic current
alembic history
```

## Rollback

```bash
cd backend
alembic downgrade -1
```

Or rollback to specific revision:

```bash
alembic downgrade <revision_id>
```

## Seeding vs Migrations

- Migrations manage schema.
- `seed.py` manages question/data sync.

Common sequence:

```bash
cd backend
alembic upgrade head
python seed.py --questions
```

## Troubleshooting

### `Can't locate revision`

- Check files in `backend/alembic/versions/`.
- Confirm `alembic current` and `alembic history`.

### `Target database is not up to date`

Usually means DB revision and migration files diverged.

```bash
alembic current
alembic upgrade head
```

If you manually altered schema and need to align revision marker:

```bash
alembic stamp head
```

### `No changes detected` during autogenerate

- Confirm your model edits are saved.
- Confirm models are imported by `backend/alembic/env.py`.

## Best Practices

- Keep each migration focused and small.
- Review autogen output before applying.
- Test both upgrade and downgrade locally.
- Do not edit already-applied migrations.
- Commit migration files with model changes.
