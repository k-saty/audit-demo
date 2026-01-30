from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import select, func

from models import (
    ConversationAuditLog,
    TenantRetention,
    DeletionAuditLog,
    PIIDetectionLog,
    User,
    Role,
)
from pii_detector import scan_audit_log_for_pii


# ============ USER MANAGEMENT ============


def create_user(db: Session, username: str, role: str = "viewer") -> User:
    """Create a new user with a specified role (default: viewer)."""
    # Only allow Admin or Viewer roles
    if role not in ("admin", "viewer"):
        raise ValueError("role must be 'admin' or 'viewer'")

    user = User(username=username, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> User:
    """Retrieve user by username."""
    return db.query(User).filter(User.username == username).first()


def get_all_users(db: Session):
    """Get all users."""
    return db.query(User).all()


def delete_user(db: Session, user_id: str) -> bool:
    """Delete user by ID. Returns True if user was deleted, False if not found."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def promote_user_to_admin(db: Session, username: str) -> User:
    """Promote a user to admin role."""
    user = get_user_by_username(db, username)
    if not user:
        raise ValueError("User not found")
    user.role = "admin"
    db.commit()
    db.refresh(user)
    return user


def create_log(db: Session, data):
    """Create audit log and scan for PII."""
    log = ConversationAuditLog(timestamp=datetime.utcnow(), **data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)

    # Scan for PII
    pii_results = scan_audit_log_for_pii(data.prompt, data.response)

    # Store PII detection results
    if pii_results["total_pii_found"] > 0 or pii_results["high_risk_count"] > 0:
        pii_log = PIIDetectionLog(
            audit_log_id=log.id,
            tenant_id=data.tenant_id,
            pii_detected=pii_results["pii_list"],
            pii_count=pii_results["total_pii_found"],
            fields_scanned=pii_results["fields_scanned"],
            ner_response_prompt=pii_results.get("ner_response_prompt"),
            ner_response_response=pii_results.get("ner_response_response"),
        )
        db.add(pii_log)
        db.commit()

    return log

    return log


def get_retention_for_tenant(db: Session, tenant_id: str) -> int:
    row = db.execute(
        select(TenantRetention.retention_days).where(
            TenantRetention.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    if row is None:
        return 90  # default retention
    return int(row)


def set_retention_for_tenant(db: Session, tenant_id: str, days: int):
    # enforce allowed values
    if days not in (30, 90, 180):
        raise ValueError("retention must be one of 30, 90, 180")
    existing = db.get(TenantRetention, tenant_id)
    if existing:
        existing.retention_days = days
    else:
        tr = TenantRetention(tenant_id=tenant_id, retention_days=days)
        db.add(tr)
    db.commit()


def run_retention_cleanup(db: Session):
    """
    Audit retention policy for each tenant and log findings.

    NOTE: ConversationAuditLog is now immutable (append-only, no deletes allowed).
    This function records what WOULD be deleted per retention policy, but does not
    perform actual deletions. Purging must be handled at database level (e.g., via
    external scripts or manual DB operations).

    Returns list of deletion audit records created (metadata only, no actual deletions).
    """
    # Find distinct tenants in ConversationAuditLog
    tenants = [
        r[0]
        for r in db.execute(select(ConversationAuditLog.tenant_id).distinct()).all()
    ]
    audits = []
    now = datetime.utcnow()
    for tenant in tenants:
        retention = get_retention_for_tenant(db, tenant)
        cutoff = now - timedelta(days=retention)

        # Count how many rows WOULD be deleted (for audit purposes only)
        count_res = db.execute(
            select(func.count(ConversationAuditLog.id)).where(
                ConversationAuditLog.tenant_id == tenant,
                ConversationAuditLog.timestamp < cutoff,
            )
        ).scalar()
        would_delete_count = count_res or 0

        # NOTE: We do NOT actually delete because ConversationAuditLog is immutable.
        # Record the audit entry for compliance purposes.
        audit = DeletionAuditLog(
            tenant_id=tenant,
            retention_days=retention,
            deleted_before=cutoff,
            deleted_count=would_delete_count,  # Records what would have been deleted
            run_timestamp=now,
        )
        db.add(audit)
        db.commit()
        audits.append(audit)
        print(
            f"[Retention Audit] Tenant {tenant}: {would_delete_count} records older than {cutoff} (not deleted - logs are immutable)"
        )

    return audits
