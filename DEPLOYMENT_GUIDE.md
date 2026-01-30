# Model Metadata Feature - Deployment & Verification Guide

## Pre-Deployment Checklist

- [ ] Code changes reviewed and merged to `main` branch
- [ ] All files compiled/linted (Python syntax check)
- [ ] Database backup created
- [ ] Staging environment available for testing
- [ ] Team notified of upcoming deployment

## Deployment Steps

### 1. Backup Database

```bash
# PostgreSQL backup
pg_dump -U postgres compliance_db > backup_compliance_db_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Apply Database Migration

**Option A: Python Helper (Recommended)**
```bash
cd /Users/lockyer/Desktop/audit-demo-2
python migrations/apply_model_metadata.py
```

**Option B: Direct SQL**
```bash
psql -U postgres -d compliance_db -f migrations/add_model_metadata.sql
```

### 3. Restart Application

```bash
# If using Docker
docker compose down
docker compose up --build

# If using manual Python
pkill -f "uvicorn main:app"
uvicorn main:app --reload
```

### 4. Verify Migration Success

Connect to database and verify columns exist:

```sql
-- In PostgreSQL
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'conversation_audit_logs'
ORDER BY ordinal_position;
```

Expected output should include:
```
model_provider    | text         | YES
model_name        | text         | YES
model_version     | text         | YES
deployment_id     | text         | YES
temperature       | text         | YES
safety_mode       | text         | YES
model_config      | jsonb        | YES
```

## Post-Deployment Verification

### 1. API Test: Create Log with Metadata

```bash
curl -X POST http://localhost:8000/audit/log \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-org",
    "agent_id": "test-agent",
    "session_id": "test-session",
    "channel": "api",
    "prompt": "Hello",
    "response": "Hi there",
    "model_info": "gpt-4-turbo",
    "model_provider": "openai",
    "model_name": "gpt-4-turbo",
    "model_version": "2024-04-09",
    "temperature": "0.7",
    "safety_mode": "strict",
    "model_config": {"top_p": 0.9}
  }'
```

Expected response:
```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-30T10:30:00.000000"
}
```

### 2. Database Verification

```sql
-- Verify data was persisted
SELECT 
  id, 
  model_provider, 
  model_name, 
  temperature, 
  safety_mode 
FROM conversation_audit_logs 
WHERE tenant_id = 'test-org'
ORDER BY timestamp DESC
LIMIT 1;
```

### 3. UI Verification

1. **Open Dashboard:** http://localhost:8000
2. **Go to Audit Logs tab**
3. **Create New Audit Log:**
   - Fill in basic fields (Tenant, Agent, Session, Channel, Prompt, Response)
   - Scroll down to "Model Metadata (Optional)" section
   - Fill in: Model Provider, Model Name, Temperature, Safety Mode
   - Click "Create Log"
4. **Fetch Logs:**
   - Click "Fetch Logs"
   - Verify new log appears in table
   - Check that "Model Provider" and "Model Name" columns are populated

### 4. Export Verification

1. **Navigate to Export tab (admin only)**
2. **Enter tenant ID:** `test-org`
3. **Download Compliance Export**
4. **Extract ZIP and verify:**
   ```bash
   unzip compliance_export_test-org_*.zip
   head -1 conversation_logs.csv
   ```
   
   Expected header row should include:
   ```
   ...,Model Info,Model Provider,Model Name,Model Version,Deployment ID,Temperature,Safety Mode,Model Config
   ```

### 5. Run Unit Tests

```bash
cd /Users/lockyer/Desktop/audit-demo-2
python test_model_metadata.py
```

Expected output:
```
======================================================================
Model Metadata Logging Feature - Unit Tests
======================================================================

[TEST] Creating audit log with model metadata...
[PASS] Audit log metadata validation passed

[TEST] Creating audit log with Azure deployment ID...
[PASS] Azure deployment metadata validation passed

[TEST] Creating audit log with minimal/missing metadata...
[PASS] Minimal metadata validation passed (backwards compatible)

[TEST] Verifying export CSV headers include metadata...
[PASS] Export includes all 7 metadata columns

[TEST] Filtering logs by model provider for compliance audit...
[PASS] Metadata filtering for compliance reporting works correctly

======================================================================
Test Results: 5 passed, 0 failed
======================================================================
```

## Monitoring & Alerts

### 1. Application Logs

Monitor for errors during metadata persistence:

```bash
# Check Docker logs
docker logs audit-api | grep -i "model_metadata\|error\|traceback"
```

### 2. Database Slow Queries

Monitor if metadata columns impact query performance:

```sql
-- Check query performance
EXPLAIN ANALYZE
SELECT * FROM conversation_audit_logs 
WHERE model_provider = 'openai'
LIMIT 10;
```

### 3. Metrics to Track

- **Logs with metadata:** Count of logs where `model_provider IS NOT NULL`
- **Missing metadata:** Count of logs where `model_provider IS NULL` (should decrease over time)
- **Query latency:** Ensure audit log queries remain < 100ms
- **Export size:** Monitor if CSV exports increase significantly

## Rollback Plan (If Issues Occur)

### Scenario 1: Migration Failed

**Recovery:**
```bash
# Restore from backup
psql -U postgres compliance_db < backup_compliance_db_YYYYMMDD_HHMMSS.sql

# Restart app
docker compose down
docker compose up
```

### Scenario 2: Application Crash Due to New Code

**Recovery:**
```bash
# Revert code to previous version
git checkout HEAD~1

# Rebuild and restart
docker compose down
docker compose up --build
```

### Scenario 3: Columns Added but Code Not Ready

**Recovery:**
Drop the columns (only if absolutely necessary):
```sql
ALTER TABLE conversation_audit_logs
DROP COLUMN IF EXISTS model_provider,
DROP COLUMN IF EXISTS model_name,
DROP COLUMN IF EXISTS model_version,
DROP COLUMN IF EXISTS deployment_id,
DROP COLUMN IF EXISTS temperature,
DROP COLUMN IF EXISTS safety_mode,
DROP COLUMN IF EXISTS model_config;
```

## Success Criteria

✅ Deployment is **successful** when:

1. ✅ Database migration applies without errors
2. ✅ Application starts without errors
3. ✅ API accepts metadata fields in log creation
4. ✅ Metadata is persisted in database
5. ✅ UI shows metadata form fields and table columns
6. ✅ Compliance export includes metadata columns
7. ✅ Unit tests all pass
8. ✅ No increase in error rate or latency

## Timeline

| Phase | Duration | Owner |
|-------|----------|-------|
| Backup | 5 min | DBA |
| Migration | 5 min | DBA |
| Restart App | 5 min | DevOps |
| Verification Tests | 10 min | QA |
| Monitoring Setup | 5 min | DevOps |
| **Total** | **~30 min** | Team |

## Sign-Off

- [ ] Database Administrator: Migration successful
- [ ] DevOps: Application restarted and healthy
- [ ] QA: All verification tests passed
- [ ] Product Manager: Feature ready for production use

---

**Last Updated:** 2026-01-30  
**Feature:** Model Metadata Logging v1.0  
**Environment:** Production Ready
