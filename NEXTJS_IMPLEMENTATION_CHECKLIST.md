# Next.js Implementation Checklist & Code Templates

## Quick Start Template

### 1. Create Next.js Project

```bash
npx create-next-app@latest interview-prep --typescript --tailwind --app
cd interview-prep
npm install zustand react-query axios
npm install -D @types/node @types/react @types/react-dom
```

### 2. Environment Setup

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_APP_NAME=Interview Prep AI
```

---

## Core Files to Create (in order)

### Phase 1: API & State Management

#### 1️⃣ `src/lib/api.ts` (Central API Client)

```typescript
import { useAuthStore } from "@/lib/store/authStore";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any,
  ) {
    super(message);
    this.name = "APIError";
  }
}

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: any;
  auth?: boolean;
}

export async function apiFetch<T = any>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { method = "GET", body = null, auth = true } = options;

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
    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });

    let data: any = null;
    const text = await response.text();

    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    if (!response.ok) {
      const message =
        data?.detail || data?.message || `Request failed (${response.status})`;

      // Handle auth errors
      if (auth && (response.status === 401 || response.status === 403)) {
        useAuthStore.getState().logout();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      }

      throw new APIError(response.status, message, data);
    }

    return data as T;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    console.error("[apiFetch]", { url, method, error });
    throw new Error(error instanceof Error ? error.message : "Network error");
  }
}

export { APIError };
```

#### 2️⃣ `src/lib/store/authStore.ts` (Zustand Auth Store)

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface User {
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
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  logout: () => void;
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
      setLoading: (loading: boolean) => set({ isLoading: loading }),
      setError: (error: string | null) => set({ error }),
      logout: () => set({ token: null, user: null, error: null }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    },
  ),
);
```

#### 3️⃣ `src/lib/store/sessionStore.ts` (Session State)

```typescript
import { create } from "zustand";

export interface Session {
  id: number;
  role: string;
  track: string;
  company_style: string;
  difficulty: string;
  stage: string;
  questions_asked_count: number;
  max_questions: number;
  current_question_id?: number;
  interviewer?: {
    id: string;
    name: string;
    gender?: string;
    image_url?: string;
  };
}

interface SessionStore {
  session: Session | null;
  messages: any[];
  isLoading: boolean;
  error: string | null;

  setSession: (session: Session) => void;
  addMessage: (message: any) => void;
  setMessages: (messages: any[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  session: null,
  messages: [],
  isLoading: false,
  error: null,

  setSession: (session) => set({ session }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setMessages: (messages) => set({ messages }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  reset: () => set({ session: null, messages: [], error: null }),
}));
```

#### 4️⃣ `src/lib/store/uiStore.ts` (UI State)

```typescript
import { create } from "zustand";

interface UIStore {
  theme: "light" | "dark";
  sidebarOpen: boolean;
  voiceEnabled: boolean;

  toggleTheme: () => void;
  setSidebarOpen: (open: boolean) => void;
  setVoiceEnabled: (enabled: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  theme: "light",
  sidebarOpen: true,
  voiceEnabled: false,

  toggleTheme: () =>
    set((state) => ({
      theme: state.theme === "light" ? "dark" : "light",
    })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setVoiceEnabled: (enabled) => set({ voiceEnabled: enabled }),
}));
```

### Phase 2: Service Layer

#### 5️⃣ `src/lib/services/authService.ts` (Auth API Calls)

```typescript
import { apiFetch, APIError } from "@/lib/api";
import { useAuthStore } from "@/lib/store/authStore";

export interface SignupResponse {
  ok: boolean;
  message: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authService = {
  async signup(
    email: string,
    password: string,
    fullName?: string,
  ): Promise<SignupResponse> {
    return await apiFetch<SignupResponse>("/auth/signup", {
      method: "POST",
      auth: false,
      body: {
        email,
        password,
        full_name: fullName || null,
      },
    });
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });

    useAuthStore.getState().setToken(data.access_token);
    localStorage.setItem("last_auth_email", email);

    return data;
  },

  async verify(email: string, code: string): Promise<TokenResponse> {
    const data = await apiFetch<TokenResponse>("/auth/verify", {
      method: "POST",
      auth: false,
      body: { email, code },
    });

    useAuthStore.getState().setToken(data.access_token);
    return data;
  },

  async resendVerification(email: string): Promise<SignupResponse> {
    return await apiFetch<SignupResponse>("/auth/resend-verify", {
      method: "POST",
      auth: false,
      body: { email },
    });
  },

  logout() {
    useAuthStore.getState().logout();
    localStorage.removeItem("last_auth_email");
  },
};
```

#### 6️⃣ `src/lib/services/sessionService.ts` (Session Management)

```typescript
import { apiFetch } from "@/lib/api";

export interface CreateSessionParams {
  track: string;
  company_style: string;
  difficulty: string;
  behavioral_questions_target?: number;
}

export interface Session {
  id: number;
  user_id: number;
  role: string;
  track: string;
  company_style: string;
  difficulty: string;
  stage: string;
  questions_asked_count: number;
  current_question_id?: number;
  max_questions: number;
  behavioral_questions_target: number;
  skill_state?: Record<string, any>;
  interviewer?: any;
  created_at: string;
}

export interface Message {
  id: number;
  session_id: number;
  role: string; // 'interviewer' | 'student' | 'system'
  content: string;
  created_at: string;
}

export interface Evaluation {
  session_id: number;
  overall_score: number;
  rubric: Record<string, number>;
  summary: Record<string, any>;
}

export const sessionService = {
  async createSession(params: CreateSessionParams): Promise<Session> {
    return await apiFetch<Session>("/sessions", {
      method: "POST",
      body: params,
    });
  },

  async getSession(sessionId: number): Promise<Session> {
    return await apiFetch<Session>(`/sessions/${sessionId}`);
  },

  async listSessions(limit: number = 50): Promise<Session[]> {
    return await apiFetch<Session[]>(`/sessions?limit=${limit}`);
  },

  async sendMessage(sessionId: number, message: string): Promise<Message> {
    return await apiFetch<Message>(`/sessions/${sessionId}/message`, {
      method: "POST",
      body: { message },
    });
  },

  async finalizeSession(sessionId: number): Promise<Evaluation> {
    return await apiFetch<Evaluation>(`/sessions/${sessionId}/finalize`, {
      method: "POST",
      body: {},
    });
  },

  async getResults(sessionId: number): Promise<Evaluation> {
    return await apiFetch<Evaluation>(
      `/analytics/sessions/${sessionId}/results`,
    );
  },
};
```

#### 7️⃣ `src/lib/services/questionService.ts` (Questions)

```typescript
import { apiFetch } from "@/lib/api";

export interface Question {
  id: number;
  track: string;
  company_style: string;
  difficulty: string;
  title: string;
  prompt: string;
  tags: string[];
  question_type: string;
}

export interface QuestionCoverage {
  track: string;
  company_style: string;
  difficulty: string;
  count: number;
  fallback_general: number;
}

export const questionService = {
  async getQuestions(filters?: {
    track?: string;
    company_style?: string;
    difficulty?: string;
  }): Promise<Question[]> {
    const params = new URLSearchParams();
    if (filters?.track) params.append("track", filters.track);
    if (filters?.company_style)
      params.append("company_style", filters.company_style);
    if (filters?.difficulty) params.append("difficulty", filters.difficulty);

    return await apiFetch<Question[]>(`/questions?${params}`);
  },

  async getCoverage(
    track: string,
    company_style: string,
    difficulty: string,
    includeBehavioral: boolean = false,
  ): Promise<QuestionCoverage> {
    return await apiFetch<QuestionCoverage>(
      `/questions/coverage?track=${track}&company_style=${company_style}&difficulty=${difficulty}&include_behavioral=${includeBehavioral}`,
    );
  },

  async getQuestion(questionId: number): Promise<Question> {
    return await apiFetch<Question>(`/questions/${questionId}`);
  },
};
```

#### 8️⃣ `src/lib/services/aiService.ts` (AI Chat & Status)

```typescript
import { apiFetch } from "@/lib/api";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  mode: "live" | "fallback";
}

export interface LLMStatus {
  configured: boolean;
  status: "online" | "offline" | "unknown";
  fallback_mode: boolean;
  last_ok_at?: number;
  last_error_at?: number;
  last_error?: string;
}

export const aiService = {
  async getStatus(): Promise<LLMStatus> {
    return await apiFetch<LLMStatus>("/ai/status");
  },

  async chat(
    message: string,
    history: ChatMessage[] = [],
  ): Promise<ChatResponse> {
    return await apiFetch<ChatResponse>("/ai/chat", {
      method: "POST",
      body: { message, history },
    });
  },

  async generateSpeech(
    text: string,
  ): Promise<ArrayBuffer | { mode: string; text: string }> {
    const token = localStorage.getItem("auth-storage");
    const parsedToken = token ? JSON.parse(token).state?.token : null;

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1"}/tts`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(parsedToken && { Authorization: `Bearer ${parsedToken}` }),
        },
        body: JSON.stringify({ text }),
      },
    );

    if (!response.ok) {
      throw new Error("TTS failed");
    }

    const contentType = response.headers.get("content-type");
    if (contentType?.includes("audio")) {
      return await response.arrayBuffer();
    }

    return await response.json();
  },
};
```

### Phase 3: Hooks

#### 9️⃣ `src/lib/hooks/useAuth.ts` (Auth Hook)

```typescript
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/authStore";

export function useAuth() {
  const router = useRouter();
  const { token, user, isLoading } = useAuthStore();

  useEffect(() => {
    if (!token && !isLoading && typeof window !== "undefined") {
      // Optional: redirect to login if not authenticated
      // Uncomment if you want to protect routes here
      // router.push('/login');
    }
  }, [token, isLoading, router]);

  return {
    token,
    user,
    isLoading,
    isAuthenticated: !!token,
  };
}
```

#### 🔟 `src/lib/hooks/useSession.ts` (Session Hook)

```typescript
"use client";

import { useState, useCallback } from "react";
import { useSessionStore } from "@/lib/store/sessionStore";
import {
  sessionService,
  CreateSessionParams,
} from "@/lib/services/sessionService";

export function useSession(initialSessionId?: number) {
  const {
    session,
    messages,
    isLoading,
    error,
    setSession,
    addMessage,
    setLoading,
    setError,
    reset,
  } = useSessionStore();

  const createSession = useCallback(
    async (params: CreateSessionParams) => {
      setLoading(true);
      try {
        const data = await sessionService.createSession(params);
        setSession(data);
        return data;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to create session";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [setSession, setLoading, setError],
  );

  const sendMessage = useCallback(
    async (message: string) => {
      if (!session?.id) throw new Error("No active session");

      setLoading(true);
      try {
        const response = await sessionService.sendMessage(session.id, message);
        addMessage(response);
        return response;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to send message";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [session?.id, setLoading, setError, addMessage],
  );

  const finalize = useCallback(async () => {
    if (!session?.id) throw new Error("No active session");

    setLoading(true);
    try {
      const evaluation = await sessionService.finalizeSession(session.id);
      return evaluation;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to finalize session";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [session?.id, setLoading, setError]);

  return {
    session,
    messages,
    isLoading,
    error,
    createSession,
    sendMessage,
    finalize,
    reset,
  };
}
```

---

## Layout Components

#### 1️⃣1️⃣ `src/components/layout/Sidebar.tsx`

```typescript
'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/store/authStore';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '🏠' },
  { href: '/interview', label: 'Interview', icon: '💬' },
  { href: '/chat', label: 'AI Chat', icon: '🤖' },
  { href: '/results', label: 'Results', icon: '📊' },
  { href: '/settings', label: 'Settings', icon: '⚙️' },
];

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <aside className="w-64 bg-gray-900 text-white h-screen flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-2xl font-bold">IntervIQ</h1>
      </div>

      <nav className="flex-1 p-6 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`block px-4 py-3 rounded-lg transition ${
              pathname === item.href
                ? 'bg-blue-600 text-white'
                : 'hover:bg-gray-800'
            }`}
          >
            <span className="mr-2">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="p-6 border-t border-gray-800">
        <button
          onClick={handleLogout}
          className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg"
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
```

#### 1️⃣2️⃣ `src/components/layout/TopBar.tsx`

```typescript
'use client';

import { useAuthStore } from '@/lib/store/authStore';

export function TopBar() {
  const user = useAuthStore((state) => state.user);

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-gray-600">Practice your technical interviews</p>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900">{user?.full_name || user?.email}</p>
          <p className="text-xs text-gray-500">{user?.role_pref}</p>
        </div>
        <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
          {user?.email?.[0].toUpperCase()}
        </div>
      </div>
    </header>
  );
}
```

---

## Page Components

#### 1️⃣3️⃣ `src/app/(auth)/login/page.tsx`

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/services/authService';
import { useAuthStore } from '@/lib/store/authStore';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const setToken = useAuthStore((state) => state.setToken);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await authService.login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome Back</h1>
          <p className="text-gray-600 mb-6">Sign in to your interview prep account</p>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg disabled:opacity-50"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="mt-6 text-center text-gray-600 text-sm">
            Don't have an account?{' '}
            <Link href="/signup" className="text-blue-600 hover:underline font-medium">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

## Types Definition

#### 1️⃣4️⃣ `src/types/api.ts`

```typescript
// Auth
export interface SignupRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

// Sessions
export interface Session {
  id: number;
  user_id: number;
  role: string;
  track: string;
  company_style: string;
  difficulty: string;
  stage: "intro" | "question" | "followups" | "evaluation" | "done";
  questions_asked_count: number;
  max_questions: number;
  behavioral_questions_target: number;
  skill_state: Record<string, any>;
  current_question_id?: number;
  created_at: string;
}

// Questions
export interface Question {
  id: number;
  track: string;
  company_style: string;
  difficulty: string;
  title: string;
  prompt: string;
  tags: string[];
  question_type: "coding" | "system_design" | "behavioral" | "conceptual";
}

// Evaluation
export interface Evaluation {
  session_id: number;
  overall_score: number;
  rubric: {
    communication: number;
    problem_solving: number;
    correctness_reasoning: number;
    complexity: number;
    edge_cases: number;
  };
  summary: {
    strengths: string[];
    weaknesses: string[];
    next_steps: string[];
  };
}
```

---

## Build & Deploy Checklist

- [ ] All components created and tested
- [ ] API services working correctly
- [ ] Auth flow complete (signup → verify → login)
- [ ] Interview flow complete (create → message → finalize)
- [ ] Results page displays scores and feedback
- [ ] Settings page saves preferences
- [ ] Theme toggle working
- [ ] Voice features tested
- [ ] Mobile responsive design verified
- [ ] Error handling for all scenarios
- [ ] Performance optimized (code splitting, lazy loading)
- [ ] SEO metadata added
- [ ] Environment variables configured
- [ ] Backend CORS allows frontend origin
- [ ] Database migrations run on backend
- [ ] E2E tests passing
- [ ] Security audit complete (no exposed tokens, HTTPS in prod)
- [ ] Staging deployment successful
- [ ] Production deployment tested
- [ ] Monitoring/error tracking set up
- [ ] User documentation updated

---

## Troubleshooting

### Common Issues

**Issue:** 401 Unauthorized on protected routes

- **Fix:** Ensure token is stored correctly in Zustand store
- **Check:** `useAuthStore.getState().token` is not null

**Issue:** CORS errors from backend

- **Fix:** Add frontend URL to `FRONTEND_ORIGINS` in backend `.env`
- **Example:** `FRONTEND_ORIGINS=http://localhost:3000`

**Issue:** API calls return 422 validation error

- **Fix:** Check request body matches API schema exactly
- **Example:** Use `company_style: 'google'`, not `companyStyle`

**Issue:** AI responses are fallback mode

- **Fix:** Verify `DEEPSEEK_API_KEY` is set in backend `.env`
- **Check:** Call `/ai/status` to see configured status

**Issue:** TTS audio not working

- **Fix:** Ensure audio Context API is initialized
- **Check:** Browser console for audio errors

---

## Performance Tips

1. **Image Optimization**

   ```typescript
   import Image from 'next/image';

   <Image
     src="/logo.png"
     alt="Logo"
     width={200}
     height={200}
     priority // for above-fold images
   />
   ```

2. **Code Splitting**

   ```typescript
   import dynamic from 'next/dynamic';
   const ResultsChart = dynamic(() => import('@/components/ResultsChart'), {
     loading: () => <div>Loading chart...</div>,
   });
   ```

3. **React Query**
   ```typescript
   const { data: sessions } = useQuery({
     queryKey: ["sessions"],
     queryFn: () => sessionService.listSessions(),
     staleTime: 5 * 60 * 1000, // 5 minutes
   });
   ```

---

## Summary

✅ Complete Next.js → FastAPI integration ready  
✅ Zero breaking changes to backend  
✅ Type-safe API client with Zustand stores  
✅ Full authentication and session management  
✅ Ready for production deployment

**Next Steps:**

1. Copy this checklist to your Next.js project
2. Follow Phase 1-3 to set up infrastructure
3. Build pages following Phase 4-7
4. Test thoroughly before deploying
