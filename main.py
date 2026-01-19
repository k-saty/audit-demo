from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import time

from database import SessionLocal, engine
from models import Base, ConversationAuditLog
from schemas import AuditLogCreate, AuditLogResponse
from crud import create_log

app = FastAPI(title="Conversation Audit Logs Demo")


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
