# Alembic Quick Start Guide

## First Time Setup

### 1. Ensure Database is Running
```bash
docker-compose up -d
```

### 2. Install Dependencies (if not already done)
```bash
cd backend
pip install -r requirements.txt
```

### 3. Initialize Migrations (Automated)
```bash
cd backend
python scripts/init_migrations.py
```

This script will:
- ✅ Check database connection
- ✅ Verify Alembic installation
- ✅ Create initial migration
- ✅ Optionally apply the migration
- ✅ Verify the setup

### 4. Manual Initialization (Alternative)
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

### Making Schema Changes

1. **Modify your models** in `app/models/`
   ```python
   # Example: Add a new column
   class User(Base):
       __tablename__ = "users"
       # ... existing columns ...
       new_field = Column(String(100), nullable=True)
   ```

2. **Generate migration**
   ```bash
   cd backend
   alembic revision --autogenerate -m "add new_field to users"
   ```

3. **Review the migration** in `alembic/versions/`
   - Check the upgrade() function
   - Check the downgrade() function
   - Edit if needed (Alembic doesn't catch everything)

4. **Test the migration**
   ```bash
   # Apply
   alembic upgrade head
   
   # Test rollback
   alembic downgrade -1
   
   # Re-apply
   alembic upgrade head
   ```

5. **Commit to git**
   ```bash
   git add alembic/versions/*.py
   git commit -m "Add new_field to users table"
   ```

## Common Commands

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Create empty migration (for data changes)
alembic revision -m "seed default data"
```

## Troubleshooting

### "Can't locate revision"
```bash
# Check if migration files exist
ls alembic/versions/

# If missing, restore from git or regenerate
```

### "Target database is not up to date"
```bash
# Check current state
alembic current

# If migrations were applied manually, stamp the database
alembic stamp head
```

### "No changes detected"
```bash
# Ensure models are imported in alembic/env.py
# Check that your model changes are saved
# Try: alembic revision --autogenerate -m "test" --verbose
```

## Best Practices

✅ **DO:**
- Review generated migrations before applying
- Test rollbacks before committing
- Keep migrations small and focused
- Use descriptive migration messages
- Commit migration files to git

❌ **DON'T:**
- Edit already-applied migrations
- Skip reviewing auto-generated migrations
- Apply untested migrations to production
- Delete migration files
- Manually modify the database schema

## Next Steps

- Read the full guide: `MIGRATIONS.md`
- Understand the configuration: `alembic.ini` and `alembic/env.py`
- Learn about data migrations and advanced scenarios

## Need Help?

- Full documentation: `backend/MIGRATIONS.md`
- Alembic docs: https://alembic.sqlalchemy.org/
- Project README: `../README