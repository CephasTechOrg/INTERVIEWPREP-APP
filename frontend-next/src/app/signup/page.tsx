'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/services/authService';
import { useAuthStore } from '@/lib/stores/authStore';
import { AuthLayout } from '@/components/layout/AuthLayout';

const inputCls =
  'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-all duration-200 disabled:opacity-50';
const selectCls =
  'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-all duration-200 disabled:opacity-50 appearance-none cursor-pointer';
const labelCls = 'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5';
const linkCls = 'text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 font-medium transition-colors';

const ROLE_OPTIONS = [
  { value: 'SWE Intern', label: 'SWE Intern' },
  { value: 'Software Engineer', label: 'Software Engineer' },
  { value: 'Senior Engineer', label: 'Senior Engineer' },
  { value: 'Cybersecurity', label: 'Cybersecurity' },
  { value: 'Data Science', label: 'Data Science' },
  { value: 'DevOps / Cloud', label: 'DevOps / Cloud' },
  { value: 'Product Management', label: 'Product Management' },
];
const COMPANY_OPTIONS = [
  { value: 'general', label: 'General Tech' },
  { value: 'amazon', label: 'Amazon' },
  { value: 'google', label: 'Google' },
  { value: 'apple', label: 'Apple' },
  { value: 'microsoft', label: 'Microsoft' },
  { value: 'meta', label: 'Meta' },
];
const DIFFICULTY_OPTIONS = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

const ChevronDown = () => (
  <svg className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

export default function SignupPage() {
  const router = useRouter();
  const { isAuthenticated, isHydrated } = useAuthStore();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rolePref, setRolePref] = useState('SWE Intern');
  const [companyPref, setCompanyPref] = useState('general');
  const [difficultyPref, setDifficultyPref] = useState('easy');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isHydrated && isAuthenticated) router.push('/');
  }, [isHydrated, isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();
    const trimmedName = fullName.trim();
    if (!trimmedEmail || !trimmedPassword) { setError('Email and password are required.'); return; }
    if (trimmedPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    try {
      setIsSubmitting(true);
      await authService.signup({ email: trimmedEmail, password: trimmedPassword, full_name: trimmedName || null });
      if (typeof window !== 'undefined') {
        localStorage.setItem(`user_profile_${trimmedEmail}`, JSON.stringify({
          email: trimmedEmail, full_name: trimmedName, role_pref: rolePref,
          company_pref: companyPref, difficulty_pref: difficultyPref, updated_at: Date.now(),
        }));
      }
      setSuccess('Verification code sent! Check your email.');
      setTimeout(() => router.push('/verify'), 1500);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj?.message || 'Signup failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-white dark:bg-slate-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <AuthLayout title="Create your account" subtitle="Start practicing for your technical interviews today">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name + Email */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Full Name</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              className={inputCls} placeholder="Your name" autoComplete="name" disabled={isSubmitting} />
          </div>
          <div>
            <label className={labelCls}>Email <span className="text-red-500">*</span></label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className={inputCls} placeholder="you@example.com" autoComplete="email" required disabled={isSubmitting} />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className={labelCls}>Password <span className="text-red-500">*</span></label>
          <div className="relative">
            <input type={showPassword ? 'text' : 'password'} value={password}
              onChange={(e) => setPassword(e.target.value)} className={`${inputCls} pr-11`}
              placeholder="Min 8 characters" autoComplete="new-password" required disabled={isSubmitting} />
            <button type="button" onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
              {showPassword ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Preferences */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className={labelCls}>Role</label>
            <div className="relative">
              <select value={rolePref} onChange={(e) => setRolePref(e.target.value)} className={selectCls} disabled={isSubmitting}>
                {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <ChevronDown />
            </div>
          </div>
          <div>
            <label className={labelCls}>Company Style</label>
            <div className="relative">
              <select value={companyPref} onChange={(e) => setCompanyPref(e.target.value)} className={selectCls} disabled={isSubmitting}>
                {COMPANY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <ChevronDown />
            </div>
          </div>
          <div>
            <label className={labelCls}>Difficulty</label>
            <div className="relative">
              <select value={difficultyPref} onChange={(e) => setDifficultyPref(e.target.value)} className={selectCls} disabled={isSubmitting}>
                {DIFFICULTY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <ChevronDown />
            </div>
          </div>
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

        <button type="submit" disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-200">
          {isSubmitting ? (
            <>
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Creating account...
            </>
          ) : 'Create Account'}
        </button>
      </form>

      <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800 space-y-2 text-center text-sm text-slate-500 dark:text-slate-400">
        <p>Already have an account? <Link href="/login" className={linkCls}>Sign in</Link></p>
        <p>Have a verification code? <Link href="/verify" className={linkCls}>Verify email</Link></p>
      </div>
    </AuthLayout>
  );
}
