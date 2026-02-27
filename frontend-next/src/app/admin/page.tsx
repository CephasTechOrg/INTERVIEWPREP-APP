
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/authStore';

export default function AdminLoginPage() {
  const router = useRouter();
  const { isAuthenticated, isHydrated, user } = useAuthStore();
  const isAdmin = !!user?.is_admin;

  useEffect(() => {
    if (!isHydrated) return;
    if (isAuthenticated && isAdmin) {
      router.push('/admin/dashboard');
      return;
    }
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isAdmin, isHydrated, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-3">Admin Portal</h1>
        <p className="text-gray-600 mb-4">Admins sign in using the main login page.</p>
        <p className="text-gray-600">Redirecting you to login...</p>
      </div>
    </div>
  );
}
