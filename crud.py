from sqlalchemy.orm import Session
from datetime import datetime
from models import ConversationAuditLog


def create_log(db: Session, data):
    log = ConversationAuditLog(timestamp=datetime.utcnow(), **data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
