import { apiClient } from '@/lib/api';
import {
  InterviewSession,
  SessionCreateRequest,
  SessionSummary,
  Message,
  SendMessageRequest,
  Evaluation,
} from '@/types/api';

export const sessionService = {
  async createSession(data: SessionCreateRequest): Promise<InterviewSession> {
    return apiClient.post('/sessions', data);
  },

  async listSessions(limit = 50): Promise<SessionSummary[]> {
    return apiClient.get(`/sessions?limit=${limit}`);
  },

  async getMessages(sessionId: number): Promise<Message[]> {
    return apiClient.get(`/sessions/${sessionId}/messages`);
  },

  async startSession(sessionId: number): Promise<Message> {
    return apiClient.post(`/sessions/${sessionId}/start`);
  },

  async sendMessage(sessionId: number, data: SendMessageRequest): Promise<Message> {
    return apiClient.post(`/sessions/${sessionId}/message`, data);
  },

  async finalizeSession(sessionId: number): Promise<Evaluation> {
    return apiClient.post(`/sessions/${sessionId}/finalize`);
  },

  async deleteSession(sessionId: number): Promise<{ ok: boolean }> {
    return apiClient.delete(`/sessions/${sessionId}`);
  },
};
