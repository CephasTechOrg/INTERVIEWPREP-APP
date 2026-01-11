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

Additional utility scripts can be added here for:
- Database seeding
- Data migrations
- Backup/restore operations
- Testing utilities
- Development helpers
