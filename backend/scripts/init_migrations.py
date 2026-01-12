#!/usr/bin/env python3
"""
Script to initialize Alembic migrations for the InterviewPrep-App.

This script:
1. Checks if the database is accessible
2. Creates the initial migration
3. Applies the migration
4. Verifies the setup

Usage:
    python scripts/init_migrations.py
"""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


def check_database_connection():
    """Check if database is accessible."""
    print("🔍 Checking database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nPlease ensure:")
        print("1. PostgreSQL is running (docker-compose up -d)")
        print("2. DATABASE_URL is correctly set in .env")
        print(f"   Current: {settings.DATABASE_URL}")
        return False


def check_alembic_installed():
    """Check if Alembic is installed."""
    print("\n🔍 Checking if Alembic is installed...")
    try:
        result = subprocess.run(["alembic", "--version"], capture_output=True, text=True, check=True)
        print(f"✅ Alembic installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Alembic not found")
        print("\nPlease install Alembic:")
        print("  pip install alembic>=1.18.0")
        return False


def check_existing_migrations():
    """Check if migrations already exist."""
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migrations = list(versions_dir.glob("*.py"))
    migrations = [m for m in migrations if m.name != "__pycache__"]

    if migrations:
        print(f"\n⚠️  Found {len(migrations)} existing migration(s):")
        for migration in migrations:
            print(f"   - {migration.name}")
        return True
    return False


def create_initial_migration():
    """Create the initial migration."""
    print("\n📝 Creating initial migration...")
    try:
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "initial schema"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        print("✅ Initial migration created")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create migration: {e}")
        print(e.stdout)
        print(e.stderr)
        return False


def apply_migration():
    """Apply the migration to the database."""
    print("\n🚀 Applying migration to database...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        print("✅ Migration applied successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to apply migration: {e}")
        print(e.stdout)
        print(e.stderr)
        return False


def verify_migration():
    """Verify the migration was applied."""
    print("\n🔍 Verifying migration...")
    try:
        result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parents[1]
        )
        print("✅ Current migration status:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to verify migration: {e}")
        print(e.stderr)
        return False


def main():
    """Main execution function."""
    print("=" * 60)
    print("InterviewPrep-App: Alembic Migration Initialization")
    print("=" * 60)

    # Step 1: Check database connection
    if not check_database_connection():
        sys.exit(1)

    # Step 2: Check Alembic installation
    if not check_alembic_installed():
        sys.exit(1)

    # Step 3: Check for existing migrations
    if check_existing_migrations():
        response = input("\n⚠️  Migrations already exist. Continue anyway? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Step 4: Create initial migration
    if not create_initial_migration():
        sys.exit(1)

    # Step 5: Ask user if they want to apply the migration
    print("\n" + "=" * 60)
    response = input("Apply migration to database now? (Y/n): ")
    if response.lower() != "n":
        if not apply_migration():
            sys.exit(1)

        # Step 6: Verify migration
        verify_migration()
    else:
        print("\nMigration created but not applied.")
        print("To apply later, run: alembic upgrade head")

    print("\n" + "=" * 60)
    print("✅ Alembic setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the generated migration in alembic/versions/")
    print("2. Test rollback: alembic downgrade -1")
    print("3. Re-apply: alembic upgrade head")
    print("4. See MIGRATIONS.md for more information")
    print("\nTo remove runtime schema patching from main.py:")
    print("- Comment out the schema upgrade SQL in _startup_init_db()")
    print("- Keep Base.metadata.create_all() for dev convenience (optional)")


if __name__ == "__main__":
    main()
