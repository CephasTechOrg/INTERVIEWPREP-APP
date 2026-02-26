# Admin Portal Testing & Verification

## Deployment Status

### Backend (https://interviq-backend.onrender.com)

- ✅ Health check: `/health` returns `{"status":"ok"}`
- ✅ Admin router: 8 routes registered successfully
- ✅ Database migrations: Applied (admin_accounts table created, user ban fields added)
- ⏳ Admin endpoints: Deploying (may take 2-5 minutes on Render)

### Frontend (https://interviq-frontend.onrender.com)

- ✅ Main app: Loading successfully
- ✅ TypeScript: No compilation errors
- ⏳ Admin routes: Deploying (may take 2-5 minutes on Render)

---

## Backend Testing Checklist

### 1. Admin Login Endpoint

```bash
curl -X POST https://interviq-backend.onrender.com/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin123","password":"securepassword123"}'
```

**Expected Response:**

```json
{
  "access_token": "eyJ...",
  "admin_id": 1,
  "username": "admin123",
  "full_name": "Admin User"
}
```

### 2. Dashboard Stats (requires admin token)

```bash
curl -X GET https://interviq-backend.onrender.com/api/v1/admin/stats \
  -H "Authorization: Bearer <TOKEN>"
```

### 3. List Users

```bash
curl -X GET https://interviq-backend.onrender.com/api/v1/admin/users \
  -H "Authorization: Bearer <TOKEN>"
```

### 4. Ban User

```bash
curl -X POST https://interviq-backend.onrender.com/api/v1/admin/users/1/ban \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"reason":"Violating terms of service"}'
```

### 5. Get Audit Logs

```bash
curl -X GET https://interviq-backend.onrender.com/api/v1/admin/audit-logs \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Frontend Testing Checklist

### 1. Admin Login Page

- Navigate to: `https://interviq-frontend.onrender.com/admin`
- Should see: Username and password form
- Try login with:
  - Username: `admin123`
  - Password: `securepassword123`

### 2. Dashboard

- Navigate to: `https://interviq-frontend.onrender.com/admin/dashboard`
- Should see: 5 stat cards
  - Total Users
  - Verified Users
  - Banned Users
  - Active Interviews
  - Total Questions

### 3. User Management

- Navigate to: `https://interviq-frontend.onrender.com/admin/users`
- Should see: User table with columns (email, name, verified, status, joined, actions)
- Features to test:
  - Filter by status (All/Active/Banned)
  - Pagination (Previous/Next)
  - Ban button (should open modal)
  - Unban button

### 4. Audit Logs

- Navigate to: `https://interviq-frontend.onrender.com/admin/audit-logs`
- Should see: Log entries with action, admin ID, timestamp
- Features: Pagination

### 5. Logout

- Click logout in sidebar
- Should redirect to `/admin` (login page)

---

## Common Issues & Solutions

### Issue: Admin endpoint returns 404

**Solution:** Backend still deploying. Render deployments take 2-5 minutes. Check:

- Git push was successful
- Alembic migrations ran
- Check Render logs: `alembic upgrade head` appears in logs

### Issue: Frontend shows 404 on `/admin` path

**Solution:** Frontend still deploying. Routes may not be built yet. Try:

- Hard refresh (Ctrl+Shift+R)
- Check browser console for errors
- Wait 2-5 minutes for Render to build and deploy

### Issue: Login fails with "Invalid credentials"

**Possible causes:**

1. Admin account wasn't created (run: `python backend/scripts/create_admin.py admin123 securepassword123`)
2. Database not synced between local and production
3. Admin table not created (migration didn't run)

### Issue: Admin can login but dashboard shows "Failed to load stats"

**Solution:** Check browser console for error. Likely causes:

- Backend still deploying
- API URL incorrect (check adminService.ts uses correct URL)
- Token format incorrect
- CORS issue

---

## Render Deployment Commands

If you need to redeploy:

```bash
# Backend redeploy (auto on git push)
git push origin main

# Check logs
# Go to Render Dashboard > interviq-backend > Logs tab

# To manually redeploy:
# Render Dashboard > interviq-backend > Manual Deploy > Deploy latest commit
```

---

## Local Testing (Before Production)

### 1. Start Backend

```bash
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Create Admin Account

```bash
python backend/scripts/create_admin.py testadmin testpass123 "Test Admin"
```

### 3. Test Admin Login Locally

```bash
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testadmin","password":"testpass123"}'
```

### 4. Start Frontend

```bash
cd frontend-next
npm run dev
# Visit http://localhost:3000/admin
```

---

## Production URLs

| Service         | URL                                                    |
| --------------- | ------------------------------------------------------ |
| Backend Health  | https://interviq-backend.onrender.com/health           |
| Backend API     | https://interviq-backend.onrender.com/api/v1           |
| Frontend        | https://interviq-frontend.onrender.com                 |
| Admin Login     | https://interviq-frontend.onrender.com/admin           |
| Admin Dashboard | https://interviq-frontend.onrender.com/admin/dashboard |

---

## Success Indicators

✅ All of these should work:

- [ ] Backend `/health` endpoint responds
- [ ] Admin login endpoint accessible and returns token
- [ ] Admin can login to frontend
- [ ] Dashboard loads with stats
- [ ] User list displays
- [ ] Can view audit logs
- [ ] Can ban/unban users
- [ ] All admin actions logged

---

## Next Steps

1. **Wait for Deployment:** Render deployments take 2-5 minutes
2. **Test Admin Login:** Go to `/admin` page
3. **Verify Dashboard:** Check stats are loading
4. **Test Features:** Try banning a user, viewing logs
5. **Create More Admins:** Use CLI tool if needed
   ```bash
   python backend/scripts/create_admin.py username password "Full Name"
   ```
6. **Monitor Logs:** Keep watch on Render dashboard for any errors

---

Generated: 2026-02-26
Status: Backend deployed, Frontend deploying, Tests pending
