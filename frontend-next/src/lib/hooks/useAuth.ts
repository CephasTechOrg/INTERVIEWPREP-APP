'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/authStore';
import { authService } from '@/lib/services/authService';
import { useAuthReady } from '@/components/providers/AuthProvider';

export const useAuth = () => {
  const router = useRouter();
  const { isReady } = useAuthReady();
  const {
    user,
    token,
    isAuthenticated,
    isLoading,
    isHydrated,
    error,
    login: storeLogin,
    logout: storeLogout,
    setLoading,
    setError,
    clearError,
  } = useAuthStore();

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        setLoading(true);
        clearError();

        const loginRes = await authService.login({ email, password });
        
        // Store token first so getProfile can use it
        localStorage.setItem('access_token', loginRes.access_token);
        
        try {
          await authService.syncLocalProfile(email);
        } catch {
          // non-blocking
        }

        const profile = await authService.getProfile();
        
        storeLogin(loginRes.access_token, profile);
        router.push('/');
        
        return { success: true };
      } catch (err: unknown) {
        const errorObj = err as { message?: string; status?: number };
        const message = errorObj?.message || 'Login failed';
        setError(message);
        
        // Check if user needs verification
        if (errorObj?.status === 403 || message.toLowerCase().includes('verify')) {
          localStorage.setItem('signup_email', email.toLowerCase());
          return { success: false, needsVerification: true, message };
        }
        
        return { success: false, needsVerification: false, message };
      } finally {
        setLoading(false);
      }
    },
    [router, storeLogin, setLoading, setError, clearError]
  );

  const signup = useCallback(
    async (email: string, password: string, fullName?: string) => {
      try {
        setLoading(true);
        clearError();

        await authService.signup({ 
          email, 
          password, 
          full_name: fullName || null 
        });
        
        return { success: true };
      } catch (err: unknown) {
        const errorObj = err as { message?: string };
        const message = errorObj?.message || 'Signup failed';
        setError(message);
        return { success: false, message };
      } finally {
        setLoading(false);
      }
    },
    [setLoading, setError, clearError]
  );

  const verify = useCallback(
    async (email: string, code: string) => {
      try {
        setLoading(true);
        clearError();

        const verifyRes = await authService.verifyEmail({ email, code });
        
        // Store token first so getProfile can use it
        localStorage.setItem('access_token', verifyRes.access_token);
        
        try {
          await authService.syncLocalProfile(email);
        } catch {
          // non-blocking
        }

        const profile = await authService.getProfile();
        
        storeLogin(verifyRes.access_token, profile);
        router.push('/');
        
        return { success: true };
      } catch (err: unknown) {
        const errorObj = err as { message?: string };
        const message = errorObj?.message || 'Verification failed';
        setError(message);
        return { success: false, message };
      } finally {
        setLoading(false);
      }
    },
    [router, storeLogin, setLoading, setError, clearError]
  );

  const logout = useCallback(() => {
    storeLogout();
    router.push('/login');
  }, [router, storeLogout]);

  const resendVerification = useCallback(
    async (email: string) => {
      try {
        setLoading(true);
        clearError();
        
        await authService.resendVerification(email);
        return { success: true };
      } catch (err: unknown) {
        const errorObj = err as { message?: string };
        const message = errorObj?.message || 'Failed to resend verification';
        setError(message);
        return { success: false, message };
      } finally {
        setLoading(false);
      }
    },
    [setLoading, setError, clearError]
  );

  return {
    // State
    user,
    token,
    isAuthenticated,
    isLoading,
    isHydrated,
    isReady,
    error,
    
    // For backwards compatibility
    initialized: isHydrated && isReady,
    
    // Actions
    login,
    signup,
    verify,
    logout,
    resendVerification,
    clearError,
  };
};

