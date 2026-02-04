# Interview Prep AI → Next.js Conversion Blueprint

## Executive Summary

Converting the **Interview Prep AI** frontend from vanilla HTML/CSS/JS to **Next.js** while maintaining **100% API compatibility** with the FastAPI backend. The backend remains untouched; all data flows through the same REST endpoints.

---

## Current Architecture Overview

### Backend (FastAPI) - **NO CHANGES**

- **Entry:** `backend/app/main.py`
- **Base URL:** `http://127.0.0.1:8000/api/v1` (configurable)
- **Database:** PostgreSQL (Alembic migrations)
- **LLM:** DeepSeek API (with graceful fallback)
- **Auth:** JWT tokens (7-day expiry)

### Frontend (Currently Vanilla) → **Next.js 14+ with App Router**

- Static HTML → React Components
- Vanilla JS → TypeScript + React hooks
- CSS → Tailwind CSS + CSS modules (or Shadcn/UI)
- localStorage → Context API + Zustand (recommended)
- Direct fetch → React Query or SWR with API client

---

## Database Schema (Unchanged)

```
Users
├─ id (PK)
├─ email (unique)
├─ password_hash (Argon2)
├─ is_verified (bool)
├─ verification_token
├─ reset_token
├─ full_name
├─ role_pref
├─ profile (JSON)
└─ created_at

InterviewSessions
├─ id (PK)
├─ user_id (FK → Users)
├─ role, track, company_style, difficulty
├─ stage (intro|question|followups|evaluation|done)
├─ questions_asked_count
├─ followups_used
├─ max_questions, max_followups_per_question
├─ behavioral_questions_target
├─ skill_state (JSON: {n, sum, last, interviewer, pool})
├─ current_question_id
└─ created_at

Questions
├─ id (PK)
├─ track (swe_intern, swe_engineer, etc.)
├─ company_style (general, amazon, google, etc.)
├─ difficulty (easy|medium|hard)
├─ title, prompt
├─ tags_csv
├─ followups (JSON)
├─ question_type (coding|system_design|behavioral|conceptual)
├─ meta (JSON)
└─ created_at

Messages
├─ id (PK)
├─ session_id (FK → InterviewSessions)
├─ role (interviewer|student|system)
├─ content (Text)
└─ created_at

Evaluations
├─ id (PK)
├─ session_id (FK → InterviewSessions, unique)
├─ overall_score
├─ rubric (JSON)
├─ summary (JSON)
└─ created_at

[Additional tables: SessionQuestion, SessionEmbedding, SessionFeedback, AuditLog, PendingSignup, UserQuestionSeen]
```

---

## API Endpoints (Unchanged)

### Authentication

```
POST   /auth/signup          → SignupResponse
POST   /auth/login           → TokenResponse (access_token)
POST   /auth/verify          → TokenResponse
POST   /auth/resend-verify   → SignupResponse
POST   /auth/reset           → ResetRequest
POST   /auth/reset-perform   → PerformResetRequest
```

### Sessions

```
GET    /sessions             → list[SessionSummaryOut]
POST   /sessions             → SessionOut (create new session)
GET    /sessions/{id}        → SessionOut (full session details)
POST   /sessions/{id}/message → MessageOut (send message + AI reply)
POST   /sessions/{id}/finalize → EvaluationOut (score & feedback)
```

### Questions

```
GET    /questions            → list[QuestionOut] (filtered by track/company/difficulty)
GET    /questions/coverage   → QuestionCoverageOut (count available questions)
GET    /questions/{id}       → QuestionOut (single question)
```

### Analytics

```
GET    /analytics/sessions/{id}/results → EvaluationOut
```

### AI

```
GET    /ai/status            → {configured, status, fallback_mode, last_ok_at, ...}
POST   /ai/chat              → ChatResponse (free-form chat)
```

### Voice/TTS

```
POST   /tts                  → audio/mpeg OR {mode: "text", text: "...", tts_provider: "..."}
```

---

## Next.js Project Structure

```
nextjs-interview-prep/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # Landing page (/)
│   │   ├── error.tsx               # Error boundary
│   │   ├── not-found.tsx           # 404 page
│   │   │
│   │   ├── (auth)/
│   │   │   ├── layout.tsx          # Auth layout
│   │   │   ├── login/page.tsx      # /login
│   │   │   ├── signup/page.tsx     # /signup
│   │   │   └── verify/page.tsx     # /verify
│   │   │
│   │   ├── (app)/
│   │   │   ├── layout.tsx          # App layout (sidebar + topbar)
│   │   │   ├── dashboard/page.tsx  # /dashboard
│   │   │   ├── interview/page.tsx  # /interview
│   │   │   ├── chat/page.tsx       # /chat
│   │   │   ├── results/[id]/page.tsx # /results/[id]
│   │   │   ├── settings/page.tsx   # /settings
│   │   │   └── history/page.tsx    # /history
│   │   │
│   │   └── api/
│   │       └── auth/
│   │           ├── login/route.ts  # OPTIONAL: middleware if needed
│   │           └── verify/route.ts # OPTIONAL: middleware if needed
│   │
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── SignupForm.tsx
│   │   │   └── VerifyForm.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   └── MobileMenu.tsx
│   │   ├── dashboard/
│   │   │   ├── SessionCard.tsx
│   │   │   ├── InterviewStart.tsx
│   │   │   └── HistoryTable.tsx
│   │   ├── interview/
│   │   │   ├── QuestionDisplay.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── SubmitAnswer.tsx
│   │   ├── results/
│   │   │   ├── ScoreGauge.tsx
│   │   │   ├── FeedbackCard.tsx
│   │   │   └── PerformanceChart.tsx
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── Spinner.tsx
│   │   └── providers/
│   │       ├── AuthProvider.tsx
│   │       ├── QueryProvider.tsx
│   │       └── ThemeProvider.tsx
│   │
│   ├── lib/
│   │   ├── api.ts              # Central API client (replaces assets/js/api.js)
│   │   ├── auth.ts             # Auth helpers
│   │   ├── hooks/
│   │   │   ├── useAuth.ts      # Auth context hook
│   │   │   ├── useSession.ts   # Session management
│   │   │   └── useInterviewEngine.ts # Interview flow logic
│   │   ├── services/
│   │   │   ├── authService.ts  # Auth API calls
│   │   │   ├── sessionService.ts # Session API calls
│   │   │   ├── questionService.ts # Question API calls
│   │   │   ├── aiService.ts    # AI chat + LLM status
│   │   │   └── analyticsService.ts # Results & analytics
│   │   ├── store/
│   │   │   ├── authStore.ts    # Zustand auth store
│   │   │   ├── sessionStore.ts # Session state
│   │   │   └── uiStore.ts      # UI state (theme, modals, etc.)
│   │   ├── utils/
│   │   │   ├── tokenStorage.ts # localStorage wrapper
│   │   │   ├── formatters.ts   # Date, score formatting
│   │   │   └── validators.ts   # Form validation
│   │   └── constants.ts        # Role, company, difficulty enums
│   │
│   ├── styles/
│   │   ├── globals.css         # Tailwind + global styles
│   │   ├── animations.css      # Shared animations
│   │   └── variables.css       # CSS custom properties
│   │
│   └── types/
│       ├── api.ts             # API response types
│       ├── models.ts          # Database model types
│       └── auth.ts            # Auth types
│
├── public/
│   ├── images/
│   │   ├── logo1.png
│   │   ├── hero.png
│   │   └── ...
│   └── fonts/
│
├── .env.local                 # Local backend URL (dev)
├── .env.production            # Production backend URL
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── README.md
```

---

## Core Implementation Details

### 1. API Client (lib/api.ts)

**Replaces:** `frontend/assets/js/api.js`

```typescript
// lib/api.ts
import { useAuthStore } from "@/lib/store/authStore";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: any;
  auth?: boolean;
}

export async function apiFetch(
  path: string,
  { method = "GET", body = null, auth = true }: FetchOptions = {},
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (auth) {
    const token = useAuthStore.getState().token;
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const url = `${API_BASE}${path}`;

  try {
    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });

    let data = null;
    const text = await res.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    if (!res.ok) {
      const msg =
        data?.detail || data?.message || `Request failed (${res.status})`;

      if (auth && (res.status === 401 || res.status === 403)) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
      }

      throw new Error(msg);
    }

    return data;
  } catch (error) {
    console.error("[apiFetch]", { url, method, error });
    throw error;
  }
}
```

### 2. Authentication Store (lib/store/authStore.ts)

**Replaces:** `localStorage` token management + `assets/js/auth.js` logic

```typescript
// lib/store/authStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: number;
  email: string;
  full_name?: string;
  role_pref: string;
  profile: Record<string, any>;
  is_verified: boolean;
}

interface AuthStore {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  error: string | null;

  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isLoading: false,
      error: null,

      setToken: (token: string) => set({ token }),
      setUser: (user: User) => set({ user }),
      logout: () => set({ token: null, user: null }),
      clearError: () => set({ error: null }),
    }),
    {
      name: "auth-storage", // localStorage key
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);
```

### 3. Auth Service (lib/services/authService.ts)

**Replaces:** `assets/js/auth.js` functions

```typescript
// lib/services/authService.ts
import { apiFetch } from "@/lib/api";
import { useAuthStore } from "@/lib/store/authStore";

export const authService = {
  async signup(email: string, password: string, fullName?: string) {
    const data = await apiFetch("/auth/signup", {
      method: "POST",
      auth: false,
      body: { email, password, full_name: fullName || null },
    });
    // Store email for verification flow
    localStorage.setItem("signup_email", email);
    return data;
  },

  async login(email: string, password: string) {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });

    // Store token
    useAuthStore.getState().setToken(data.access_token);
    localStorage.setItem("last_auth_email", email);

    return data;
  },

  async verify(email: string, code: string) {
    const data = await apiFetch("/auth/verify", {
      method: "POST",
      auth: false,
      body: { email, code },
    });

    useAuthStore.getState().setToken(data.access_token);
    return data;
  },

  logout() {
    useAuthStore.getState().logout();
    localStorage.removeItem("last_auth_email");
  },
};
```

### 4. Session Service (lib/services/sessionService.ts)

**Replaces:** Parts of `interview.part1.js`, `interview.part2.js`, `interview.part3.js`

```typescript
// lib/services/sessionService.ts
import { apiFetch } from "@/lib/api";

export const sessionService = {
  async createSession(params: {
    track: string;
    company_style: string;
    difficulty: string;
    behavioral_questions_target?: number;
  }) {
    return await apiFetch("/sessions", {
      method: "POST",
      body: params,
    });
  },

  async getSession(sessionId: number) {
    return await apiFetch(`/sessions/${sessionId}`);
  },

  async listSessions(limit: number = 50) {
    return await apiFetch(`/sessions?limit=${limit}`);
  },

  async sendMessage(sessionId: number, message: string) {
    return await apiFetch(`/sessions/${sessionId}/message`, {
      method: "POST",
      body: { message },
    });
  },

  async finalizeSession(sessionId: number) {
    return await apiFetch(`/sessions/${sessionId}/finalize`, {
      method: "POST",
    });
  },

  async getResults(sessionId: number) {
    return await apiFetch(`/analytics/sessions/${sessionId}/results`);
  },
};
```

### 5. Question Service (lib/services/questionService.ts)

```typescript
// lib/services/questionService.ts
import { apiFetch } from "@/lib/api";

export const questionService = {
  async getQuestions(filters?: {
    track?: string;
    company_style?: string;
    difficulty?: string;
  }) {
    const params = new URLSearchParams();
    if (filters?.track) params.append("track", filters.track);
    if (filters?.company_style)
      params.append("company_style", filters.company_style);
    if (filters?.difficulty) params.append("difficulty", filters.difficulty);

    return await apiFetch(`/questions?${params}`);
  },

  async getCoverage(track: string, company_style: string, difficulty: string) {
    return await apiFetch(
      `/questions/coverage?track=${track}&company_style=${company_style}&difficulty=${difficulty}`,
    );
  },

  async getQuestion(questionId: number) {
    return await apiFetch(`/questions/${questionId}`);
  },
};
```

### 6. AI Service (lib/services/aiService.ts)

**Replaces:** `assets/js/chat.js`

```typescript
// lib/services/aiService.ts
import { apiFetch } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export const aiService = {
  async getStatus() {
    return await apiFetch("/ai/status");
  },

  async chat(message: string, history: ChatMessage[] = []) {
    return await apiFetch("/ai/chat", {
      method: "POST",
      body: {
        message,
        history,
      },
    });
  },

  async generateSpeech(text: string) {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1"}/tts`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("auth-storage")}`,
        },
        body: JSON.stringify({ text }),
      },
    );

    if (!response.ok) throw new Error("TTS failed");

    const contentType = response.headers.get("content-type");
    if (contentType?.includes("audio")) {
      return await response.arrayBuffer();
    }

    return await response.json();
  },
};
```

### 7. Auth Hook (lib/hooks/useAuth.ts)

**Replaces:** Manual auth state management in vanilla JS

```typescript
// lib/hooks/useAuth.ts
import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/authStore";
import { authService } from "@/lib/services/authService";

export function useAuth() {
  const router = useRouter();
  const { token, user, isLoading, logout } = useAuthStore();

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!token && !isLoading) {
      router.push("/login");
    }
  }, [token, isLoading, router]);

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        await authService.login(email, password);
        router.push("/dashboard");
      } catch (error) {
        console.error("Login failed:", error);
        throw error;
      }
    },
    [router],
  );

  const signup = useCallback(
    async (email: string, password: string, fullName?: string) => {
      try {
        await authService.signup(email, password, fullName);
        // Redirect to verify page
        router.push(`/verify?email=${email}`);
      } catch (error) {
        console.error("Signup failed:", error);
        throw error;
      }
    },
    [router],
  );

  return {
    token,
    user,
    isLoading,
    login,
    signup,
    logout,
    isAuthenticated: !!token,
  };
}
```

### 8. Session Hook (lib/hooks/useSession.ts)

**Replaces:** Interview state management from vanilla JS

```typescript
// lib/hooks/useSession.ts
import { useState, useCallback } from "react";
import { sessionService } from "@/lib/services/sessionService";

interface Session {
  id: number;
  role: string;
  track: string;
  company_style: string;
  difficulty: string;
  stage: string;
  questions_asked_count: number;
  current_question_id?: number;
}

export function useSession(sessionId?: number) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = useCallback(async (params: any) => {
    setLoading(true);
    try {
      const data = await sessionService.createSession(params);
      setSession(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!session?.id) throw new Error("No active session");

      setLoading(true);
      try {
        const data = await sessionService.sendMessage(session.id, message);
        return data;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [session?.id],
  );

  const finalize = useCallback(async () => {
    if (!session?.id) throw new Error("No active session");

    setLoading(true);
    try {
      const data = await sessionService.finalizeSession(session.id);
      return data;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to finalize session",
      );
      throw err;
    } finally {
      setLoading(false);
    }
  }, [session?.id]);

  return {
    session,
    loading,
    error,
    createSession,
    sendMessage,
    finalize,
  };
}
```

---

## Component Mapping (Vanilla → React)

| Vanilla Page | HTML File        | React Component  | Route           |
| ------------ | ---------------- | ---------------- | --------------- |
| Landing      | `index.html`     | Landing (static) | `/`             |
| Login/Auth   | `login.html`     | LoginPage        | `/login`        |
| Dashboard    | `dashboard.html` | DashboardPage    | `/dashboard`    |
| Interview    | `interview.html` | InterviewPage    | `/interview`    |
| Chat         | `chat.html`      | ChatPage         | `/chat`         |
| Results      | `results.html`   | ResultsPage      | `/results/[id]` |
| Settings     | `settings.html`  | SettingsPage     | `/settings`     |

---

## Migration Steps

### Phase 1: Setup & Infrastructure (Week 1)

- [ ] Create Next.js project with TypeScript
- [ ] Install dependencies (React Query, Zustand, Tailwind, Shadcn/UI)
- [ ] Set up environment variables
- [ ] Create API client (`lib/api.ts`)
- [ ] Set up Zustand stores (auth, session, ui)
- [ ] Create service layer (authService, sessionService, etc.)

### Phase 2: Authentication (Week 1-2)

- [ ] Create LoginForm component
- [ ] Create SignupForm component
- [ ] Create VerifyForm component
- [ ] Implement auth flows (login, signup, verify)
- [ ] Test with backend

### Phase 3: Layout & Navigation (Week 2)

- [ ] Create Sidebar component
- [ ] Create TopBar component
- [ ] Create AppLayout (authenticated pages)
- [ ] Create AuthLayout (login/signup pages)
- [ ] Route protection middleware

### Phase 4: Dashboard (Week 2-3)

- [ ] DashboardPage component
- [ ] SessionCard component
- [ ] InterviewStart form
- [ ] History table
- [ ] Performance charts

### Phase 5: Interview Engine (Week 3-4)

- [ ] InterviewPage layout
- [ ] QuestionDisplay component
- [ ] ChatWindow component
- [ ] MessageBubble component
- [ ] Submit answer logic
- [ ] Stage management (intro → question → followups → evaluation)

### Phase 6: Results & Analytics (Week 4)

- [ ] ResultsPage component
- [ ] ScoreGauge (SVG circle progress)
- [ ] FeedbackCard component
- [ ] Performance charts
- [ ] Export/share results

### Phase 7: Chat & Settings (Week 4-5)

- [ ] ChatPage component
- [ ] AI chat logic
- [ ] SettingsPage component
- [ ] Theme toggle
- [ ] Voice settings

### Phase 8: Testing & Optimization (Week 5-6)

- [ ] API integration tests
- [ ] E2E tests
- [ ] Performance optimization
- [ ] Mobile responsiveness
- [ ] Accessibility audit

---

## Critical API Compatibility Checklist

### ✅ Authentication Flow

- [x] Token storage (localStorage → Zustand + localStorage)
- [x] JWT decode/verify (same format)
- [x] Email verification (6-digit code)
- [x] Password reset flow
- [x] Rate limiting (same IP/email logic)

### ✅ Session Management

- [x] Create session (POST /sessions)
- [x] Send message (POST /sessions/{id}/message)
- [x] Stage progression (intro → question → followups → evaluation → done)
- [x] Skill state tracking (JSON)
- [x] Finalize & score (POST /sessions/{id}/finalize)

### ✅ Question Selection

- [x] Filter by track/company/difficulty
- [x] Adaptive difficulty adjustment
- [x] Behavioral mix (2-3 behavioral questions)
- [x] Coverage lookup

### ✅ AI Integration

- [x] LLM status checks
- [x] Chat history management
- [x] Fallback mode when API key missing
- [x] TTS audio response handling

### ✅ Data Persistence

- [x] User profile in localStorage
- [x] Session state in Zustand
- [x] Interview history from backend
- [x] Evaluation scores from backend

---

## Environment Configuration

```env
# .env.local (development)
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_APP_NAME=Interview Prep AI

# .env.production
NEXT_PUBLIC_API_BASE=https://api.interviewprep.com/api/v1
NEXT_PUBLIC_APP_NAME=Interview Prep AI
```

---

## Error Handling Strategy

### 401/403 Unauthorized

- Clear token
- Redirect to `/login`
- Show toast: "Session expired. Please log in again."

### 422 Validation Error

- Show field-specific errors in forms
- Toast: "Please check your inputs"

### 429 Rate Limited

- Show toast: "Too many requests. Please wait a moment."
- Disable form submission for 60 seconds

### 500 Server Error

- Show toast: "Server error. Please try again."
- Log to Sentry (optional)

### LLM Offline

- Show notification: "AI is currently offline"
- Use fallback responses
- Display status badge

---

## Performance Optimizations

1. **Code Splitting:**
   - Dynamic imports for heavy pages
   - Lazy load results charts

2. **Data Fetching:**
   - React Query for caching
   - Stale-while-revalidate strategy
   - Background refetch

3. **Images:**
   - Next.js Image component (auto-optimization)
   - WebP format with fallback
   - Lazy load below-fold images

4. **Bundling:**
   - Tree-shaking unused CSS
   - Minify CSS/JS
   - Gzip compression

5. **Rendering:**
   - SSG for landing page
   - ISR for static content
   - Client-side for interactive features

---

## Testing Strategy

### Unit Tests (Vitest)

- API client error handling
- Auth state management
- Session hooks
- Utility functions

### Integration Tests (Playwright)

- Login → Dashboard → Start Interview flow
- Complete interview → Results flow
- Settings changes persist

### E2E Tests (Cypress)

- Full user journey from signup to results
- API error scenarios
- Offline mode handling

---

## Rollout Plan

1. **Beta Phase (Internal):**
   - Deploy to staging server
   - Test all API endpoints
   - Performance benchmarking
   - Load testing

2. **Gradual Rollout:**
   - 10% of users → Next.js app
   - Monitor error rates & performance
   - Gather feedback
   - Incremental 20% → 50% → 100%

3. **Fallback:**
   - Keep vanilla frontend live
   - Feature flag to switch between versions
   - Quick rollback if issues

---

## Known Considerations

### Speech Recognition & TTS

- Browser Web Speech API stays the same (in `components/interview/VoiceInput.tsx`)
- TTS endpoint unchanged (`/tts`)
- Audio blob handling in React

### WebSocket (if real-time chat added)

- Not currently used; keep REST-based for now
- Future: add Socket.io or native WebSocket support

### Local Storage Limits

- Current: token + user profile (~1-2KB)
- Safe for localStorage (5-10MB quota)
- No migration issues

### Browser Compatibility

- Next.js 14+: ES2020 target
- Supported: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- Polyfills: Built-in via Next.js

---

## Deployment

### Vercel (Recommended)

```bash
npm i -g vercel
vercel login
vercel --prod
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment at Deployment

- Set `NEXT_PUBLIC_API_BASE` to backend URL
- Ensure CORS allows frontend origin
- Verify JWT secret matches backend

---

## Summary: Zero API Disruption

✅ **Same Endpoints** - No backend changes  
✅ **Same Data Schema** - Tables unchanged  
✅ **Same Auth Tokens** - JWT format identical  
✅ **Same Error Codes** - 401, 422, 429 handling  
✅ **Same Rate Limits** - Applied identically  
✅ **Same LLM Integration** - DeepSeek calls same  
✅ **Same Validation** - Client-side + backend

**Result:** Users won't notice the frontend changed; they'll just see a better UI with React performance.

---

## Questions & Gotchas

**Q: Do we need to change the backend?**  
A: No. The API stays 100% the same. The backend doesn't know or care that the frontend is now Next.js.

**Q: Will authentication work the same?**  
A: Yes. JWT tokens are identical. The only difference is Zustand store instead of localStorage directly.

**Q: What about CORS?**  
A: Backend already has permissive CORS in dev mode. In production, add the Next.js frontend URL to `FRONTEND_ORIGINS`.

**Q: Can we deploy both frontends simultaneously?**  
A: Yes. Use feature flags to gradually shift users. Old vanilla frontend runs on same backend simultaneously.

**Q: What if Next.js breaks something?**  
A: Roll back to vanilla frontend (both run on same backend). Zero risk.
