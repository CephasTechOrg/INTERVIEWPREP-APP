import { describe, it, expect, beforeEach } from 'vitest';
import { analyticsService } from '@/lib/services/analyticsService';

describe('analyticsService', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'mock_jwt_token');
  });

  describe('getSessionResults', () => {
    it('should return evaluation results for a session', async () => {
      const result = await analyticsService.getSessionResults(1);

      expect(result.session_id).toBe(1);
      expect(result.scores).toBeDefined();
      expect(result.scores.overall).toBe(85);
      expect(result.feedback).toBeDefined();
      expect(result.strengths).toBeInstanceOf(Array);
      expect(result.improvements).toBeInstanceOf(Array);
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(analyticsService.getSessionResults(1)).rejects.toMatchObject({
        status: 401,
      });
    });
  });
});
