# Lightweight RBAC Implementation (2 Roles)

## Overview
This document describes the implementation of lightweight role-based access control (RBAC) with two roles: **Admin** and **Viewer**. The system uses route-level access guards without a permission matrix, enabling audit reviewer access with appropriate restrictions.

## Architecture

### 1. Roles Defined
- **Admin**: Full access to all endpoints including user management, retention policies, and admin operations
- **Viewer**: Read-only access to audit logs, PII detection, and compliance export (default role for new users)

### 2. User Model
**File: `models.py`**

```python
class Role(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, unique=True, nullable=False)
    role = Column(SQLEnum(Role), nullable=False, default=Role.VIEWER)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
```

### 3. Authentication & Authorization
**File: `main.py`**

#### Current User Dependency
```python
def get_current_user(
    x_user: Optional[str] = Header(None), 
    db: Session = Depends(get_db)
) -> CurrentUser:
```
- Extracts user from `X-User` header (demo mode)
- In production, replace with JWT validation or session authentication

#### Role Guard Dependency Factory
```python
def require_role(required_role: str):
    async def check_role(current_user: CurrentUser = Depends(get_current_user)):
        # Checks if user has required role
        # Admin can access Viewer routes (hierarchy: Admin > Viewer)
```
- Returns HTTP 403 Forbidden if insufficient permissions
- Admins can access any protected route

### 4. Protected Endpoints

#### Admin-Only Routes
- `POST /admin/retention` - Set retention policies
- `GET /admin/deletion-audits` - View deletion audit trail
- `POST /admin/run-cleanup` - Trigger data cleanup
- `POST /users/create` - Create new users
- `POST /users/{username}/promote` - Promote users to admin

#### Protected but Viewer-Accessible Routes
- `GET /users` - List all users
- `GET /users/me` - Get current user info
- `POST /audit/log` - Create audit logs
- `GET /audit/logs` - View audit logs
- `GET /pii/summary` - View PII detection summary
- `GET /pii/logs` - View PII detection logs
- `GET /compliance/export` - Download compliance package

### 5. User Management API

#### Create User (Admin-only)
```
POST /users/create
{
  "username": "john.doe",
  "role": "viewer"  # or "admin"
}
```

#### List Users
```
GET /users
```
Returns all users with their roles and creation timestamps.

#### Get Current User
```
GET /users/me
```
Returns authenticated user's info.

#### Promote to Admin
```
POST /users/{username}/promote
```
Only admins can promote viewers to admin.

## Frontend Implementation

### 1. Authentication Flow
**File: `static/main.js`**

```javascript
async function initializeAuth() {
    // Load user from localStorage or create demo user
    // Fetch current user info via GET /users/me
    // Update UI with user role
    // Show/hide admin panel based on role
}
```

### 2. Role-Based UI
- **Demo User Auto-Creation**: On first load, creates a demo "viewer" user
- **Admin Panel**: Only visible to admin users
- **Header Display**: Shows current username and role with color-coded badges
  - Admin: Red badge
  - Viewer: Blue badge

### 3. API Calls with Auth
```javascript
function getAuthHeaders() {
    return {
        "Content-Type": "application/json",
        "X-User": currentUser.username  // Pass user in header
    };
}

async function apiCall(endpoint, method = "GET", body = null) {
    const opts = {
        method,
        headers: getAuthHeaders(),
        body: body ? JSON.stringify(body) : null
    };
    return fetch(endpoint, opts);
}
```

### 4. Admin Panel UI
New section added to index.html:
- **Create User Form**: Username and role selection
- **Manage Users Table**: 
  - Shows all users with their roles
  - "Promote to Admin" button for viewer users
  - Admin users display with special styling

## Styling

**File: `static/style.css`**

Added role-specific styles:
```css
.user-role.role-admin { color: #d63a2b; }  /* Red */
.user-role.role-viewer { color: #0066cc; } /* Blue */

.role-badge.admin { background: #ffe5e0; color: #d63a2b; }
.role-badge.viewer { background: #e6f2ff; color: #0066cc; }
```

## Database Schema Changes

### New Table: `users`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

The migration is automatic via SQLAlchemy's `Base.metadata.create_all()`.

## Security Considerations

1. **Header-Based Auth (Demo Mode)**
   - Current implementation uses `X-User` header for simplicity
   - In production, implement proper JWT tokens or session cookies
   - Validate token signature and expiration

2. **Admin Promotion Protection**
   - Only existing admins can create or promote admin users
   - Initial admin must be created via CLI or script

3. **Error Handling**
   - 401 Unauthorized: User not authenticated
   - 403 Forbidden: User authenticated but lacks permission
   - No information leakage in error messages

4. **Rate Limiting**
   - Recommended for production deployment
   - Protect sensitive endpoints like user creation

## Deployment Guide

### Development (Demo Mode)
1. Start the FastAPI server
2. Navigate to dashboard
3. Auto-created demo viewer user will be used
4. Use browser DevTools to set `X-User` header to test different roles

### Production Setup

1. **Create Initial Admin User**
   ```bash
   # Via Python CLI in container
   python -c "
   from crud import create_user
   from database import SessionLocal
   db = SessionLocal()
   create_user(db, 'admin_user', 'admin')
   print('Admin user created')
   "
   ```

2. **Replace Authentication**
   - Update `get_current_user()` in `main.py`
   - Implement JWT validation or session check
   - Store tokens in secure httpOnly cookies

3. **Environment Variables**
   ```bash
   # Add to production config
   AUTH_SECRET_KEY=<long-random-string>
   TOKEN_EXPIRY=3600  # 1 hour
   ```

## Testing

### Test Scenarios

1. **Viewer User Access**
   - ✅ Can view audit logs
   - ✅ Can view PII detections
   - ✅ Can download compliance pack
   - ❌ Cannot create users
   - ❌ Cannot modify retention policy
   - ❌ Cannot access admin panel

2. **Admin User Access**
   - ✅ Can do everything viewers can do
   - ✅ Can create new users
   - ✅ Can promote users to admin
   - ✅ Can manage retention policies
   - ✅ Can access admin panel
   - ✅ Can trigger cleanup

3. **Unauthenticated Access**
   - ❌ Cannot access any protected endpoint
   - Returns 401 Unauthorized

### Running Tests
```bash
# Create test user
curl -X POST http://localhost:8000/users/create \
  -H "X-User: admin_user" \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "role": "viewer"}'

# Try to access admin endpoint as viewer
curl http://localhost:8000/admin/deletion-audits \
  -H "X-User: test_user"
# Should return 403 Forbidden
```

## Future Enhancements

1. **Fine-Grained Permissions**
   - Add permission matrix for specific operations
   - Implement scoped access (e.g., tenant-level permissions)

2. **Audit Logging**
   - Log all user creation, promotion, and permission changes
   - Track who accessed what resources

3. **Session Management**
   - Implement session timeouts
   - Multi-device login management
   - Token refresh mechanisms

4. **Role Hierarchy**
   - Add intermediate roles (e.g., Auditor, Compliance Officer)
   - Define permission inheritance rules

5. **API Rate Limiting**
   - Protect sensitive endpoints from brute force
   - Implement per-user rate limits
