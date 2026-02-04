import { describe, it, expect, beforeEach } from 'vitest';
import { apiClient } from '@/lib/api';

describe('API Client', () => {
  describe('token handling', () => {
    it('should include Authorization header when token exists', async () => {
      localStorage.setItem('access_token', 'test_token');

      // This will hit the MSW mock for /users/me
      const result = await apiClient.get('/users/me');

      expect(result).toBeDefined();
      expect((result as { id: number }).id).toBe(1);
    });

    it('should not include Authorization header when no token', async () => {
      localStorage.removeItem('access_token');

      // Should fail with 401 because no token
      await expect(apiClient.get('/users/me')).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('error handling', () => {
    it('should parse error message from detail string', async () => {
      await expect(
        apiClient.post('/auth/login', { email: 'test@example.com', password: 'wrong' })
      ).rejects.toMatchObject({
        message: expect.stringContaining('Incorrect'),
        status: 401,
      });
    });

    it('should handle 403 forbidden errors', async () => {
      await expect(
        apiClient.post('/auth/login', { email: 'unverified@example.com', password: 'correct_password' })
      ).rejects.toMatchObject({
        status: 403,
        message: expect.stringContaining('verify'),
      });
    });
  });

  describe('HTTP methods', () => {
    beforeEach(() => {
      localStorage.setItem('access_token', 'test_token');
    });

    it('should handle GET requests', async () => {
      const result = await apiClient.get('/users/me');
      expect(result).toBeDefined();
    });

    it('should handle POST requests', async () => {
      const result = await apiClient.post('/sessions', {
        role: 'swe_engineer',
        track: 'algorithms',
      });
      expect(result).toBeDefined();
    });

    it('should handle PATCH requests', async () => {
      const result = await apiClient.patch('/users/me', {
        full_name: 'Updated Name',
      });
      expect(result).toBeDefined();
    });
  });
});
