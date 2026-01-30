# RBAC Quick Reference Card

## 🚀 Quick Start

```bash
# Start server
cd /Users/lockyer/Desktop/audit-demo-2
python -m uvicorn main:app --reload

# Visit dashboard
http://localhost:8000

# Demo user auto-created: demo_viewer (role: viewer)
```

---

## 👥 Two Roles

| Role | Access | Use Case |
|------|--------|----------|
| **Viewer** | Audit logs, PII, export (read-only) | Compliance auditors, reviewers |
| **Admin** | Everything + user mgmt, retention, cleanup | System administrators |

---

## 🔐 Authentication

### Header-Based (Demo)
```
X-User: username
```

### Production (Recommended)
Replace with JWT token in `Authorization: Bearer <token>` header.

---

## 📡 Key Endpoints

### User Management
```
POST /users/create          [Admin only]
GET /users                  [Authenticated]
GET /users/me               [Authenticated]
POST /users/{name}/promote  [Admin only]
```

### Admin Operations
```
POST /admin/retention       [Admin only]
GET /admin/deletion-audits  [Admin only]
POST /admin/run-cleanup     [Admin only]
```

### Audit/PII (Authenticated)
```
POST /audit/log             [Authenticated]
GET /audit/logs             [Authenticated]
GET /pii/summary            [Authenticated]
GET /pii/logs               [Authenticated]
GET /compliance/export      [Authenticated]
```

---

## 🛡️ Role Guards

### Syntax
```python
@app.post("/endpoint", dependencies=[Depends(require_role("admin"))])
def handler(...):
    pass
```

### How It Works
1. Route receives request
2. `require_role("admin")` dependency executes
3. Extracts current user from X-User header
4. Checks if user.role == "admin"
5. If False → Returns 403 Forbidden
6. If True → Proceeds to handler

---

## 🎨 Frontend Integration

### Auth Initialization
```javascript
await initializeAuth()
// Loads user, updates UI based on role
```

### API Calls with Auth
```javascript
const resp = await apiCall("/endpoint", "GET")
// Automatically includes X-User header
```

### Show/Hide UI by Role
```javascript
if (currentUser.role === "admin") {
    adminPanel.style.display = "block"
}
```

---

## 📊 Access Control Matrix

```
Endpoint                    Viewer  Admin
────────────────────────    ──────  ──────
POST /audit/log             ✅      ✅
GET /audit/logs             ✅      ✅
GET /pii/*                  ✅      ✅
GET /compliance/export      ✅      ✅
POST /admin/retention       ❌      ✅
GET /admin/deletion-audits  ❌      ✅
POST /admin/run-cleanup     ❌      ✅
POST /users/create          ❌      ✅
POST /users/{}/promote      ❌      ✅
```

---

## 🧪 Quick Tests

### Test Viewer Restriction
```bash
curl http://localhost:8000/admin/deletion-audits \
  -H "X-User: demo_viewer"
# Returns: 403 Forbidden
```

### Test Admin Access
```bash
curl http://localhost:8000/admin/deletion-audits \
  -H "X-User: admin_user"
# Returns: 200 OK with data
```

### Create User (Admin)
```bash
curl -X POST http://localhost:8000/users/create \
  -H "X-User: admin_user" \
  -H "Content-Type: application/json" \
  -d '{"username": "jane.doe", "role": "viewer"}'
```

---

## 🔧 Code Locations

| Feature | File |
|---------|------|
| User model | `models.py:10-20` |
| Auth dependency | `main.py:35-55` |
| Role guard | `main.py:57-75` |
| User endpoints | `main.py:85-130` |
| CRUD functions | `crud.py:15-50` |
| UI initialization | `static/main.js:20-80` |
| Admin panel | `templates/index.html:300-380` |
| Role styling | `static/style.css:1050-1100` |

---

## ⚙️ Configuration

### Demo Mode (Current)
- Uses X-User header
- Auto-creates demo_viewer on first load
- Stored in localStorage

### Production Mode (Needed)
1. Implement JWT in `get_current_user()`
2. Add password hashing to user creation
3. Store tokens in secure cookies
4. Validate token expiration
5. Add rate limiting
6. Enable HTTPS

---

## 🐛 Troubleshooting

### 401 Unauthorized
- Missing X-User header
- User doesn't exist in database
- User not created yet

**Fix:** Include valid X-User header

### 403 Forbidden
- User is Viewer, accessing admin endpoint
- User lacks required role

**Fix:** Use admin user or access allowed endpoint

### Admin Panel Not Showing
- User role is "viewer"
- localStorage not updated

**Fix:** Create admin user or update role

### 404 Not Found
- Wrong endpoint
- Typo in URL

**Fix:** Check endpoint path

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `RBAC_SUMMARY.md` | Overview & key features |
| `RBAC_IMPLEMENTATION.md` | Technical deep dive |
| `RBAC_USAGE.md` | API examples & workflows |
| `RBAC_ARCHITECTURE.md` | System design & diagrams |
| `RBAC_QUICK_REFERENCE.md` | This file |

---

## 🚦 Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | ✅ Proceed |
| 401 | Not authenticated | 🔐 Add X-User header |
| 403 | Forbidden | 👑 Need admin role |
| 404 | Not found | 🔍 Check endpoint |
| 500 | Server error | 🐛 Check logs |

---

## 💡 Best Practices

1. **Always include X-User header** in authenticated requests
2. **Check currentUser.role** before showing admin UI
3. **Use apiCall()** wrapper for consistent auth
4. **Handle 403 errors** gracefully in frontend
5. **Log access attempts** in production
6. **Rotate tokens** regularly
7. **Use HTTPS** in production
8. **Hash passwords** when implemented

---

## 🔄 Typical User Journey

### As Viewer
1. Visit dashboard
2. Auto-created as "demo_viewer"
3. See audit logs, PII, export sections
4. Admin panel NOT visible
5. Cannot access admin endpoints

### As Admin
1. User created with role="admin"
2. See all viewer sections PLUS admin panel
3. Can manage users and settings
4. Can trigger cleanup operations

### Promoting Viewer → Admin
1. Admin opens Admin Panel
2. Finds user in "Manage Users" table
3. Clicks "Promote to Admin"
4. User now has admin access
5. Admin panel appears next login

---

## 📝 Key Files Modified

```
models.py          +14 lines (Role enum, User model)
schemas.py         +20 lines (User schemas)
crud.py           +35 lines (User CRUD)
main.py           +80 lines (Auth, guards, endpoints)
templates/index.html +60 lines (Admin panel)
static/main.js    +120 lines (Auth logic)
static/style.css  +30 lines (Role styling)
```

**Total additions:** ~359 lines of code

---

## 📞 Support

For issues or questions, refer to:
- `RBAC_IMPLEMENTATION.md` for technical details
- `RBAC_USAGE.md` for API examples
- `RBAC_ARCHITECTURE.md` for system design
