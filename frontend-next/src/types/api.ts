// ============================================
// Authentication Types
// ============================================

export interface SignupRequest {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface SignupResponse {
  ok: boolean;
  message: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface VerifyEmailRequest {
  email: string;
  code: string;
}

export interface VerifyEmailResponse {
  access_token: string;
  token_type: string;
}

export interface ResendVerificationRequest {
  email: string;
}

export interface ResendVerificationResponse {
  ok: boolean;
  message?: string;
}

export interface ResetPasswordRequest {
  email: string;
}

export interface PerformResetRequest {
  email: string;
  token: string;
  new_password: string;
}

// ============================================
// User Types
// ============================================

// User profile returned by /users/me
export interface User {
  email: string;
  full_name?: string | null;
  role_pref?: string | null;
  profile?: Record<string, unknown>;
}

export interface UserProfileUpdate {
  full_name?: string | null;
  role_pref?: string;
  profile?: Record<string, unknown>;
}

// Session Types
export type SessionStage =
  | 'warmup'
  | 'behavioral'
  | 'main'
  | 'intro'
  | 'question'
  | 'followup'
  | 'evaluation'
  | 'done'
  | string;
export type Difficulty = 'easy' | 'medium' | 'hard';
export type Track = 'swe_engineer' | 'swe_intern' | 'data_science' | 'devops_cloud' | 'product_management' | 'behavioral' | 'cybersecurity';

export interface InterviewerProfile {
  id: string;
  name: string;
  gender?: string | null;
  image_url?: string | null;
}

export interface SessionCreateRequest {
  role?: string;
  track: Track;
  company_style: string;
  difficulty: Difficulty;
  behavioral_questions_target?: number;
  interviewer?: InterviewerProfile | null;
}

export interface InterviewSession {
  id: number;
  role: string;
  track: Track;
  company_style: string;
  difficulty: Difficulty;
  stage: SessionStage;
  current_question_id?: number | null;
  interviewer?: InterviewerProfile | null;
}

export interface SessionSummary {
  id: number;
  role: string;
  track: Track;
  company_style: string;
  difficulty: Difficulty;
  stage: SessionStage;
  current_question_id?: number | null;
  questions_asked_count?: number;
  max_questions?: number;
  behavioral_questions_target?: number;
  overall_score?: number | null;
  created_at?: string | null;
  interviewer?: InterviewerProfile | null;
}

export interface Message {
  id: number;
  session_id: number;
  role: string;
  content: string;
  created_at?: string | null;
  current_question_id?: number | null;
}

export interface SendMessageRequest {
  content: string;
}

export interface FinalizeSessionRequest {
  feedback?: string;
}

export interface EvaluationSummary {
  strengths?: string[];
  weaknesses?: string[];
  next_steps?: string[];
}

export interface Evaluation {
  session_id: number;
  overall_score: number;
  rubric: Record<string, unknown>;
  summary: EvaluationSummary;
}

// Question Types
export interface Question {
  id: number;
  track: Track;
  company_style: string;
  difficulty: Difficulty;
  title: string;
  prompt: string;
  tags: string[];
  question_type?: string | null;
}

// Analytics Types
export interface QuestionCoverageResponse {
  track: Track;
  company_style: string;
  difficulty: Difficulty;
  count: number;
  fallback_general: number;
}

// AI Types
export interface AIStatusResponse {
  configured: boolean;
  status: 'online' | 'offline' | 'unknown';
  fallback_mode?: boolean;
  reason?: string;
  last_ok_at?: number | null;
  last_error_at?: number | null;
  last_error?: string | null;
  base_url?: string;
  model?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AIChatRequest {
  message: string;
  history?: ChatMessage[];
}

export interface AIChatResponse {
  reply: string;
  mode: 'live' | 'fallback';
}

// Voice/TTS Types
export interface TTSRequest {
  text: string;
}

export interface TTSResponseText {
  mode: 'text';
  text: string;
  tts_provider?: string;
}

export interface TTSResponseAudio {
  mode: 'audio';
  audio_url: string;
  tts_provider?: string;
}

export type TTSResponse = TTSResponseText | TTSResponseAudio;

// Error Types
export interface APIError {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
}

export interface ErrorResponse {
  message: string;
  status: number;
  details?: unknown;
}
