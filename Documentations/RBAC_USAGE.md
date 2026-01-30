# RBAC Usage Guide

## Quick Start

### Running the Application

```bash
# Start the server
cd /Users/lockyer/Desktop/audit-demo-2
python -m uvicorn main:app --reload

# Visit in browser
http://localhost:8000
```

### Demo Workflow

#### 1. First Load (Auto-User Creation)
- On first visit, a demo viewer user is automatically created
- Username: `demo_viewer`
- Role: `viewer`
- Stored in browser's localStorage

#### 2. View as Viewer
- See Dashboard, Audit Logs, PII Detection, Risk Reports, Export, Settings
- Admin Panel NOT visible
- Cannot access admin endpoints

#### 3. Manually Test Different Roles
Using browser DevTools Console:

```javascript
// Change user role (demo mode only)
localStorage.setItem("demo_user", "admin_user");
location.reload();

// Then create an admin user via API
```

## API Examples

### Authentication Header
All API calls require the `X-User` header (in demo mode):

```bash
curl http://localhost:8000/users/me \
  -H "X-User: demo_viewer"
```

### User Management

#### List All Users
```bash
curl http://localhost:8000/users \
  -H "X-User: demo_viewer"
```

Response:
```json
[
  {
    "id": "uuid-1",
    "username": "demo_viewer",
    "role": "viewer",
    "created_at": "2026-01-29T10:00:00Z"
  }
]
```

#### Create New User (Admin Only)
```bash
curl -X POST http://localhost:8000/users/create \
  -H "X-User: admin_user" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "role": "viewer"
  }'
```

#### Promote User to Admin (Admin Only)
```bash
curl -X POST http://localhost:8000/users/john.doe/promote \
  -H "X-User: admin_user" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Get Current User Info
```bash
curl http://localhost:8000/users/me \
  -H "X-User: john.doe"
```

Response:
```json
{
  "username": "john.doe",
  "role": "viewer"
}
```

### Protected Admin Endpoints

#### Set Retention Policy
```bash
curl -X POST http://localhost:8000/admin/retention \
  -H "X-User: admin_user" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "org-123",
    "retention_days": 90
  }'
```

#### View Deletion Audits
```bash
curl http://localhost:8000/admin/deletion-audits \
  -H "X-User: admin_user"

# Filter by tenant
curl http://localhost:8000/admin/deletion-audits?tenant_id=org-123 \
  -H "X-User: admin_user"
```

#### Run Cleanup (Demo)
```bash
curl -X POST http://localhost:8000/admin/run-cleanup \
  -H "X-User: admin_user" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Viewer Access to Audits

#### Create Audit Log (Authenticated)
```bash
curl -X POST http://localhost:8000/audit/log \
  -H "X-User: demo_viewer" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "org-123",
    "agent_id": "agent-001",
    "session_id": "sess-abc123",
    "channel": "web",
    "prompt": "What is compliance?",
    "response": "Compliance is...",
    "model_info": "gpt-4"
  }'
```

#### Get Audit Logs
```bash
curl http://localhost:8000/audit/logs?tenant_id=org-123 \
  -H "X-User: demo_viewer"
```

### Error Responses

#### Unauthorized (Missing X-User)
```bash
curl http://localhost:8000/users/me
```

Response: `401 Unauthorized - "Not authenticated"`

#### Forbidden (Insufficient Permissions)
```bash
curl -X POST http://localhost:8000/admin/retention \
  -H "X-User: demo_viewer" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "org-123", "retention_days": 90}'
```

Response: `403 Forbidden - "Insufficient permissions. Required role: admin"`

## UI Navigation

### Dashboard (All Users)
- KPI cards with compliance metrics
- Recent activity timeline
- Overview of system health

### Audit Logs (Viewers)
- Create new audit logs
- Query and view logs by tenant
- Search across audit trail

### PII Detection (Viewers)
- View PII detection summary
- Filter by risk level
- Review detected sensitive data
- View NER API responses

### Risk Reports (Viewers)
- View identified risks
- Risk severity tracking
- Recommendations

### Export (Viewers)
- Download compliance package
- ZIP contains:
  - Conversation logs (CSV)
  - PII detection logs (CSV)
  - Retention policy (JSON)
  - Metadata (JSON)

### Settings (Viewers)
- View current retention policy
- View deletion audit trail (no modify)

### Admin Panel (Admins Only)
- Create new users
- Manage users (list, promote)
- Set retention policies
- View deletion audits
- Trigger cleanup

## Browser Storage

### localStorage
```javascript
// Demo user stored in localStorage
localStorage.getItem("demo_user")  // Returns: "demo_viewer"

// Change for testing (demo mode)
localStorage.setItem("demo_user", "admin_user");
```

## Session Management (Demo Mode)

The demo implementation:
1. Checks localStorage for `demo_user`
2. If exists, loads that user
3. If not, creates `demo_viewer` automatically
4. Session persists across page reloads
5. Clear localStorage to reset

To reset:
```javascript
localStorage.clear();
location.reload();
```

## Testing Role-Based Access

### Test Viewer Restrictions
```bash
# Create viewer user
curl -X POST http://localhost:8000/users/create \
  -H "X-User: admin_user" \
  -d '{"username": "test_viewer", "role": "viewer"}'

# Try to access admin endpoint (should fail)
curl http://localhost:8000/admin/deletion-audits \
  -H "X-User: test_viewer"
# Response: 403 Forbidden
```

### Test Admin Promotion
```bash
# Promote viewer to admin
curl -X POST http://localhost:8000/users/test_viewer/promote \
  -H "X-User: admin_user" \
  -d '{}'

# Now viewer can access admin endpoints
curl http://localhost:8000/admin/deletion-audits \
  -H "X-User: test_viewer"
# Response: 200 OK with data
```

## Production Checklist

- [ ] Replace `X-User` header auth with JWT tokens
- [ ] Implement `get_current_user()` with token validation
- [ ] Store tokens in secure httpOnly cookies
- [ ] Add token refresh mechanism
- [ ] Set up password hashing (bcrypt)
- [ ] Configure HTTPS/TLS
- [ ] Add CORS settings
- [ ] Implement rate limiting
- [ ] Set up audit logging
- [ ] Configure database encryption
- [ ] Create admin user via secure setup script
- [ ] Test all role-based access restrictions
