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
    model_info: str = (
        "default"  # Model name/version used (e.g., 'gpt-4', 'claude-3', etc.)
    )


class AuditLogResponse(BaseModel):
    log_id: UUID
    timestamp: datetime


class RetentionUpdate(BaseModel):
    tenant_id: str
    retention_days: int


class DeletionAuditRecord(BaseModel):
    id: UUID
    tenant_id: str
    retention_days: int
    deleted_before: datetime
    deleted_count: int
    run_timestamp: datetime

    class Config:
        orm_mode = True


# ============ AUTH & RBAC SCHEMAS ============


class UserCreate(BaseModel):
    username: str
    role: str = "viewer"  # Default role


class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    created_at: datetime

    class Config:
        orm_mode = True


class CurrentUser(BaseModel):
    username: str
    role: str
