# Database Migrations Guide

This guide explains how to use Alembic for database migrations in the InterviewPrep-App project.

## Prerequisites

1. Ensure PostgreSQL is running via Docker:
   ```bash
   docker-compose up -d
   ```

2. Ensure you have a `.env` file in the `backend/` directory with `DATABASE_URL` set:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/interviewprep
   ```

## Alembic Configuration

The project is now configured with Alembic:
- `alembic.ini` - Main configuration file
- `alembic/env.py` - Environment configuration (imports all models)
- `alembic/versions/` - Directory for migration files

## Common Commands

### 1. Generate Initial Migration

From the `backend/` directory:

```bash
# Windows PowerShell
cd backend
alembic revision --autogenerate -m "initial schema"

# Linux/Mac
cd backend
alembic revision --autogenerate -m "initial schema"
```

This will:
- Scan all SQLAlchemy models
- Compare with current database state
- Generate a migration file in `alembic/versions/`

### 2. Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply one migration at a time
alembic upgrade +1

# Apply to a specific revision
alembic upgrade <revision_id>
```

### 3. Rollback Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### 4. View Migration History

```bash
# Show current revision
alembic current

# Show all revisions
alembic history

# Show verbose history
alembic history --verbose
```

### 5. Create Empty Migration (for data migrations)

```bash
alembic revision -m "add default data"
```

## Migration Workflow

### For New Features

1. **Modify Models**: Update SQLAlchemy models in `app/models/`
2. **Generate Migration**:
   ```bash
   alembic revision --autogenerate -m "add new_column to users"
   ```
3. **Review Migration**: Check the generated file in `alembic/versions/`
4. **Test Migration**:
   ```bash
   alembic upgrade head
   ```
5. **Test Rollback**:
   ```bash
   alembic downgrade -1
   alembic upgrade head
   ```
6. **Commit**: Add migration file to git

### For Production Deployment

1. **Backup Database**: Always backup before migrations
2. **Test on Staging**: Run migrations on staging environment first
3. **Apply to Production**:
   ```bash
   alembic upgrade head
   ```
4. **Verify**: Check application logs and database state

## Important Notes

### What Alembic Detects

✅ **Automatically Detected:**
- New tables
- New columns
- Column type changes
- Column renames (with hints)
- Index additions/removals
- Foreign key changes

❌ **NOT Automatically Detected:**
- Table renames (appears as drop + create)
- Column renames (appears as drop + add)
- Constraint changes (may need manual editing)
- Enum changes (requires special handling)

### Manual Migration Editing

After generating a migration, you may need to edit it:

```python
# Example: Rename column instead of drop + add
def upgrade():
    op.alter_column('users', 'old_name', new_column_name='new_name')

def downgrade():
    op.alter_column('users', 'new_name', new_column_name='old_name')
```

### Data Migrations

For data-only changes, create an empty migration:

```bash
alembic revision -m "populate default roles"
```

Then edit the migration file:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Insert default data
    op.execute("""
        INSERT INTO roles (name, description)
        VALUES ('admin', 'Administrator role')
    """)

def downgrade():
    # Remove default data
    op.execute("DELETE FROM roles WHERE name = 'admin'")
```

## Troubleshooting

### Issue: "Target database is not up to date"

```bash
# Check current state
alembic current

# Stamp database with current revision (if migrations were applied manually)
alembic stamp head
```

### Issue: "Can't locate revision identified by 'xyz'"

```bash
# This usually means the migration file is missing
# Check alembic/versions/ directory
# Restore from git if needed
```

### Issue: Migration conflicts

```bash
# If multiple developers created migrations simultaneously
# You may need to merge migration branches

# Check history
alembic history

# Merge branches (if needed)
alembic merge -m "merge migrations" <rev1> <rev2>
```

### Issue: "sqlalchemy.url" not found

Make sure your `.env` file has `DATABASE_URL` set correctly.

## Removing Runtime Schema Patching

After confirming migrations work, you can remove the runtime schema patching from `app/main.py`:

1. Comment out or remove the `_startup_init_db()` function
2. Remove the schema upgrade SQL in the startup event
3. Keep only `Base.metadata.create_all(bind=engine)` for development convenience (optional)

## Best Practices

1. **Always review generated migrations** - Alembic may not detect everything correctly
2. **Test rollbacks** - Ensure `downgrade()` works before committing
3. **Keep migrations small** - One logical change per migration
4. **Use descriptive names** - Make it clear what the migration does
5. **Never edit applied migrations** - Create a new migration instead
6. **Backup before production migrations** - Always have a rollback plan
7. **Run migrations in CI/CD** - Automate migration testing

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# Example GitHub Actions
- name: Run migrations
  run: |
    cd backend
    alembic upgrade head

- name: Test rollback
  run: |
    cd backend
    alembic downgrade -1
    alembic upgrade head
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Project README: `../README.md`
