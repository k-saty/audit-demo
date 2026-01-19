import uuid
from sqlalchemy import Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class ConversationAuditLog(Base):
    __tablename__ = "conversation_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(TIMESTAMP(timezone=True))
    tenant_id = Column(Text, nullable=False)
    agent_id = Column(Text, nullable=False)
    session_id = Column(Text, nullable=False)
    channel = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
