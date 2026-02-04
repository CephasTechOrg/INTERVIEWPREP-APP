import { describe, it, expect, beforeEach } from 'vitest';
import { sessionService } from '@/lib/services/sessionService';

describe('sessionService', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'mock_jwt_token');
  });

  describe('createSession', () => {
    it('should create a new interview session', async () => {
      const result = await sessionService.createSession({
        role: 'swe_engineer',
        track: 'algorithms',
        company_style: 'faang',
        difficulty: 'medium',
        interviewer: 'balanced',
        behavioral_count: 2,
      });

      expect(result.id).toBeDefined();
      expect(result.role).toBe('swe_engineer');
      expect(result.track).toBe('algorithms');
      expect(result.status).toBe('active');
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(
        sessionService.createSession({
          role: 'swe_engineer',
          track: 'algorithms',
          company_style: 'faang',
          difficulty: 'medium',
        })
      ).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('listSessions', () => {
    it('should return list of sessions', async () => {
      const result = await sessionService.listSessions();

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].id).toBeDefined();
      expect(result[0].status).toBeDefined();
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(sessionService.listSessions()).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('getMessages', () => {
    it('should return messages for a session', async () => {
      const result = await sessionService.getMessages(1);

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].content).toBeDefined();
      expect(result[0].role).toBeDefined();
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(sessionService.getMessages(1)).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('startSession', () => {
    it('should start a session and return first message', async () => {
      const result = await sessionService.startSession(1);

      expect(result.id).toBeDefined();
      expect(result.content).toBeDefined();
      expect(result.role).toBe('interviewer');
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(sessionService.startSession(1)).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('sendMessage', () => {
    it('should send a message and receive response', async () => {
      const result = await sessionService.sendMessage(1, {
        content: 'My answer to the question',
      });

      expect(result.id).toBeDefined();
      expect(result.content).toContain('Response to:');
      expect(result.role).toBe('interviewer');
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(
        sessionService.sendMessage(1, { content: 'Hello' })
      ).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('finalizeSession', () => {
    it('should finalize a session and return evaluation', async () => {
      const result = await sessionService.finalizeSession(1);

      expect(result.session_id).toBe(1);
      expect(result.scores).toBeDefined();
      expect(result.feedback).toBeDefined();
      expect(result.strengths).toBeDefined();
      expect(result.improvements).toBeDefined();
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(sessionService.finalizeSession(1)).rejects.toMatchObject({
        status: 401,
      });
    });
  });
});
