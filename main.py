from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import time
import threading
from datetime import datetime

from database import SessionLocal, engine
from models import Base, ConversationAuditLog
from schemas import AuditLogCreate, AuditLogResponse
from crud import create_log
from crud import (
    get_retention_for_tenant,
    set_retention_for_tenant,
    run_retention_cleanup,
)
from schemas import RetentionUpdate, DeletionAuditRecord

app = FastAPI(title="Conversation Audit Logs Demo")

# Serve static files and templates for a small dashboard UI
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ DB init with retry
@app.on_event("startup")
def startup_event():
    retries = 10
    while retries > 0:
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database connected and tables created")
            break
        except OperationalError:
            retries -= 1
            print("⏳ Waiting for database...")
            time.sleep(2)
    else:
        raise Exception("❌ Database not available after retries")

    # Run an immediate cleanup once at startup for any overdue logs
    try:
        db = SessionLocal()
        run_retention_cleanup(db)
    finally:
        db.close()

    # Start background thread to run retention cleanup once every 24 hours
    def retention_loop():
        interval_seconds = 24 * 60 * 60
        while True:
            try:
                db = SessionLocal()
                run_retention_cleanup(db)
            except Exception as e:
                print("Retention cleanup failed:", e)
            finally:
                try:
                    db.close()
                except Exception:
                    pass
            time.sleep(interval_seconds)

    t = threading.Thread(target=retention_loop, daemon=True, name="retention-cleaner")
    t.start()


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/audit/log", response_model=AuditLogResponse)
def log_conversation(data: AuditLogCreate, db: Session = Depends(get_db)):
    log = create_log(db, data)
    return {"log_id": log.id, "timestamp": log.timestamp}


@app.get("/audit/logs")
def get_logs(tenant_id: str, db: Session = Depends(get_db)):
    logs = (
        db.query(ConversationAuditLog)
        .filter(ConversationAuditLog.tenant_id == tenant_id)
        .order_by(ConversationAuditLog.timestamp.desc())
        .all()
    )
    return {"count": len(logs), "logs": logs}


# Admin endpoints for retention management and audit viewing
@app.post("/admin/retention")
def admin_set_retention(payload: RetentionUpdate, db: Session = Depends(get_db)):
    # NOTE: In production, protect this endpoint with admin auth
    set_retention_for_tenant(db, payload.tenant_id, payload.retention_days)
    return {"tenant_id": payload.tenant_id, "retention_days": payload.retention_days}


@app.get("/admin/deletion-audits")
def admin_get_deletion_audits(tenant_id: str = None, db: Session = Depends(get_db)):
    # NOTE: protect in production
    q = db.query
    from models import DeletionAuditLog

    q = db.query(DeletionAuditLog)
    if tenant_id:
        q = q.filter(DeletionAuditLog.tenant_id == tenant_id)
    q = q.order_by(DeletionAuditLog.run_timestamp.desc())
    results = q.all()
    return {"count": len(results), "audits": results}


@app.post("/admin/run-cleanup")
def admin_run_cleanup(db: Session = Depends(get_db)):
    # NOTE: this endpoint is provided for demo/testing only. In production, cleanup must be non-user-triggered.
    audits = run_retention_cleanup(db)
    return {"count": len(audits), "audits": audits}
