import { describe, it, expect, beforeEach } from 'vitest';
import { authService } from '@/lib/services/authService';

describe('authService', () => {
  describe('signup', () => {
    it('should successfully sign up a new user', async () => {
      const result = await authService.signup({
        email: 'newuser@example.com',
        password: 'securePassword123',
      });

      expect(result.message).toBe('Verification code sent');
      expect(result.email).toBe('newuser@example.com');
    });

    it('should store signup email in localStorage', async () => {
      await authService.signup({
        email: 'newuser@example.com',
        password: 'securePassword123',
      });

      expect(localStorage.getItem('signup_email')).toBe('newuser@example.com');
    });

    it('should reject duplicate emails', async () => {
      await expect(
        authService.signup({
          email: 'existing@example.com',
          password: 'password123',
        })
      ).rejects.toMatchObject({
        status: 400,
        message: expect.stringContaining('already registered'),
      });
    });
  });

  describe('login', () => {
    it('should successfully login with correct credentials', async () => {
      const result = await authService.login({
        email: 'test@example.com',
        password: 'correct_password',
      });

      expect(result.access_token).toBe('mock_jwt_token_12345');
      expect(result.token_type).toBe('bearer');
    });

    it('should reject incorrect password', async () => {
      await expect(
        authService.login({
          email: 'test@example.com',
          password: 'wrong_password',
        })
      ).rejects.toMatchObject({
        status: 401,
        message: expect.stringContaining('Incorrect'),
      });
    });

    it('should reject unverified users with 403', async () => {
      await expect(
        authService.login({
          email: 'unverified@example.com',
          password: 'correct_password',
        })
      ).rejects.toMatchObject({
        status: 403,
        message: expect.stringContaining('verify'),
      });
    });
  });

  describe('verifyEmail', () => {
    it('should successfully verify email with correct code', async () => {
      const result = await authService.verifyEmail({
        email: 'test@example.com',
        code: '123456',
      });

      expect(result.access_token).toBe('mock_jwt_token_verified');
      expect(result.user).toBeDefined();
      expect(result.user?.email).toBe('test@example.com');
    });

    it('should clear signup_email after successful verification', async () => {
      localStorage.setItem('signup_email', 'test@example.com');

      await authService.verifyEmail({
        email: 'test@example.com',
        code: '123456',
      });

      expect(localStorage.getItem('signup_email')).toBeNull();
    });

    it('should reject invalid verification code', async () => {
      await expect(
        authService.verifyEmail({
          email: 'test@example.com',
          code: '000000',
        })
      ).rejects.toMatchObject({
        status: 400,
        message: expect.stringContaining('Invalid'),
      });
    });
  });

  describe('getProfile', () => {
    beforeEach(() => {
      localStorage.setItem('access_token', 'mock_jwt_token');
    });

    it('should return user profile when authenticated', async () => {
      const result = await authService.getProfile();

      expect(result.id).toBe(1);
      expect(result.email).toBe('test@example.com');
      expect(result.is_verified).toBe(true);
    });

    it('should reject when not authenticated', async () => {
      localStorage.removeItem('access_token');

      await expect(authService.getProfile()).rejects.toMatchObject({
        status: 401,
      });
    });
  });

  describe('updateProfile', () => {
    beforeEach(() => {
      localStorage.setItem('access_token', 'mock_jwt_token');
    });

    it('should update user profile', async () => {
      const result = await authService.updateProfile({
        full_name: 'Updated Name',
        role_pref: 'data_science',
      });

      expect(result.full_name).toBe('Updated Name');
      expect(result.role_pref).toBe('data_science');
    });
  });

  describe('getStoredProfile', () => {
    it('should return null when no profile stored', () => {
      const result = authService.getStoredProfile('test@example.com');
      expect(result).toBeNull();
    });

    it('should return stored profile preferences', () => {
      const profileData = {
        full_name: 'Test User',
        role_pref: 'swe_engineer',
        company_pref: 'faang',
        difficulty_pref: 'hard',
      };
      localStorage.setItem('user_profile_test@example.com', JSON.stringify(profileData));

      const result = authService.getStoredProfile('test@example.com');

      expect(result).not.toBeNull();
      expect(result?.full_name).toBe('Test User');
      expect(result?.role_pref).toBe('swe_engineer');
    });
  });

  describe('getStoredSignupEmail', () => {
    it('should return null when no email stored', () => {
      const result = authService.getStoredSignupEmail();
      expect(result).toBeNull();
    });

    it('should return stored signup email', () => {
      localStorage.setItem('signup_email', 'stored@example.com');
      const result = authService.getStoredSignupEmail();
      expect(result).toBe('stored@example.com');
    });
  });
});
