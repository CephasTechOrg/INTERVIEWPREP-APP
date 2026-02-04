import { describe, it, expect, beforeEach } from 'vitest';
import { aiService } from '@/lib/services/aiService';

describe('aiService', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'mock_jwt_token');
  });

  describe('chat', () => {
    it('should send a chat message and receive response', async () => {
      const result = await aiService.chat({
        message: 'What is a binary tree?',
      });

      expect(result.response).toBeDefined();
      expect(result.response).toContain('AI response to: What is a binary tree?');
    });
  });
});
