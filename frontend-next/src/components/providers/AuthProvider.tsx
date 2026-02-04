'use client';

import { useEffect, useState, createContext, useContext, ReactNode } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { authService } from '@/lib/services/authService';

interface AuthContextType {
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({ isReady: false });

export function useAuthReady() {
  const context = useContext(AuthContext);
  // If used outside provider, return a safe default
  if (context === undefined) {
    return { isReady: true };
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isReady, setIsReady] = useState(false);
  const { isHydrated, token, user, setUser, logout, setLoading } = useAuthStore();

  useEffect(() => {
    const initializeAuth = async () => {
      // Wait for Zustand to hydrate from localStorage
      if (!isHydrated) return;

      // If we have a token but no user, fetch the profile
      if (token && !user) {
        try {
          setLoading(true);
          const profile = await authService.getProfile();
          setUser(profile);
          if (typeof window !== 'undefined') {
            localStorage.setItem('user', JSON.stringify(profile));
          }
        } catch (error) {
          // Token is invalid, log out
          console.error('Failed to fetch profile:', error);
          logout();
        } finally {
          setLoading(false);
        }
      }

      setIsReady(true);
    };

    initializeAuth();
  }, [isHydrated, token, user, setUser, logout, setLoading]);

  // Show nothing until hydrated to prevent flash
  if (!isHydrated) {
    return null;
  }

  return (
    <AuthContext.Provider value={{ isReady }}>
      {children}
    </AuthContext.Provider>
  );
}
