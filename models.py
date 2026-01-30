import uuid
from datetime import datetime
from sqlalchemy import Column, Text, TIMESTAMP, Integer, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from enum import Enum
from sqlalchemy import event
from sqlalchemy.orm import Session


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    VIEWER = "viewer"


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
    model_info = Column(Text, nullable=False, default="default")
    # Model metadata for auditor traceability
    model_provider = Column(
        Text, nullable=True
    )  # e.g., 'openai', 'anthropic', 'cohere'
    model_name = Column(Text, nullable=True)  # e.g., 'gpt-4', 'claude-3-sonnet'
    model_version = Column(Text, nullable=True)  # e.g., '1.0', 'v20240115'
    deployment_id = Column(Text, nullable=True)  # e.g., Azure deployment ID
    temperature = Column(Text, nullable=True)  # e.g., '0.7' (string for precision)
    safety_mode = Column(Text, nullable=True)  # e.g., 'strict', 'relaxed', 'balanced'
    model_config = Column(
        JSON, nullable=True
    )  # Extra config: top_p, frequency_penalty, etc.


# Enforce append-only & immutable: prevent any UPDATE or DELETE operations on ConversationAuditLog instances.
@event.listens_for(ConversationAuditLog, "before_update", propagate=True)
def _prevent_conversation_update(mapper, connection, target):
    raise Exception("ConversationAuditLog is immutable and cannot be updated")


@event.listens_for(ConversationAuditLog, "before_delete", propagate=True)
def _prevent_conversation_delete(mapper, connection, target):
    raise Exception("ConversationAuditLog is immutable and cannot be deleted")


class TenantRetention(Base):
    """Per-tenant retention configuration (days).

    Allowed values: 30, 90, 180. Default can be set per-tenant; if missing a global default is used.
    """

    __tablename__ = "tenant_retention"

    tenant_id = Column(Text, primary_key=True)
    retention_days = Column(Integer, nullable=False, default=90)


class DeletionAuditLog(Base):
    """Records automatic deletion runs for compliance auditing.

    Each record represents one tenant's deletion action: when it ran and how many rows were removed.
    """

    __tablename__ = "deletion_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Text, nullable=False)
    retention_days = Column(Integer, nullable=False)
    deleted_before = Column(DateTime(timezone=True), nullable=False)
    deleted_count = Column(Integer, nullable=False)
    run_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)


class PIIDetectionLog(Base):
    """Records PII detection results for audit logs.

    Stores detected PII entities (email, phone, name, etc.) from conversation logs.
    """

    __tablename__ = "pii_detection_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id = Column(Text, nullable=False)
    detection_timestamp = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    pii_detected = Column(
        JSON, nullable=False
    )  # list of {type, value, field, risk_level}
    pii_count = Column(Integer, nullable=False, default=0)
    fields_scanned = Column(JSON, nullable=False)  # ["prompt", "response"]
    ner_response_prompt = Column(JSON, nullable=True)  # NER API response for prompt
    ner_response_response = Column(JSON, nullable=True)  # NER API response for response
    ner_response_prompt = Column(JSON, nullable=True)  # Raw NER API response for prompt
    ner_response_response = Column(
        JSON, nullable=True
    )  # Raw NER API response for response
    ner_model_info = Column(
        Text, nullable=False, default="dslim/bert-base-NER"
    )  # NER model used


class User(Base):
    """User model with role-based access control."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, unique=True, nullable=False)
    role = Column(SQLEnum(Role), nullable=False, default=Role.VIEWER)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
