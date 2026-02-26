# Admin Portal Implementation Plan

## Overview

Build a professional admin dashboard for InterviewPrep with separate username/password authentication. Admin can manage users, questions, view audit logs, and monitor platform health.

---

## Phase 1: Backend Setup (Admin Model & Auth)

### 1.1 Database Schema Changes

**New Table: `admin_accounts`**

```sql
CREATE TABLE admin_accounts (
    id INTEGER PRIMARY KEY
    username VARCHAR(50) UNIQUE NOT NULL
    password_hash VARCHAR(255) NOT NULL
    full_name VARCHAR(255) NULLABLE
    is_active BOOLEAN DEFAULT true
    created_at TIMESTAMP DEFAULT NOW()
    last_login TIMESTAMP NULLABLE
)
```

**Update Existing: `users` table**

```sql
ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN ban_reason VARCHAR(500) NULLABLE;
ALTER TABLE users ADD COLUMN banned_at TIMESTAMP NULLABLE;
```

**Update: `audit_logs` table** (if needed)

- Ensure it captures: `admin_id`, `action`, `target_type`, `target_id`, `metadata`, `timestamp`

### 1.2 Models

**File:** `backend/app/models/admin.py` (NEW)

```python
from sqlalchemy import DateTime, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AdminAccount(Base):
    __tablename__ = "admin_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Update:** `backend/app/models/user.py`

```python
# Add to User model:
is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
ban_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
banned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 1.3 CRUD Operations

**File:** `backend/app/crud/admin.py` (NEW)

```python
def create_admin(db: Session, username: str, password: str, full_name: str | None = None) -> AdminAccount
def get_admin_by_username(db: Session, username: str) -> AdminAccount | None
def authenticate_admin(db: Session, username: str, password: str) -> AdminAccount | None
def update_admin_last_login(db: Session, admin_id: int)
def get_all_admins(db: Session) -> list[AdminAccount]
def deactivate_admin(db: Session, admin_id: int)
```

**File:** `backend/app/crud/user.py` (UPDATE)

```python
def ban_user(db: Session, user_id: int, reason: str | None = None) -> User
def unban_user(db: Session, user_id: int) -> User
def get_all_users_paginated(db: Session, skip: int = 0, limit: int = 50, filter_banned: bool = False) -> list[User]
```

### 1.4 Schemas (DTOs)

**File:** `backend/app/schemas/admin.py` (NEW)

```python
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    admin_id: int
    username: str

class AdminCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str | None = None

class AdminResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    last_login: datetime | None

class UserBanRequest(BaseModel):
    reason: str | None = None

class UserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_verified: bool
    is_banned: bool
    ban_reason: str | None
    banned_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

### 1.5 Security & JWT

**Update:** `backend/app/core/security.py`

```python
def create_admin_access_token(admin_id: int, username: str) -> str:
    # Same JWT, but payload includes admin_id and role="admin"
    payload = {
        "sub": str(admin_id),
        "username": username,
        "role": "admin",
        "type": "admin_token",
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_admin_token(token: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return payload
```

### 1.6 Dependencies

**File:** `backend/app/api/deps.py` (UPDATE)

```python
def get_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AdminAccount:
    payload = verify_admin_token(token)
    admin_id = int(payload.get("sub"))
    admin = db.query(AdminAccount).filter(AdminAccount.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account inactive or invalid")
    return admin
```

### 1.7 Endpoints

**File:** `backend/app/api/v1/admin.py` (NEW)

```python
router = APIRouter(prefix="/admin", tags=["admin"])

# Authentication
@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = authenticate_admin(db, payload.username, payload.password)
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    update_admin_last_login(db, admin.id)
    token = create_admin_access_token(admin.id, admin.username)
    return AdminLoginResponse(
        access_token=token,
        admin_id=admin.id,
        username=admin.username
    )

# User Management
@router.get("/users", response_model=list[UserDetailResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    filter_banned: bool = False,
    admin: AdminAccount = Depends(get_admin),
    db: Session = Depends(get_db)
):
    users = get_all_users_paginated(db, skip=skip, limit=limit, filter_banned=filter_banned)
    log_audit(db, "admin_list_users", user_id=None, admin_id=admin.id, metadata={"skip": skip, "limit": limit})
    return users

@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    user_id: int,
    admin: AdminAccount = Depends(get_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    log_audit(db, "admin_view_user", user_id=user_id, admin_id=admin.id)
    return user

@router.post("/users/{user_id}/ban")
def ban_user_endpoint(
    user_id: int,
    payload: UserBanRequest,
    admin: AdminAccount = Depends(get_admin),
    db: Session = Depends(get_db)
):
    user = ban_user(db, user_id, payload.reason)
    log_audit(db, "admin_ban_user", user_id=user_id, admin_id=admin.id, metadata={"reason": payload.reason})
    return {"ok": True, "message": f"User {user.email} banned"}

@router.post("/users/{user_id}/unban")
def unban_user_endpoint(
    user_id: int,
    admin: AdminAccount = Depends(get_admin),
    db: Session = Depends(get_db)
):
    user = unban_user(db, user_id)
    log_audit(db, "admin_unban_user", user_id=user_id, admin_id=admin.id)
    return {"ok": True, "message": f"User {user.email} unbanned"}

# Dashboard Stats
@router.get("/stats")
def get_dashboard_stats(
    admin: AdminAccount = Depends(get_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    banned_users = db.query(User).filter(User.is_banned == True).count()
    active_interviews = db.query(InterviewSession).filter(InterviewSession.status == "in_progress").count()
    total_questions = db.query(Question).count()

    log_audit(db, "admin_view_stats", user_id=None, admin_id=admin.id)

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "banned_users": banned_users,
        "active_interviews": active_interviews,
        "total_questions": total_questions,
        "timestamp": datetime.utcnow()
    }

# Audit Logs
@router.get("/audit-logs")
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    admin: AdminAccount = Depends(get_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs
```

### 1.8 CLI Command for Admin Creation

**File:** `backend/scripts/create_admin.py` (NEW)

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.admin import AdminAccount

def create_admin(username: str, password: str, full_name: str = None):
    db = SessionLocal()
    try:
        existing = db.query(AdminAccount).filter(AdminAccount.username == username).first()
        if existing:
            print(f"✗ Admin '{username}' already exists")
            return False

        admin = AdminAccount(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✓ Admin '{username}' created successfully (ID: {admin.id})")
        return True
    except Exception as e:
        print(f"✗ Error creating admin: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password> [full_name]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else None

    create_admin(username, password, full_name)
```

**Usage:**

```bash
python backend/scripts/create_admin.py admin123 securepassword123 "Your Name"
```

### 1.9 Database Migration

**Create migration:**

```bash
cd backend
alembic revision --autogenerate -m "add admin authentication and user banning"
alembic upgrade head
```

---

## Phase 2: Frontend Setup (Admin Dashboard)

### 2.1 Routes & Layout

**File:** `frontend-next/src/app/admin/layout.tsx` (NEW)

- Admin layout with sidebar navigation
- Protect routes with `AdminGuard` component

**File:** `frontend-next/src/app/admin/page.tsx` (NEW)

- Admin login page

**Routes:**

```
/admin              → Login (public)
/admin/dashboard    → Dashboard (protected)
/admin/users        → User management (protected)
/admin/questions    → Question management (protected)
/admin/audit-logs   → Audit logs (protected)
```

### 2.2 Authentication

**File:** `frontend-next/src/lib/stores/adminStore.ts` (NEW)

```typescript
export const useAdminStore = create((set) => ({
  admin_token: localStorage.getItem("admin_token") || null,
  admin_id: null,
  username: null,

  login: async (username: string, password: string) => {
    // POST /admin/login
    // Save token + admin info
  },

  logout: () => {
    // Clear localStorage
  },

  isAuthenticated: () => !!admin_token,
}));
```

**File:** `frontend-next/src/components/AdminGuard.tsx` (NEW)

- Redirect to `/admin` if not authenticated

### 2.3 Components

**Dashboard:**

- Stats cards (total users, verified, banned, active interviews)
- Quick actions (ban user, add question)
- Recent audit logs

**User Management:**

- Table of all users
- Search/filter (verified, banned, email, name)
- Actions: View detail, Ban, Unban, Reset password (future)
- Pagination

**Audit Logs:**

- Timeline of all admin actions
- Filter by admin, action type, date range
- Search

---

## Phase 3: Implementation Steps

### Step 1: Database & Models

- [ ] Create Alembic migration
- [ ] Add AdminAccount model
- [ ] Update User model with ban fields
- [ ] Update audit_log schema

### Step 2: Backend CRUD & Security

- [ ] Implement admin CRUD functions
- [ ] Update security module with admin JWT
- [ ] Create admin dependencies

### Step 3: Backend Endpoints

- [ ] Admin login endpoint
- [ ] User listing/detail endpoints
- [ ] Ban/unban endpoints
- [ ] Dashboard stats endpoint
- [ ] Audit log endpoints

### Step 4: CLI Tool

- [ ] Create `create_admin.py` script
- [ ] Test locally

### Step 5: Frontend Auth

- [ ] Create admin store
- [ ] Admin login page
- [ ] AdminGuard component

### Step 6: Frontend Pages

- [ ] Dashboard page
- [ ] User management page
- [ ] Audit logs page
- [ ] Layout/navigation

### Step 7: Testing & Deployment

- [ ] Test locally
- [ ] Create admin user in production
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] End-to-end testing

---

## Development Checklist

### Backend

```
Models:
- [ ] AdminAccount model
- [ ] User model (add is_banned, ban_reason, banned_at)
- [ ] AuditLog enhancement

CRUD:
- [ ] admin.py (create, get, authenticate, list, deactivate)
- [ ] user.py (ban, unban, list with filters)

Schemas:
- [ ] admin.py (login, response, create, ban request)
- [ ] user.py (detail with ban fields)

Security:
- [ ] create_admin_access_token
- [ ] verify_admin_token

Routes:
- [ ] /admin/login (POST)
- [ ] /admin/users (GET) - list
- [ ] /admin/users/{id} (GET) - detail
- [ ] /admin/users/{id}/ban (POST)
- [ ] /admin/users/{id}/unban (POST)
- [ ] /admin/stats (GET)
- [ ] /admin/audit-logs (GET)

CLI:
- [ ] create_admin.py script

Migration:
- [ ] Run alembic migration
```

### Frontend

```
Store:
- [ ] adminStore.ts (login, logout, token, user info)

Components:
- [ ] AdminGuard (route protection)
- [ ] AdminLayout (sidebar, header)
- [ ] UserTable (list, sort, filter, paginate)
- [ ] UserDetail (modal or page)
- [ ] AuditLogTimeline
- [ ] StatsCards

Pages:
- [ ] /admin (login)
- [ ] /admin/dashboard (stats, quick actions)
- [ ] /admin/users (user management)
- [ ] /admin/audit-logs (logs viewer)

API:
- [ ] adminService.ts (login, getUsers, banUser, getStats, getAuditLogs)
```

---

## Timeline

- Phase 1 (Backend): ~2-3 hours
- Phase 2 (Frontend): ~2-3 hours
- Phase 3 (Testing & Deploy): ~1 hour

**Total: ~6 hours of focused work**

---

## Security Considerations

- ✅ Admin token separate from user token (role-based)
- ✅ Require is_active check for admin
- ✅ All admin actions logged to audit_log
- ✅ Admin password hashed with argon2
- ✅ Token expiry: 24 hours (shorter than user)
- ✅ Rate limit admin login attempts
- ⚠️ TODO: IP whitelisting (future)
- ⚠️ TODO: 2FA (future)

---

## Success Criteria

- [ ] Admin can login with username/password
- [ ] Admin sees dashboard with accurate stats
- [ ] Admin can view all users with details
- [ ] Admin can ban/unban users
- [ ] All admin actions logged in audit_log
- [ ] Admin session expires after 24 hours
- [ ] Frontend/backend deployed and working in production
