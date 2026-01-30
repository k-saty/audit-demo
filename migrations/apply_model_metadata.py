#!/usr/bin/env python
"""
Migration Helper: Apply Model Metadata Columns
Purpose: Add model_provider, model_name, model_version, deployment_id, temperature, safety_mode, model_config to conversation_audit_logs
Run this script to programmatically apply the migration.
"""

import sys
from sqlalchemy import text
from database import SessionLocal


def apply_migration():
    """Apply model metadata columns migration."""
    db = SessionLocal()
    try:
        print("[INFO] Starting migration: Add Model Metadata Columns")

        # SQL migration statement
        migration_sql = """
        ALTER TABLE conversation_audit_logs
        ADD COLUMN IF NOT EXISTS model_provider TEXT,
        ADD COLUMN IF NOT EXISTS model_name TEXT,
        ADD COLUMN IF NOT EXISTS model_version TEXT,
        ADD COLUMN IF NOT EXISTS deployment_id TEXT,
        ADD COLUMN IF NOT EXISTS temperature TEXT,
        ADD COLUMN IF NOT EXISTS safety_mode TEXT,
        ADD COLUMN IF NOT EXISTS model_config JSONB;
        """

        db.execute(text(migration_sql))
        db.commit()

        print("[SUCCESS] Migration applied successfully!")
        print("[INFO] New columns added:")
        print("  - model_provider (TEXT)")
        print("  - model_name (TEXT)")
        print("  - model_version (TEXT)")
        print("  - deployment_id (TEXT)")
        print("  - temperature (TEXT)")
        print("  - safety_mode (TEXT)")
        print("  - model_config (JSONB)")

        return True
    except Exception as e:
        print(f"[ERROR] Migration failed: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
