'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/services/authService';
import { useAuthStore } from '@/lib/stores/authStore';
import { AuthLayout } from '@/components/layout/AuthLayout';

const inputCls =
  'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 disabled:opacity-50';
const labelCls = 'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5';
const linkCls = 'text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium transition-colors';

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { isAuthenticated, isHydrated } = useAuthStore();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (isHydrated && isAuthenticated) router.push('/');
  }, [isHydrated, isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail) { setError('Please enter your email address.'); return; }
    try {
      setIsSubmitting(true);
      await authService.requestPasswordReset(trimmedEmail);
      if (typeof window !== 'undefined') localStorage.setItem('reset_email', trimmedEmail);
      setSuccess('If an account exists with this email, you will receive a 6-digit reset code.');
      setRedirecting(true);
      setTimeout(() => router.push(`/reset-password?email=${encodeURIComponent(trimmedEmail)}`), 1200);
    } catch {
      if (typeof window !== 'undefined') localStorage.setItem('reset_email', trimmedEmail);
      setSuccess('If an account exists with this email, you will receive a 6-digit reset code.');
      setRedirecting(true);
      setTimeout(() => router.push(`/reset-password?email=${encodeURIComponent(trimmedEmail)}`), 1200);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-white dark:bg-slate-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your email and we'll send you a reset code">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className={labelCls}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputCls}
            placeholder="you@example.com"
            autoComplete="email"
            disabled={isSubmitting || !!success}
          />
        </div>

        {error && (
          <div className="flex items-start gap-3 p-3.5 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-400 text-sm rounded-xl">
            <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="flex items-start gap-3 p-3.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-sm rounded-xl">
            <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{success}</span>
          </div>
        )}

        {!success ? (
          <button type="submit" disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-xl shadow-lg shadow-indigo-500/25 transition-all duration-200">
            {isSubmitting ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Sending...
              </>
            ) : 'Send Reset Code'}
          </button>
        ) : (
          <button type="button" disabled={redirecting}
            onClick={() => router.push(`/reset-password?email=${encodeURIComponent(email.trim().toLowerCase())}`)}
            className="w-full flex items-center justify-center gap-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 font-medium py-3 px-4 rounded-xl transition-all duration-200">
            {redirecting ? 'Opening reset form...' : 'Enter Reset Code →'}
          </button>
        )}
      </form>

      <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800 space-y-2 text-center text-sm text-slate-500 dark:text-slate-400">
        <p>Already have a code? <Link href="/reset-password" className={linkCls}>Reset now</Link></p>
        <p>Remember your password? <Link href="/login" className={linkCls}>Sign in</Link></p>
        <p>Need an account? <Link href="/signup" className={linkCls}>Sign up</Link></p>
      </div>
    </AuthLayout>
  );
}
