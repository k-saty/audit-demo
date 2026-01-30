# RBAC Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React/Vanilla JS)          │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │           UI Based on User Role                    │  │
│  │  ┌──────────────────┬──────────────────────┐      │  │
│  │  │  Viewer UI       │  Admin UI             │      │  │
│  │  │  - Dashboard     │  - User Management    │      │  │
│  │  │  - Audit Logs    │  - Role Assignment    │      │  │
│  │  │  - PII Detection │  - Retention Config   │      │  │
│  │  │  - Export        │  - Cleanup Triggers   │      │  │
│  │  └──────────────────┴──────────────────────┘      │  │
│  └────────────────────────────────────────────────────┘  │
│                            ↓                               │
│  ┌────────────────────────────────────────────────────┐  │
│  │        API Calls with X-User Header                │  │
│  │   { "X-User": "username" }                         │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
           ↓↓↓ HTTP Request ↓↓↓
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend                             │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │    HTTP Request with X-User Header                 │  │
│  └────────────────────────────────────────────────────┘  │
│                      ↓                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │    Dependency Injection Layer                       │  │
│  │                                                     │  │
│  │  get_current_user()                                │  │
│  │  ├─ Extract X-User header                          │  │
│  │  ├─ Query database for user                        │  │
│  │  └─ Return CurrentUser object with role            │  │
│  └────────────────────────────────────────────────────┘  │
│                      ↓                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │    Role Guard (require_role)                        │  │
│  │                                                     │  │
│  │  require_role("admin")                             │  │
│  │  ├─ Check current_user.role == "admin"             │  │
│  │  ├─ If NO → 403 Forbidden                          │  │
│  │  └─ If YES → Continue to route handler             │  │
│  └────────────────────────────────────────────────────┘  │
│                      ↓                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │    Route Handler (with full authorization)         │  │
│  │                                                     │  │
│  │  @app.post("/admin/retention")                     │  │
│  │  def admin_set_retention(...):                      │  │
│  │      # Only admins reach here                       │  │
│  │      set_retention_for_tenant(...)                 │  │
│  └────────────────────────────────────────────────────┘  │
│                      ↓                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Database Layer (SQLAlchemy)                │  │
│  │                                                     │  │
│  │  - Users table (id, username, role)                │  │
│  │  - All other existing tables                       │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
           ↓↓↓ Response ↓↓↓
┌─────────────────────────────────────────────────────────┐
│              Frontend Receives Response                  │
│           (200, 403, or 401 Status Code)               │
└─────────────────────────────────────────────────────────┘
```

## Request Flow: Accessing Admin Endpoint

```
Viewer User (demo_viewer)
    ↓
[1] GET /admin/deletion-audits
    Header: X-User: demo_viewer
    ↓
[2] FastAPI Routes to Handler
    ↓
[3] Dependencies Executed:
    - get_db()
    - require_role("admin")
      - get_current_user()
        - Extract X-User header → "demo_viewer"
        - Query Users table → role = "viewer"
        - Return CurrentUser(username="demo_viewer", role="viewer")
      - Check: role == "admin"? → FALSE
      - Raise HTTPException(status_code=403)
    ↓
[4] Response: 403 Forbidden
    {
      "detail": "Insufficient permissions. Required role: admin"
    }
    ↓
[5] Frontend Displays Error
    "Only admins can access this"
```

## Request Flow: Accessing Admin Endpoint (Admin User)

```
Admin User (admin_user)
    ↓
[1] POST /admin/retention
    Header: X-User: admin_user
    Body: {
      "tenant_id": "org-123",
      "retention_days": 90
    }
    ↓
[2] FastAPI Routes to Handler
    ↓
[3] Dependencies Executed:
    - get_db() → SessionLocal()
    - require_role("admin")
      - get_current_user()
        - Extract X-User header → "admin_user"
        - Query Users table → role = "admin"
        - Return CurrentUser(username="admin_user", role="admin")
      - Check: role == "admin"? → TRUE
      - Return current_user (allow to proceed)
    ↓
[4] Handler Executes:
    admin_set_retention(
        payload=RetentionUpdate(...),
        db=Session,
        dependencies=[admin_guard_result]
    )
    → set_retention_for_tenant(db, "org-123", 90)
    → db.commit()
    ↓
[5] Response: 200 OK
    {
      "tenant_id": "org-123",
      "retention_days": 90
    }
    ↓
[6] Frontend Displays Success
    "✓ Retention saved for org-123: 90 days"
```

## User Model Structure

```
┌──────────────────────────────────────┐
│          Users Table                 │
├──────────────────────────────────────┤
│ id (UUID, PK)                        │
│ username (TEXT, UNIQUE)              │
│ role (ENUM: admin, viewer)           │
│ created_at (TIMESTAMP)               │
└──────────────────────────────────────┘

Sample Data:
┌─────────────────────────────┬────────┐
│ username                    │ role   │
├─────────────────────────────┼────────┤
│ demo_viewer                 │ viewer │
│ john.doe                    │ viewer │
│ jane.smith                  │ admin  │
│ compliance_manager          │ admin  │
└─────────────────────────────┴────────┘
```

## Authentication Flow (Demo Mode)

```
User Visits Dashboard
    ↓
[1] DOMContentLoaded Event
    ↓
[2] initializeAuth()
    ├─ Check localStorage("demo_user")
    │  ├─ If exists → username = stored value
    │  └─ If not → username = "demo_viewer"
    ├─ Try: GET /users/me with X-User header
    │  ├─ If 200 OK → Load user from response
    │  └─ If 401 → User doesn't exist
    └─ If user doesn't exist:
       ├─ POST /users/create
       │  └─ Create "demo_viewer" with role="viewer"
       └─ Update UI with user info
    ↓
[3] currentUser = {
      username: "demo_viewer",
      role: "viewer"
    }
    ↓
[4] UI Initialization
    ├─ Show user name in header
    ├─ Show role badge (colored)
    ├─ Show/Hide Admin Panel (based on role)
    └─ All future API calls use getAuthHeaders()
    ↓
[5] User Can Now Interact
    └─ All API calls include X-User header
       from currentUser.username
```

## Role Permission Hierarchy

```
┌────────────────────────────┐
│     Permission Hierarchy   │
├────────────────────────────┤
│                            │
│        ┌────────────┐      │
│        │   Admin    │      │
│        │ (Level 2)  │      │
│        └─────┬──────┘      │
│              │             │
│         [CAN ACCESS]       │
│              │             │
│        ┌─────▼──────┐      │
│        │  Viewer    │      │
│        │ (Level 1)  │      │
│        └────────────┘      │
│                            │
│   Permission Matrix:       │
│   ┌──────────┬────┬───┐   │
│   │Endpoint  │View│Adm│   │
│   ├──────────┼────┼───┤   │
│   │/audit/..│ ✅ │ ✅ │   │
│   │/pii/...│ ✅ │ ✅ │   │
│   │/admin/..│ ❌ │ ✅ │   │
│   │/users/..│ ⚠️ │ ✅ │   │
│   └──────────┴────┴───┘   │
│                            │
└────────────────────────────┘
```

## Dependency Injection Chain

```
FastAPI Route Handler
    ↓
@app.post("/admin/retention", 
          dependencies=[Depends(require_role("admin"))])
def admin_set_retention(
    payload: RetentionUpdate,
    db: Session = Depends(get_db),
):
    ↓
Dependency Resolution Chain:
    ↓
[1] Depends(get_db)
    └─ Return SessionLocal() database session
    ↓
[2] Depends(require_role("admin"))
    └─ Inner function requires: get_current_user()
       └─ get_current_user requires:
          ├─ x_user: str from Header(None)
          └─ db: Session from Depends(get_db)
             └─ (Session already resolved)
       └─ Extract user from header
       └─ Query database for user object
       └─ Return CurrentUser(username, role)
    └─ Check user.role == "admin"
    └─ If False → raise 403
    └─ If True → Continue
    ↓
[3] Handler Executes with:
    - payload (from body)
    - db (from dependency)
    - All guards passed
```

## UI State Management

```
┌─────────────────────────────────────────┐
│      Global JavaScript State            │
├─────────────────────────────────────────┤
│                                         │
│  let currentUser = {                    │
│    username: string,                    │
│    role: "admin" | "viewer"             │
│  }                                      │
│                                         │
│  Functions:                             │
│  - getAuthHeaders()                     │
│    └─ Returns headers with X-User       │
│                                         │
│  - apiCall(endpoint, method, body)      │
│    └─ fetch() with auth headers         │
│                                         │
│  - initializeAuth()                     │
│    └─ Load user from API, update UI     │
│                                         │
│  UI Update Logic:                       │
│  - Show/hide admin panel                │
│  - Update user name display             │
│  - Set role badge color                 │
│  - Disable admin buttons for viewers    │
│                                         │
└─────────────────────────────────────────┘
```

## Error Response Examples

```
1. Unauthenticated (401)
──────────────────────
curl http://localhost:8000/users/me
Response:
{
  "detail": "Not authenticated"
}
Status: 401 Unauthorized

2. Insufficient Permissions (403)
──────────────────────────────────
curl http://localhost:8000/admin/retention \
  -H "X-User: demo_viewer" \
  -d '{"tenant_id": "test", "retention_days": 90}'
Response:
{
  "detail": "Insufficient permissions. Required role: admin"
}
Status: 403 Forbidden

3. User Not Found (401)
──────────────────────
curl http://localhost:8000/users/me \
  -H "X-User: nonexistent_user"
Response:
{
  "detail": "User not found"
}
Status: 401 Unauthorized
```

## Summary Table: Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Role Enum | `models.py` | Define admin/viewer roles |
| User Model | `models.py` | Store user data with roles |
| get_current_user | `main.py` | Extract & validate user from header |
| require_role | `main.py` | Role guard factory for routes |
| User Endpoints | `main.py` | User CRUD operations |
| CRUD Functions | `crud.py` | Database user operations |
| Auth Schemas | `schemas.py` | Pydantic models for auth |
| User Management UI | `index.html` | Admin panel section |
| Auth Logic | `main.js` | Frontend auth initialization |
| API Wrapper | `main.js` | apiCall() with auth headers |
| Role Styling | `style.css` | Role badge colors & display |
