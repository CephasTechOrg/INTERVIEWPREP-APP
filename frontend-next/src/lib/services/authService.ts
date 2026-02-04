import { apiClient } from '@/lib/api';
import {
  LoginRequest,
  LoginResponse,
  SignupRequest,
  SignupResponse,
  VerifyEmailRequest,
  VerifyEmailResponse,
  ResendVerificationRequest,
  ResendVerificationResponse,
  ResetPasswordRequest,
  PerformResetRequest,
  User,
  UserProfileUpdate,
} from '@/types/api';

export const authService = {
  /**
   * Get locally stored profile preferences (from signup form)
   */
  getStoredProfile(email: string): UserProfileUpdate | null {
    if (typeof window === 'undefined') return null;
    const key = `user_profile_${email.toLowerCase()}`;
    const raw = localStorage.getItem(key);
    if (!raw) return null;

    try {
      const parsed = JSON.parse(raw) as any;
      const profile: Record<string, unknown> = {};

      if (parsed.company_pref) profile.company_pref = parsed.company_pref;
      if (parsed.difficulty_pref) profile.difficulty_pref = parsed.difficulty_pref;
      if (parsed.focus_pref) profile.focus_pref = parsed.focus_pref;
      if (parsed.years_experience) profile.years_experience = parsed.years_experience;
      if (parsed.location) profile.location = parsed.location;

      return {
        full_name: parsed.full_name || null,
        role_pref: parsed.role_pref || null,
        profile: Object.keys(profile).length ? profile : undefined,
      };
    } catch {
      return null;
    }
  },

  /**
   * Sync locally stored profile preferences to the server
   */
  async syncLocalProfile(email: string): Promise<void> {
    const update = this.getStoredProfile(email);
    if (!update) return;
    await this.updateProfile(update);
  },

  /**
   * Sign up a new user - creates a pending signup and sends verification code
   */
  async signup(data: SignupRequest): Promise<SignupResponse> {
    const response = await apiClient.post<SignupResponse>('/auth/signup', data);
    // Store email for verification flow
    if (typeof window !== 'undefined') {
      localStorage.setItem('signup_email', data.email.toLowerCase());
    }
    return response;
  },

  /**
   * Log in with email and password
   * Returns JWT token if successful
   * Throws 403 if email not verified
   */
  async login(data: LoginRequest): Promise<LoginResponse> {
    return apiClient.post<LoginResponse>('/auth/login', data);
  },

  /**
   * Verify email with 6-digit code
   * Creates the actual user account and returns JWT token
   */
  async verifyEmail(data: VerifyEmailRequest): Promise<VerifyEmailResponse> {
    const response = await apiClient.post<VerifyEmailResponse>('/auth/verify', data);
    // Clear signup email after successful verification
    if (typeof window !== 'undefined') {
      localStorage.removeItem('signup_email');
    }
    return response;
  },

  /**
   * Resend verification code to email
   */
  async resendVerification(email: string): Promise<ResendVerificationResponse> {
    return apiClient.post<ResendVerificationResponse>('/auth/resend-verification', { email });
  },

  /**
   * Request a password reset email
   */
  async requestPasswordReset(email: string): Promise<{ ok: boolean; message?: string }> {
    return apiClient.post('/auth/request-password-reset', { email });
  },

  /**
   * Perform password reset with token
   */
  async resetPassword(token: string, newPassword: string): Promise<{ ok: boolean; message?: string }> {
    return apiClient.post('/auth/reset-password', { 
      token, 
      new_password: newPassword 
    });
  },

  /**
   * Get current user's profile
   */
  async getProfile(): Promise<User> {
    return apiClient.get<User>('/users/me');
  },

  /**
   * Update current user's profile
   */
  async updateProfile(data: UserProfileUpdate): Promise<User> {
    return apiClient.patch<User>('/users/me', data);
  },

  /**
   * Get the stored signup email (for verify page auto-fill)
   */
  getStoredSignupEmail(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('signup_email');
  },
};

