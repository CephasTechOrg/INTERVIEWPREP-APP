# Interview Prep AI - Next.js Frontend Testing Guide

## ✅ Current Status

Both backend and frontend are running and ready for testing!

### Servers Running

- **Frontend (Next.js):** http://localhost:3000
- **Backend (FastAPI):** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger UI)

---

## 🧪 Test User Credentials

Use these credentials to test the application:

```
Email:    test@example.com
Password: password123
```

> ℹ️ The test user is verified and ready to use immediately (no email verification required)

---

## 📋 Testing Workflow

### 1. **Login Page** (`/login`)

- Go to http://localhost:3000/login
- Enter credentials:
  - Email: `test@example.com`
  - Password: `password123`
- Click "Sign In"
- ✓ Expected: Redirects to dashboard homepage

### 2. **Dashboard** (Main Page `/`)

After logging in, you should see:

- **Persistent Sidebar** on the left (stays visible)
- **Top Bar** with page title, theme toggle, user info
- **Content Area** with:
  - Hero greeting message
  - Quick Start section with interview cards (track selection)
  - Recent Sessions list
  - Statistics (Total, Completed, In Progress)

**Navigation:** Click any track + difficulty level to start a new interview

### 3. **Interview Section** (`/interview`)

When you start an interview, the dashboard switches to the Interview section:

- **Question Panel** (left): Shows current question and session details
- **Chat Panel** (right): Message history and input field
- Messages appear in chat bubbles (your answers in blue, interviewer in gray)
- Type your answer and click "Send" to submit

> ⚠️ **Note:** Currently messages are stored but the AI feedback loop isn't fully configured. This is expected in this phase.

### 4. **Results Section** (`/results`)

Click on a completed session from Recent Sessions to view results:

- **Overall Score** display
- **Summary** section
- **Rubric Breakdown** with detailed evaluation criteria

### 5. **Analytics Section** (`/charts`)

View performance statistics:

- Total sessions count
- Completed sessions count
- Average score
- Performance by track (if multiple interviews done)

### 6. **Settings Section** (`/settings`)

Manage preferences:

- **Profile Display** (email, full name, LinkedIn)
- **Theme Toggle** (Light/Dark mode)
- **Voice Output** (enable/disable)

---

## 🔍 Debugging Tips

### If "Network Error" on Login

1. **Check backend is running:**

   ```bash
   # In terminal:
   cd backend
   python -m uvicorn app.main:app --reload
   ```

   Should show: `Uvicorn running on http://127.0.0.1:8000`

2. **Check frontend can reach backend:**
   - Open browser console (F12)
   - Check "Network" tab for API calls
   - Look for calls to `http://localhost:8000/api/v1/auth/login`

3. **Check CORS settings:**
   - Backend should allow localhost:3000
   - See `backend/app/main.py` lines 28-47 for CORS config

4. **Check .env.local:**
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```

### If Login Page Doesn't Load

1. **Check frontend is running:**

   ```bash
   cd frontend-next
   npm run dev
   ```

   Should show: `✓ Ready in X.Xs` and `Local: http://localhost:3000`

2. **Clear browser cache:**
   - DevTools > Application > Clear site data
   - Close and reopen browser

### Browser Console Errors

- Open DevTools (F12)
- Check Console tab for JavaScript errors
- Check Network tab to see if API calls fail
- Look for CORS errors in headers

---

## 📊 Single-Page App Architecture

The frontend is a true SPA with:

- **Persistent Sidebar & TopBar** - stays visible during navigation
- **Dynamic Content Area** - content switches without page reload
- **No Page Loads** - all transitions are smooth (no full refresh)
- **Single URL** - main page at `/` handles all sections

When you click:

- Dashboard → content updates, sidebar stays
- Interview → content updates, sidebar stays
- Results → content updates, sidebar stays
- Charts → content updates, sidebar stays
- Settings → content updates, sidebar stays

---

## 🎯 Full Test Scenario

**Time:** ~5-10 minutes

1. ✓ Go to http://localhost:3000/login
2. ✓ Sign in with test@example.com / password123
3. ✓ Verify dashboard loads with sidebar & recent sessions
4. ✓ Click a track + difficulty (e.g., SWE Engineer - Easy)
5. ✓ Verify page switches to Interview section (no reload)
6. ✓ Type a response and click Send
7. ✓ Verify message appears in chat
8. ✓ Click Analytics in sidebar (no page reload, content changes)
9. ✓ Verify stats display
10. ✓ Click Settings
11. ✓ Toggle theme (should change page appearance)
12. ✓ Click Dashboard to return
13. ✓ Click the user avatar or Settings > Logout

---

## 🛠️ Common Test Scenarios

### Scenario A: Multiple Interviews

```
1. Create interview 1 (Dashboard → SWE Engineer/Easy)
2. Send one message
3. Navigate to Results (see incomplete interview)
4. Back to Dashboard
5. Create interview 2 (Data Science/Medium)
6. Navigate back to Dashboard
→ Should see both interviews in Recent Sessions list
```

### Scenario B: Theme Switching

```
1. Click theme toggle (☀️/🌙) in TopBar
2. Check if page background/text colors change
3. Refresh page (F5)
→ Theme preference should persist (saved in localStorage)
```

### Scenario C: Sidebar Responsiveness

```
1. Resize browser window smaller (<1024px)
2. Sidebar should transform to mobile menu
3. Click hamburger (☰) button
→ Sidebar should slide out as overlay
```

---

## 📱 Mobile Testing

The SPA is responsive across devices:

**Desktop (>1024px):**

- Sidebar always visible
- Full content width

**Tablet (768px - 1024px):**

- Sidebar visible but narrower
- Content adjusts

**Mobile (<768px):**

- Hamburger menu (☰)
- Click to toggle sidebar overlay
- Full-width content

---

## 🚀 Next Steps (After Testing)

### Phase 1: Polish

- [ ] Add loading skeletons
- [ ] Improve error messages
- [ ] Add toast notifications

### Phase 2: AI Integration

- [ ] Connect to LLM for interview evaluation
- [ ] Real-time AI responses
- [ ] Rubric feedback

### Phase 3: Features

- [ ] Export results as PDF
- [ ] Share results link
- [ ] Leaderboard/progress tracking

### Phase 4: Deployment

- [ ] Deploy to Vercel
- [ ] Set up CI/CD
- [ ] Performance optimization

---

## 📚 Key Files

**Frontend Structure:**

```
frontend-next/
├── src/
│   ├── app/
│   │   ├── page.tsx           # Main SPA shell
│   │   ├── login/page.tsx     # Login page
│   │   ├── signup/page.tsx    # Signup page
│   │   ├── verify/page.tsx    # Email verification
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Tailwind styles
│   ├── components/
│   │   ├── layout/            # Sidebar, TopBar, MainLayout
│   │   └── sections/          # Dashboard, Interview, Results, Charts, Settings
│   ├── lib/
│   │   ├── api.ts             # HTTP client
│   │   ├── stores/            # Zustand stores (auth, session, ui)
│   │   ├── services/          # API service layer
│   │   └── hooks/             # Custom hooks (useAuth)
│   └── types/
│       └── api.ts             # TypeScript API types
```

**Backend API (Reference):**

```
http://localhost:8000/api/v1
├── /auth
│   ├── POST /signup
│   ├── POST /login
│   ├── POST /verify-email
│   └── GET /profile
├── /sessions
│   ├── POST /create
│   ├── GET /{id}
│   ├── POST /{id}/message
│   └── POST /{id}/finalize
├── /questions
│   ├── GET /list
│   └── GET /coverage/{session_id}
├── /analytics
│   └── GET
└── /ai
    ├── GET /status
    └── POST /chat
```

---

## 💡 Pro Tips

- **Keyboard Shortcuts:**
  - `F12` - Open DevTools
  - `Ctrl+Shift+I` - Inspect Element
  - `Ctrl+K` - Search (browser)

- **Browser DevTools:**
  - Network tab: Watch API calls
  - Console: Check for errors
  - Application tab: View localStorage (including auth token)
  - Sources: Debug TypeScript

- **Testing with cURL:**
  ```bash
  # Test login endpoint
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"password123"}'
  ```

---

## ✅ Success Criteria

- [ ] Login works with test credentials
- [ ] Dashboard loads with sidebar visible
- [ ] Can navigate between sections without page reload
- [ ] Sidebar & TopBar stay visible when switching sections
- [ ] Can start an interview session
- [ ] Can send messages in interview
- [ ] Theme toggle works
- [ ] Logout works and redirects to login
- [ ] No console errors
- [ ] No network errors

---

## 🐛 Found a Bug?

1. **Note the error message**
2. **Check browser console (F12)**
3. **Check backend logs**
4. **Provide:**
   - Steps to reproduce
   - Expected vs actual behavior
   - Console error (if any)
   - Network response (if API call failed)

---

## 🎉 Ready to Test!

All systems are running. Go to **http://localhost:3000/login** and start testing!

Questions or issues? Check the relevant section above or review the backend API docs at **http://localhost:8000/docs**.

**Happy Testing! 🚀**
