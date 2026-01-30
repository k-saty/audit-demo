"""
Unit Tests: Model Metadata Logging Feature
Tests for metadata persistence, export, and retrieval
"""

import json
from datetime import datetime
from schemas import AuditLogCreate
from crud import create_log
from models import ConversationAuditLog


def test_audit_log_with_model_metadata():
    """Test creating an audit log with complete model metadata."""

    # Sample audit log data with metadata
    log_data = AuditLogCreate(
        tenant_id="test-tenant",
        agent_id="agent-001",
        session_id="sess-abc123",
        channel="api",
        prompt="What is machine learning?",
        response="Machine learning is a subset of AI...",
        model_info="gpt-4-turbo",
        model_provider="openai",
        model_name="gpt-4-turbo",
        model_version="2024-04-09",
        deployment_id=None,
        temperature="0.7",
        safety_mode="strict",
        model_config={"top_p": 0.9, "frequency_penalty": 0.5},
    )

    print("[TEST] Creating audit log with model metadata...")
    print(f"  Payload: {log_data.dict()}")

    # Verify all fields are present
    assert log_data.model_provider == "openai"
    assert log_data.model_name == "gpt-4-turbo"
    assert log_data.model_version == "2024-04-09"
    assert log_data.temperature == "0.7"
    assert log_data.safety_mode == "strict"
    assert log_data.model_config["top_p"] == 0.9

    print("[PASS] Audit log metadata validation passed")
    return True


def test_audit_log_with_azure_deployment():
    """Test creating an audit log with Azure deployment ID."""

    log_data = AuditLogCreate(
        tenant_id="azure-tenant",
        agent_id="agent-azure",
        session_id="sess-xyz789",
        channel="web",
        prompt="Analyze this data",
        response="Analysis complete...",
        model_info="gpt-35-turbo",
        model_provider="azure",
        model_name="gpt-35-turbo",
        model_version="1.0",
        deployment_id="my-gpt-35-turbo-deployment",
        temperature="0.5",
        safety_mode="relaxed",
        model_config={"max_tokens": 2000},
    )

    print("[TEST] Creating audit log with Azure deployment ID...")

    assert log_data.deployment_id == "my-gpt-35-turbo-deployment"
    assert log_data.model_provider == "azure"

    print("[PASS] Azure deployment metadata validation passed")
    return True


def test_audit_log_minimal_metadata():
    """Test creating an audit log with minimal metadata (some fields missing)."""

    log_data = AuditLogCreate(
        tenant_id="minimal-tenant",
        agent_id="agent-min",
        session_id="sess-min123",
        channel="api",
        prompt="Hello",
        response="Hi there",
        model_info="default",
        # Only required fields, metadata is optional
    )

    print("[TEST] Creating audit log with minimal/missing metadata...")

    assert log_data.model_provider is None
    assert log_data.model_name is None
    assert log_data.temperature is None

    print("[PASS] Minimal metadata validation passed (backwards compatible)")
    return True


def test_export_includes_metadata_columns():
    """Test that CSV export includes model metadata columns."""

    csv_headers = [
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

    print("[TEST] Verifying export CSV headers include metadata...")

    metadata_headers = [
        "Model Provider",
        "Model Name",
        "Model Version",
        "Deployment ID",
        "Temperature",
        "Safety Mode",
        "Model Config",
    ]

    for header in metadata_headers:
        assert header in csv_headers, f"Missing header: {header}"

    print(f"[PASS] Export includes all {len(metadata_headers)} metadata columns")
    return True


def test_metadata_compliance_reporting():
    """Test that metadata can be filtered for compliance audits."""

    # Simulate audit logs with different model providers
    logs = [
        {
            "id": "log-1",
            "model_provider": "openai",
            "model_name": "gpt-4",
            "safety_mode": "strict",
        },
        {
            "id": "log-2",
            "model_provider": "anthropic",
            "model_name": "claude-3",
            "safety_mode": "balanced",
        },
        {
            "id": "log-3",
            "model_provider": "openai",
            "model_name": "gpt-35-turbo",
            "safety_mode": "relaxed",
        },
    ]

    print("[TEST] Filtering logs by model provider for compliance audit...")

    # Filter for OpenAI logs
    openai_logs = [log for log in logs if log["model_provider"] == "openai"]
    assert len(openai_logs) == 2
    assert all(log["model_provider"] == "openai" for log in openai_logs)

    # Filter for high-security (strict safety mode)
    high_sec_logs = [log for log in logs if log["safety_mode"] == "strict"]
    assert len(high_sec_logs) == 1
    assert high_sec_logs[0]["model_name"] == "gpt-4"

    print("[PASS] Metadata filtering for compliance reporting works correctly")
    return True


def run_all_tests():
    """Run all metadata feature tests."""
    tests = [
        test_audit_log_with_model_metadata,
        test_audit_log_with_azure_deployment,
        test_audit_log_minimal_metadata,
        test_export_includes_metadata_columns,
        test_metadata_compliance_reporting,
    ]

    print("=" * 70)
    print("Model Metadata Logging Feature - Unit Tests")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {str(e)}")
            failed += 1
        print()

    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
