# Backend Scripts

This directory contains utility scripts for the InterviewPrep-App backend.

## Migration Scripts

### `init_migrations.py`

Initializes Alembic migrations for the project.

**Usage:**
```bash
cd backend
python scripts/init_migrations.py
```

**What it does:**
1. Checks database connectivity
2. Verifies Alembic installation
3. Creates initial migration from current models
4. Optionally applies the migration
5. Verifies the setup

**Prerequisites:**
- PostgreSQL running (via `docker-compose up -d`)
- `.env` file with `DATABASE_URL` configured
- Alembic installed (`pip install alembic>=1.18.0`)

## Other Scripts

### `seed.py` (in `backend/`)

Seeds questions from `data/questions` and can reset tables.

**Usage:**
```bash
cd backend
python seed.py                     # Migrate + upsert questions
python seed.py --questions          # Upsert questions only
python seed.py --questions --no-upsert  # Insert-only
python seed.py --reset              # Wipe all tables
```

Additional utility scripts can be added here for:
- Database seeding
- Data migrations
- Backup/restore operations
- Testing utilities
- Development helpers
