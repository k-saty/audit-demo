"""
Compliance Export module for generating audit-ready compliance artifacts.
Generates a ZIP file containing:
- Conversation logs (CSV)
- PII detection logs (CSV)
- Data sources manifest
- Model info
- Retention policy
- Timestamps and metadata
"""

import io
import csv
import json
import zipfile
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    ConversationAuditLog,
    PIIDetectionLog,
    TenantRetention,
    DeletionAuditLog,
)


def generate_compliance_export(db: Session, tenant_id: str) -> io.BytesIO:
    """
    Generate a compliance export ZIP file for a tenant.
    Returns BytesIO object containing the ZIP.
    """
    zip_buffer = io.BytesIO()
    export_timestamp = datetime.utcnow().isoformat()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Export conversation logs as CSV
        logs = (
            db.query(ConversationAuditLog)
            .filter(ConversationAuditLog.tenant_id == tenant_id)
            .order_by(ConversationAuditLog.timestamp.desc())
            .all()
        )

        if logs:
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(
                [
                    "Log ID",
                    "Timestamp",
                    "Agent ID",
                    "Session ID",
                    "Channel",
                    "Prompt",
                    "Response",
                    "Model Info",
                    "Model Provider",
                    "Model Name",
                    "Model Version",
                    "Deployment ID",
                    "Temperature",
                    "Safety Mode",
                    "Model Config",
                ]
            )

            for log in logs:
                writer.writerow(
                    [
                        str(log.id),
                        log.timestamp.isoformat(),
                        log.agent_id,
                        log.session_id,
                        log.channel,
                        log.prompt,
                        log.response,
                        log.model_info,
                        log.model_provider or "",
                        log.model_name or "",
                        log.model_version or "",
                        log.deployment_id or "",
                        log.temperature or "",
                        log.safety_mode or "",
                        str(log.model_config) if log.model_config else "",
                    ]
                )

            zip_file.writestr("conversation_logs.csv", csv_buffer.getvalue())

        # 2. Export PII detection logs as CSV
        pii_logs = (
            db.query(PIIDetectionLog)
            .filter(PIIDetectionLog.tenant_id == tenant_id)
            .order_by(PIIDetectionLog.detection_timestamp.desc())
            .all()
        )

        if pii_logs:
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(
                [
                    "Detection ID",
                    "Audit Log ID",
                    "Timestamp",
                    "PII Count",
                    "High Risk Count",
                    "PII Types",
                    "Risk Levels",
                    "Details",
                ]
            )

            for pii_log in pii_logs:
                pii_types = set()
                high_risk_count = 0
                risk_levels = set()

                for pii_item in pii_log.pii_detected:
                    pii_types.add(pii_item.get("type", "unknown"))
                    risk_levels.add(pii_item.get("risk_level", "unknown"))
                    if pii_item.get("risk_level") == "high":
                        high_risk_count += 1

                writer.writerow(
                    [
                        str(pii_log.id),
                        str(pii_log.audit_log_id),
                        pii_log.detection_timestamp.isoformat(),
                        pii_log.pii_count,
                        high_risk_count,
                        "|".join(sorted(pii_types)),
                        "|".join(sorted(risk_levels)),
                        (
                            json.dumps(pii_log.pii_detected)[:100] + "..."
                            if len(json.dumps(pii_log.pii_detected)) > 100
                            else json.dumps(pii_log.pii_detected)
                        ),
                    ]
                )

            zip_file.writestr("pii_detection_logs.csv", csv_buffer.getvalue())

        # 3. Data sources manifest
        sources_manifest = {
            "export_timestamp": export_timestamp,
            "tenant_id": tenant_id,
            "data_sources": [
                {
                    "name": "conversation_audit_logs",
                    "description": "Conversation logs including prompts and agent responses",
                    "record_count": len(logs),
                    "fields": [
                        "id",
                        "timestamp",
                        "tenant_id",
                        "agent_id",
                        "session_id",
                        "channel",
                        "prompt",
                        "response",
                        "model_info",
                        "model_provider",
                        "model_name",
                        "model_version",
                        "deployment_id",
                        "temperature",
                        "safety_mode",
                        "model_config",
                    ],
                },
                {
                    "name": "pii_detection_logs",
                    "description": "PII detection results and findings",
                    "record_count": len(pii_logs),
                    "fields": [
                        "id",
                        "audit_log_id",
                        "tenant_id",
                        "detection_timestamp",
                        "pii_detected",
                        "pii_count",
                        "fields_scanned",
                    ],
                },
            ],
        }
        zip_file.writestr("data_sources.json", json.dumps(sources_manifest, indent=2))

        # 4. Model info
        model_info = {
            "model_name": "dslim/bert-base-multilingual-cased-ner-hrl",
            "model_type": "Named Entity Recognition (NER)",
            "model_source": "HuggingFace Hub",
            "model_api_endpoint": "https://router.huggingface.co/models/dslim/bert-base-multilingual-cased-ner-hrl",
            "detection_methods": [
                "NER Model: BERT-based entity recognition",
                "Regex Patterns: Email, Phone, SSN, Credit Card, IPv4",
            ],
            "pii_categories_detected": [
                "PERSON",
                "EMAIL",
                "PHONE",
                "SSN",
                "CREDIT_CARD",
                "IPV4",
                "DATE",
                "ORG",
                "LOCATION",
                "MISC",
            ],
            "risk_levels": {
                "high": ["email", "phone", "ssn", "credit_card", "PERSON"],
                "medium": ["ipv4", "DATE", "ORG"],
                "low": ["LOCATION", "MISC"],
            },
        }
        zip_file.writestr("model_info.json", json.dumps(model_info, indent=2))

        # 5. Retention policy
        retention_policy = {
            "tenant_id": tenant_id,
            "retention_days": int(
                db.query(TenantRetention.retention_days)
                .filter(TenantRetention.tenant_id == tenant_id)
                .scalar()
                or 90
            ),
            "allowed_retention_values": [30, 90, 180],
            "deletion_audits": [],
        }

        deletion_audits = (
            db.query(DeletionAuditLog)
            .filter(DeletionAuditLog.tenant_id == tenant_id)
            .order_by(DeletionAuditLog.run_timestamp.desc())
            .all()
        )

        for audit in deletion_audits:
            retention_policy["deletion_audits"].append(
                {
                    "audit_id": str(audit.id),
                    "run_timestamp": audit.run_timestamp.isoformat(),
                    "deleted_before": audit.deleted_before.isoformat(),
                    "deleted_count": audit.deleted_count,
                    "retention_days": audit.retention_days,
                }
            )

        zip_file.writestr(
            "retention_policy.json", json.dumps(retention_policy, indent=2)
        )

        # 6. Compliance metadata and timestamps
        compliance_metadata = {
            "export_timestamp": export_timestamp,
            "export_timestamp_unix": int(datetime.utcnow().timestamp()),
            "tenant_id": tenant_id,
            "data_period": {
                "earliest_log": logs[0].timestamp.isoformat() if logs else None,
                "latest_log": logs[-1].timestamp.isoformat() if logs else None,
                "total_logs": len(logs),
                "total_pii_detections": len(pii_logs),
            },
            "compliance_artifacts": [
                "conversation_logs.csv",
                "pii_detection_logs.csv",
                "data_sources.json",
                "model_info.json",
                "retention_policy.json",
                "compliance_metadata.json",
            ],
            "hash_verification": {
                "algorithm": "SHA256",
                "note": "Hash each file for integrity verification",
            },
        }
        zip_file.writestr(
            "compliance_metadata.json", json.dumps(compliance_metadata, indent=2)
        )

        # 7. README with instructions
        readme = f"""# Compliance Export Pack
Generated: {export_timestamp}
Tenant ID: {tenant_id}

## Contents

1. **conversation_logs.csv** - All conversation logs with prompts and responses
2. **pii_detection_logs.csv** - All detected PII findings with risk levels
3. **data_sources.json** - Manifest of data sources and record counts
4. **model_info.json** - Model configuration and detection methods
5. **retention_policy.json** - Data retention settings and deletion audit history
6. **compliance_metadata.json** - Export metadata and audit timestamps

## Usage

This compliance pack is ready for:
- Regulatory audits (GDPR, HIPAA, SOC2, etc.)
- Data governance reviews
- PII leak investigations
- Retention policy compliance verification
- Proof-of-compliance for third parties

## Data Period

- Earliest Log: {logs[0].timestamp.isoformat() if logs else "No logs"}
- Latest Log: {logs[-1].timestamp.isoformat() if logs else "No logs"}
- Total Logs: {len(logs)}
- Total PII Detections: {len(pii_logs)}

## Verification

Each artifact includes:
- Timestamp for audit trail
- Tenant isolation
- Complete data lineage
- Model/detection method documentation

For support, contact compliance team.
"""
        zip_file.writestr("README.txt", readme)

    zip_buffer.seek(0)
    return zip_buffer
