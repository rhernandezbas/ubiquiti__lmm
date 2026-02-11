#!/usr/bin/env python3
"""
Run Alembic database migrations automatically.

This script can be called:
1. On application startup
2. In GitHub Actions deployment
3. Manually from command line

Usage:
    python run_migrations.py
"""

import os
import sys
from alembic.config import Config
from alembic import command
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent

def run_migrations():
    """Run all pending Alembic migrations."""
    try:
        # Check if DATABASE_URL is set
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: DATABASE_URL environment variable not set")
            print("   Set it with: export DATABASE_URL='mysql+pymysql://user:pass@host:port/db'")
            return False

        print("🔧 Running database migrations...")
        print(f"   Database: {database_url.split('@')[-1] if '@' in database_url else 'unknown'}")

        # Create Alembic config
        alembic_ini = PROJECT_ROOT / "alembic.ini"
        if not alembic_ini.exists():
            print(f"❌ ERROR: alembic.ini not found at {alembic_ini}")
            return False

        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        # Run migrations to head (latest version)
        print("📝 Applying migrations...")
        command.upgrade(alembic_cfg, "head")

        print("✅ Migrations completed successfully!")
        return True

    except Exception as e:
        print(f"❌ ERROR running migrations: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_migrations_status():
    """Check current migration status."""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not set")
            return

        alembic_ini = PROJECT_ROOT / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        print("📋 Current migration status:")
        command.current(alembic_cfg)

        print("\n📋 Migration history:")
        command.history(alembic_cfg)

    except Exception as e:
        print(f"❌ ERROR checking status: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_migrations_status()
    else:
        success = run_migrations()
        sys.exit(0 if success else 1)
