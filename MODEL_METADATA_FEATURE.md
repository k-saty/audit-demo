# Model Metadata Logging Feature

## Overview

This feature enables **model-level traceability** by logging system/model metadata for every conversation interaction. This is critical for auditors to understand which models were used, their configurations, and deployment details.

## What's Tracked

Per conversation/interaction, the system now logs:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `model_provider` | String | LLM service provider | `openai`, `anthropic`, `azure`, `cohere` |
| `model_name` | String | Model identifier | `gpt-4`, `claude-3-sonnet`, `gpt-35-turbo` |
| `model_version` | String | Model version/deployment date | `1.0`, `v20240115` |
| `deployment_id` | String | Cloud provider deployment ID | Azure: `my-gpt-deployment` |
| `temperature` | String | Model sampling temperature (as string) | `0.7`, `0.5` |
| `safety_mode` | String | Safety/moderation level | `strict`, `relaxed`, `balanced` |
| `model_config` | JSON | Extra model configuration | `{"top_p": 0.9, "frequency_penalty": 0.5}` |

## Implementation Details

### Database Schema

Seven new columns added to `conversation_audit_logs` table:

```sql
ALTER TABLE conversation_audit_logs
ADD COLUMN model_provider TEXT,
ADD COLUMN model_name TEXT,
ADD COLUMN model_version TEXT,
ADD COLUMN deployment_id TEXT,
ADD COLUMN temperature TEXT,
ADD COLUMN safety_mode TEXT,
ADD COLUMN model_config JSONB;
```

All columns are **nullable** for backward compatibility.

### API Endpoints

#### Create Audit Log (POST /audit/log)

Request payload now accepts metadata fields:

```json
{
  "tenant_id": "org-123",
  "agent_id": "agent-001",
  "session_id": "sess-abc",
  "channel": "api",
  "prompt": "What is AI?",
  "response": "AI is...",
  "model_info": "gpt-4-turbo",
  "model_provider": "openai",
  "model_name": "gpt-4-turbo",
  "model_version": "2024-04-09",
  "deployment_id": null,
  "temperature": "0.7",
  "safety_mode": "strict",
  "model_config": {"top_p": 0.9}
}
```

**Note:** All metadata fields are optional. Existing integrations without metadata will continue to work.

### Compliance Export

The `compliance_export.zip` now includes model metadata in `conversation_logs.csv`:

```csv
Log ID,Timestamp,Agent ID,Session ID,Channel,Prompt,Response,Model Info,Model Provider,Model Name,Model Version,Deployment ID,Temperature,Safety Mode,Model Config
log-123,2026-01-30T10:30:00Z,agent-001,sess-abc,api,...,...,gpt-4-turbo,openai,gpt-4-turbo,2024-04-09,,0.7,strict,"{...}"
```

### UI/Dashboard

**Create Log Form:**
- New "Model Metadata (Optional)" section in the audit log creation form
- Fields: Model Provider, Model Name, Model Version, Deployment ID, Temperature, Safety Mode

**View Logs Table:**
- Two new columns: "Model Provider" and "Model Name"
- Other metadata available in the underlying data

## Migration

### Option 1: SQL Script (Direct DB)

Apply the migration using PostgreSQL directly:

```bash
psql -U postgres -d compliance_db -f migrations/add_model_metadata.sql
```

### Option 2: Python Helper

Run the provided Python migration helper:

```bash
cd /Users/lockyer/Desktop/audit-demo-2
python migrations/apply_model_metadata.py
```

### Option 3: Manual Database Operation

Connect to your PostgreSQL instance and execute:

```sql
ALTER TABLE conversation_audit_logs
ADD COLUMN IF NOT EXISTS model_provider TEXT,
ADD COLUMN IF NOT EXISTS model_name TEXT,
ADD COLUMN IF NOT EXISTS model_version TEXT,
ADD COLUMN IF NOT EXISTS deployment_id TEXT,
ADD COLUMN IF NOT EXISTS temperature TEXT,
ADD COLUMN IF NOT EXISTS safety_mode TEXT,
ADD COLUMN IF NOT EXISTS model_config JSONB;
```

## Testing

Run the provided test suite:

```bash
python test_model_metadata.py
```

Tests cover:
- Metadata field validation
- Azure deployment scenarios
- Backward compatibility (minimal metadata)
- Export CSV column inclusion
- Compliance filtering by model provider/safety mode

## Security & Privacy Considerations

⚠️ **Important:**

1. **No Secrets in Metadata:**
   - DO NOT log API keys, tokens, or secrets in `model_config`
   - Implement input validation/sanitization in your client code

2. **Prompt/Response Sensitivity:**
   - If prompts/responses contain sensitive data, consider redacting them before logging
   - This feature logs metadata about the MODEL used, not the content itself

3. **Audit Access Control:**
   - Only admins can export compliance reports
   - Consider restricting who can view model metadata in the UI

4. **Data Retention:**
   - Model metadata is subject to the same retention policies as conversation logs
   - Older logs are audited per retention rules and marked for deletion

## Auditor Use Cases

1. **Model Compliance Verification:**
   - "Show me all interactions that used models with `safety_mode == 'strict'`"
   - "Audit all Claude interactions vs. GPT interactions"

2. **Deployment Tracking:**
   - "Which Azure deployments were used in the last month?"
   - "Verify all production interactions used the approved model version"

3. **Configuration Audit:**
   - "Find all interactions with `temperature > 0.8`"
   - "Identify which configs generated high-risk content"

4. **Provider Accountability:**
   - "Generate report of all OpenAI vs. Anthropic usage"
   - "Calculate audit costs by model provider"

## Schema Example

```
tenant_id    | agent_id     | model_provider | model_name      | temperature | safety_mode | ...
-------------|--------------|----------------|-----------------|-------------|-------------|-----
org-123      | agent-ai-01  | openai         | gpt-4-turbo     | 0.7         | strict      | ...
org-123      | agent-ai-02  | anthropic      | claude-3-sonnet | 0.5         | balanced    | ...
org-456      | azure-agent  | azure          | gpt-35-turbo    | 0.6         | relaxed     | ...
```

## FAQ

**Q: What if I don't provide model metadata?**
A: The fields default to `NULL`. Logs are still created and tracked normally.

**Q: Can I update metadata after log creation?**
A: No. Logs are immutable (append-only). Metadata is fixed at log creation time.

**Q: How is `temperature` stored?**
A: As a TEXT field (string) to preserve floating-point precision (e.g., "0.7" vs. 0.7).

**Q: What format is `model_config`?**
A: JSON/JSONB. Examples: `{"top_p": 0.9, "frequency_penalty": 0.5}`.

**Q: Are older logs missing metadata?**
A: Yes. Pre-migration logs will have `NULL` in the new columns. This is expected and does not affect auditing.

## Files Modified/Created

- `models.py` - Added 7 metadata columns to `ConversationAuditLog`
- `schemas.py` - Extended `AuditLogCreate` with metadata fields
- `crud.py` - No changes needed (already uses `**data.dict()`)
- `compliance_export.py` - Updated CSV export to include metadata columns
- `templates/index.html` - Added form fields and table columns for metadata
- `static/main.js` - Updated form handling and table rendering
- `migrations/add_model_metadata.sql` - SQL migration script
- `migrations/apply_model_metadata.py` - Python migration helper
- `test_model_metadata.py` - Unit tests for the feature

## Next Steps

1. **Apply migration** to your database
2. **Restart the application** to load new schema
3. **Test** by creating an audit log with metadata (via UI or API)
4. **Verify** export includes metadata columns
5. **Monitor** logs for any errors during metadata persistence

## Support & Troubleshooting

If you encounter issues:

1. Check PostgreSQL logs for migration errors
2. Verify columns were added: `\d conversation_audit_logs` (in psql)
3. Run `test_model_metadata.py` to validate feature
4. Check browser console for UI errors when creating logs with metadata

---

**Feature Status:** ✅ Implemented and Ready for Production

**Version:** 1.0  
**Release Date:** 2026-01-30  
**Auditor-Critical:** Yes (model-level traceability enabled)
