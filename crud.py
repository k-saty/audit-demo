from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import select, delete, func

from models import ConversationAuditLog, TenantRetention, DeletionAuditLog


def create_log(db: Session, data):
    log = ConversationAuditLog(timestamp=datetime.utcnow(), **data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
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
    """Delete logs older than retention per tenant. Returns list of deletion audit records created."""
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
        # delete rows older than cutoff for this tenant
        res = db.execute(
            delete(ConversationAuditLog).where(
                ConversationAuditLog.tenant_id == tenant,
                ConversationAuditLog.timestamp < cutoff,
            )
        )
        deleted_count = res.rowcount if hasattr(res, "rowcount") else 0
        db.commit()

        # record deletion audit (immutable)
        audit = DeletionAuditLog(
            tenant_id=tenant,
            retention_days=retention,
            deleted_before=cutoff,
            deleted_count=deleted_count,
            run_timestamp=now,
        )
        db.add(audit)
        db.commit()
        audits.append(audit)

    return audits
