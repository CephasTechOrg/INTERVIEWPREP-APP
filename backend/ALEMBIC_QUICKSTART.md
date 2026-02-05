# Alembic Quick Start Guide

## First-Time Setup

### 1. Ensure database is running

```bash
docker-compose up -d
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Initialize migrations (automated)

```bash
cd backend
python scripts/init_migrations.py
```

This helper script checks DB connectivity, verifies Alembic, creates the initial migration (if needed), and can apply it.

### 4. Manual initialization (alternative)

```bash
cd backend

# Create initial migration
alembic revision --autogenerate -m "initial schema"

# Review the generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Verify
alembic current
```

## Daily Workflow

1. Modify SQLAlchemy models in `app/models/`.
2. Generate migration:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

3. Review generated `upgrade()` and `downgrade()` in `alembic/versions/`.
4. Test upgrade and rollback:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

5. Commit migration file(s) with related model changes.

## Common Commands

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision_id>

# Create empty migration (e.g. data migration)
alembic revision -m "seed default data"
```

## Troubleshooting

### "Can't locate revision"

```bash
ls alembic/versions/
```

If files are missing, restore from git.

### "Target database is not up to date"

```bash
alembic current
alembic upgrade head
```

If schema was modified manually and you need to align revision markers:

```bash
alembic stamp head
```

### "No changes detected"

- Ensure your model edits are saved.
- Ensure models are imported by `backend/alembic/env.py`.
- Retry with:

```bash
alembic revision --autogenerate -m "test" --verbose
```

## Best Practices

Do:
- Review generated migrations before applying.
- Test both upgrade and downgrade locally.
- Keep migrations small and focused.
- Use descriptive migration messages.
- Commit migration files to git.

Do not:
- Edit already-applied migrations.
- Skip migration review.
- Apply untested migrations to production.
- Delete committed migration files.
- Modify schema manually without migration tracking.

## More Documentation

- Full migration guide: `backend/MIGRATIONS.md`
- Alembic docs: https://alembic.sqlalchemy.org/
- Project setup: `README.md`
