import { http, HttpResponse } from 'msw';

const BASE_URL = 'http://127.0.0.1:8000/api/v1';

// Mock data
export const mockUser = {
  id: 1,
  email: 'test@example.com',
  full_name: 'Test User',
  is_verified: true,
  role_pref: 'swe_engineer',
  profile: {
    company_pref: 'faang',
    difficulty_pref: 'medium',
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

export const mockSession = {
  id: 1,
  user_id: 1,
  role: 'swe_engineer',
  track: 'algorithms',
  stage: 'warmup',
  company_style: 'faang',
  difficulty: 'medium',
  interviewer: 'balanced',
  behavioral_count: 2,
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

export const mockMessage = {
  id: 1,
  session_id: 1,
  role: 'interviewer',
  content: 'Welcome to your interview!',
  created_at: '2026-01-01T00:00:00Z',
};

export const handlers = [
  // Auth endpoints
  http.post(`${BASE_URL}/auth/signup`, async ({ request }) => {
    const body = await request.json() as { email?: string; password?: string };
    
    if (!body.email || !body.password) {
      return HttpResponse.json(
        { detail: 'Email and password are required' },
        { status: 422 }
      );
    }
    
    if (body.email === 'existing@example.com') {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 400 }
      );
    }
    
    return HttpResponse.json({
      message: 'Verification code sent',
      email: body.email,
    });
  }),

  http.post(`${BASE_URL}/auth/login`, async ({ request }) => {
    const body = await request.json() as { email?: string; password?: string };
    
    if (!body.email || !body.password) {
      return HttpResponse.json(
        { detail: 'Email and password are required' },
        { status: 422 }
      );
    }
    
    if (body.email === 'unverified@example.com') {
      return HttpResponse.json(
        { detail: 'Please verify your email first' },
        { status: 403 }
      );
    }
    
    if (body.password !== 'correct_password') {
      return HttpResponse.json(
        { detail: 'Incorrect email or password' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json({
      access_token: 'mock_jwt_token_12345',
      token_type: 'bearer',
    });
  }),

  http.post(`${BASE_URL}/auth/verify`, async ({ request }) => {
    const body = await request.json() as { email?: string; code?: string };
    
    if (body.code !== '123456') {
      return HttpResponse.json(
        { detail: 'Invalid verification code' },
        { status: 400 }
      );
    }
    
    return HttpResponse.json({
      access_token: 'mock_jwt_token_verified',
      token_type: 'bearer',
      user: mockUser,
    });
  }),

  http.post(`${BASE_URL}/auth/resend-verification`, async () => {
    return HttpResponse.json({
      message: 'Verification code sent',
    });
  }),

  // User endpoints
  http.get(`${BASE_URL}/users/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json(mockUser);
  }),

  http.patch(`${BASE_URL}/users/me`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...mockUser, ...body });
  }),

  // Session endpoints
  http.post(`${BASE_URL}/sessions`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...mockSession, ...body });
  }),

  http.get(`${BASE_URL}/sessions`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json([
      { ...mockSession, id: 1, status: 'completed' },
      { ...mockSession, id: 2, status: 'active' },
    ]);
  }),

  http.get(`${BASE_URL}/sessions/:id/messages`, ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json([
      { ...mockMessage, id: 1, role: 'interviewer', content: 'Welcome!' },
      { ...mockMessage, id: 2, role: 'student', content: 'Hello!' },
    ]);
  }),

  http.post(`${BASE_URL}/sessions/:id/start`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json(mockMessage);
  }),

  http.post(`${BASE_URL}/sessions/:id/message`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    const body = await request.json() as { content?: string };
    return HttpResponse.json({
      ...mockMessage,
      id: Date.now(),
      role: 'interviewer',
      content: `Response to: ${body.content}`,
    });
  }),

  http.post(`${BASE_URL}/sessions/:id/finalize`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json({
      session_id: 1,
      scores: { overall: 85 },
      feedback: 'Great job!',
      strengths: ['Problem solving', 'Communication'],
      improvements: ['Time management'],
    });
  }),

  // Analytics endpoints
  http.get(`${BASE_URL}/analytics/sessions/:id/results`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json({
      session_id: 1,
      scores: { overall: 85, technical: 80, communication: 90 },
      feedback: 'Great performance!',
      strengths: ['Clear communication', 'Good problem-solving'],
      improvements: ['Practice edge cases'],
    });
  }),

  // AI endpoints
  http.post(`${BASE_URL}/ai/chat`, async ({ request }) => {
    const body = await request.json() as { message?: string };
    return HttpResponse.json({
      response: `AI response to: ${body.message}`,
    });
  }),
];
