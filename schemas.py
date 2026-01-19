from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class AuditLogCreate(BaseModel):
    tenant_id: str
    agent_id: str
    session_id: str
    channel: str
    prompt: str
    response: str


class AuditLogResponse(BaseModel):
    log_id: UUID
    timestamp: datetime
