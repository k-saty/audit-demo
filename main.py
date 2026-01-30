from fastapi import FastAPI, Depends, Request, HTTPException, Header, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import time
import threading
from datetime import datetime
from typing import Optional

from database import SessionLocal, engine
from models import Base, ConversationAuditLog, PIIDetectionLog, User
from schemas import (
    AuditLogCreate,
    AuditLogResponse,
    CurrentUser,
    UserCreate,
    UserResponse,
)
from crud import (
    create_log,
    create_user,
    get_user_by_username,
    get_all_users,
    promote_user_to_admin,
)
from crud import (
    get_retention_for_tenant,
    set_retention_for_tenant,
    run_retention_cleanup,
)
from schemas import RetentionUpdate, DeletionAuditRecord
from compliance_export import generate_compliance_export

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


# ============ AUTH & RBAC DEPENDENCIES ============


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    """
    Extract current user from session cookie `session_user` or X-User header.
    In production, replace with proper JWT/session validation.
    """
    # First try cookie
    username = request.cookies.get("session_user")
    # Fallback to X-User header for backwards compatibility
    if not username:
        username = request.headers.get("x-user")

    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return CurrentUser(username=user.username, role=user.role)


@app.post("/auth/login")
def auth_login(payload: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Login endpoint for demo: creates user if missing and sets a session cookie."""
    if payload.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = get_user_by_username(db, payload.username)
    if not user:
        user = create_user(db, payload.username, payload.role)

    # Set cookie (demo, httponly)
    response.set_cookie("session_user", user.username, httponly=True)
    return {"username": user.username, "role": user.role}


@app.post("/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie("session_user")
    return {"message": "logged out"}


@app.get("/auth/me", response_model=CurrentUser)
def auth_me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user


def require_role(required_role: str):
    """
    Dependency factory to enforce role-based access.
    Usage: @app.post("/admin/route", dependencies=[Depends(require_role("admin"))])
    """

    async def check_role(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role != required_role and required_role != "viewer":
            # Allow admin to access viewer routes
            if not (current_user.role == "admin" and required_role == "viewer"):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required role: {required_role}",
                )
        return current_user

    return check_role


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


# ============ USER MANAGEMENT ENDPOINTS ============


@app.post("/users/create", response_model=UserResponse)
def create_new_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new user. Only admins can do this."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create users")

    # Only admins can create admin users
    if payload.role == "admin" and current_user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Only admins can create admin users"
        )

    existing = get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = create_user(db, payload.username, payload.role)
    return user


@app.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all users. Both admins and viewers can access this."""
    users = get_all_users(db)
    return users


@app.get("/users/me", response_model=CurrentUser)
def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """Get information about the currently authenticated user."""
    return current_user


@app.post("/users/{username}/promote")
def promote_to_admin(
    username: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Promote a user to admin. Only existing admins can do this."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can promote users")

    user = promote_user_to_admin(db, username)
    return {
        "message": f"User {username} promoted to admin",
        "user": UserResponse.from_orm(user),
    }


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
@app.post("/admin/retention", dependencies=[Depends(require_role("admin"))])
def admin_set_retention(payload: RetentionUpdate, db: Session = Depends(get_db)):
    # NOTE: Endpoint is protected by admin role
    set_retention_for_tenant(db, payload.tenant_id, payload.retention_days)
    return {"tenant_id": payload.tenant_id, "retention_days": payload.retention_days}


@app.get("/admin/deletion-audits", dependencies=[Depends(require_role("admin"))])
def admin_get_deletion_audits(tenant_id: str = None, db: Session = Depends(get_db)):
    # NOTE: Endpoint is protected by admin role
    q = db.query
    from models import DeletionAuditLog

    q = db.query(DeletionAuditLog)
    if tenant_id:
        q = q.filter(DeletionAuditLog.tenant_id == tenant_id)
    q = q.order_by(DeletionAuditLog.run_timestamp.desc())
    results = q.all()
    return {"count": len(results), "audits": results}


@app.post("/admin/run-cleanup", dependencies=[Depends(require_role("admin"))])
def admin_run_cleanup(db: Session = Depends(get_db)):
    # NOTE: this endpoint is provided for demo/testing only. In production, cleanup must be non-user-triggered.
    # Endpoint is protected by admin role
    audits = run_retention_cleanup(db)
    return {"count": len(audits), "audits": audits}


@app.get("/pii/summary")
def get_pii_summary(tenant_id: str, db: Session = Depends(get_db)):
    """Get PII detection summary for a tenant."""
    pii_logs = (
        db.query(PIIDetectionLog)
        .filter(PIIDetectionLog.tenant_id == tenant_id)
        .order_by(PIIDetectionLog.detection_timestamp.desc())
        .all()
    )

    # Aggregate statistics
    total_detections = len(pii_logs)
    high_risk_count = sum(
        1
        for log in pii_logs
        if any(p.get("risk_level") == "high" for p in log.pii_detected)
    )

    # Count by PII type
    pii_type_counts = {}
    for log in pii_logs:
        for pii_item in log.pii_detected:
            pii_type = pii_item.get("type", "unknown")
            pii_type_counts[pii_type] = pii_type_counts.get(pii_type, 0) + 1

    return {
        "tenant_id": tenant_id,
        "total_pii_detections": total_detections,
        "high_risk_count": high_risk_count,
        "pii_type_breakdown": pii_type_counts,
        "recent_detections": [
            {
                "detection_id": str(log.id),
                "audit_log_id": str(log.audit_log_id),
                "timestamp": log.detection_timestamp,
                "pii_count": log.pii_count,
                "high_risk": any(
                    p.get("risk_level") == "high" for p in log.pii_detected
                ),
                "pii_types": list(set(p.get("type") for p in log.pii_detected)),
            }
            for log in pii_logs[:10]  # Last 10
        ],
    }


@app.get("/pii/details/{detection_id}")
def get_pii_details(detection_id: str, db: Session = Depends(get_db)):
    """Get detailed PII findings for a specific detection."""
    pii_log = (
        db.query(PIIDetectionLog).filter(PIIDetectionLog.id == detection_id).first()
    )

    # Fetch the original audit log
    audit_log = None
    if pii_log:
        audit_log = (
            db.query(ConversationAuditLog)
            .filter(ConversationAuditLog.id == pii_log.audit_log_id)
            .first()
        )

    if not pii_log:
        return {
            "detection_id": detection_id,
            "pii_found": False,
            "pii_count": 0,
            "details": [],
            "audit_log": None,
            "ner_response_prompt": None,
            "ner_response_response": None,
        }

    return {
        "detection_id": str(pii_log.id),
        "audit_log_id": str(pii_log.audit_log_id),
        "tenant_id": pii_log.tenant_id,
        "detection_timestamp": pii_log.detection_timestamp,
        "pii_found": pii_log.pii_count > 0,
        "pii_count": pii_log.pii_count,
        "fields_scanned": pii_log.fields_scanned,
        "details": pii_log.pii_detected,
        "high_risk_items": [
            p for p in pii_log.pii_detected if p.get("risk_level") == "high"
        ],
        "ner_response_prompt": pii_log.ner_response_prompt,
        "ner_response_response": pii_log.ner_response_response,
        "audit_log": (
            {
                "id": str(audit_log.id),
                "timestamp": audit_log.timestamp,
                "tenant_id": audit_log.tenant_id,
                "agent_id": audit_log.agent_id,
                "session_id": audit_log.session_id,
                "channel": audit_log.channel,
                "prompt": audit_log.prompt,
                "response": audit_log.response,
            }
            if audit_log
            else None
        ),
    }


@app.get("/pii/logs")
def get_pii_logs(
    tenant_id: str = None, risk_level: str = None, db: Session = Depends(get_db)
):
    """Get PII detection logs with optional filtering."""
    query = db.query(PIIDetectionLog)

    if tenant_id:
        query = query.filter(PIIDetectionLog.tenant_id == tenant_id)

    pii_logs = query.order_by(PIIDetectionLog.detection_timestamp.desc()).all()

    # Filter by risk level if specified
    if risk_level:
        pii_logs = [
            log
            for log in pii_logs
            if any(p.get("risk_level") == risk_level for p in log.pii_detected)
        ]

    return {
        "count": len(pii_logs),
        "logs": [
            {
                "detection_id": str(log.id),
                "audit_log_id": str(log.audit_log_id),
                "tenant_id": log.tenant_id,
                "timestamp": log.detection_timestamp,
                "pii_count": log.pii_count,
                "high_risk": any(
                    p.get("risk_level") == "high" for p in log.pii_detected
                ),
                "pii_types": list(set(p.get("type") for p in log.pii_detected)),
            }
            for log in pii_logs
        ],
    }


@app.get("/compliance/export")
def export_compliance_pack(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Generate and download compliance export pack as ZIP."""
    if not tenant_id:
        return {"error": "tenant_id is required"}

    try:
        print(f"Generating compliance export for tenant: {tenant_id}")
        zip_buffer = generate_compliance_export(db, tenant_id)
        zip_data = zip_buffer.getvalue()
        print(f"Generated ZIP size: {len(zip_data)} bytes")

        return StreamingResponse(
            iter([zip_data]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=compliance_export_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
            },
        )
    except Exception as e:
        print(f"Export error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
