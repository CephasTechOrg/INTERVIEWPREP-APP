'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/services/authService';
import { useAuthStore } from '@/lib/stores/authStore';

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

export default function SignupPage() {
  const router = useRouter();
  const { isAuthenticated, isHydrated } = useAuthStore();
  
  // Form state
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rolePref, setRolePref] = useState('SWE Intern');
  const [companyPref, setCompanyPref] = useState('general');
  const [difficultyPref, setDifficultyPref] = useState('easy');
  
  // UI state
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isHydrated && isAuthenticated) {
      router.push('/');
    }
  }, [isHydrated, isAuthenticated, router]);

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) return 'Password must be at least 8 characters.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();
    const trimmedName = fullName.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError('Email and password are required.');
      return;
    }

    const passwordError = validatePassword(trimmedPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    try {
      setIsSubmitting(true);
      
      // Call signup API
      await authService.signup({ 
        email: trimmedEmail, 
        password: trimmedPassword,
        full_name: trimmedName || null
      });
      
      // Store preferences locally for later profile update
      if (typeof window !== 'undefined') {
        const profileKey = `user_profile_${trimmedEmail}`;
        localStorage.setItem(profileKey, JSON.stringify({
          email: trimmedEmail,
          full_name: trimmedName,
          role_pref: rolePref,
          company_pref: companyPref,
          difficulty_pref: difficultyPref,
          updated_at: Date.now(),
        }));
      }
      
      setSuccess('Verification code sent! Check your email.');
      
      // Redirect to verify page after short delay
      setTimeout(() => router.push('/verify'), 1500);
    } catch (err: unknown) {
      console.error('Signup error:', err);
      const errorObj = err as { message?: string };
      setError(errorObj?.message || 'Signup failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Don't render until hydrated
  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="animate-pulse text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Interview Prep <span className="text-blue-400">AI</span>
          </h1>
          <p className="text-slate-400">Master your next technical interview</p>
        </div>

        {/* Card */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-2">Create Account</h2>
          <p className="text-slate-300 mb-6">Start practicing for your interviews</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Two Column Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Full Name */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Your name"
                  autoComplete="name"
                  disabled={isSubmitting}
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Email <span className="text-red-400">*</span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                  disabled={isSubmitting}
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Password <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all pr-12"
                    placeholder="Min 8 characters"
                    autoComplete="new-password"
                    required
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                  >
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

              {/* Preferred Role */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Preferred Role
                </label>
                <select
                  value={rolePref}
                  onChange={(e) => setRolePref(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all appearance-none cursor-pointer"
                  disabled={isSubmitting}
                >
                  {ROLE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value} className="bg-slate-800">
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Company Style */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Company Style
                </label>
                <select
                  value={companyPref}
                  onChange={(e) => setCompanyPref(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all appearance-none cursor-pointer"
                  disabled={isSubmitting}
                >
                  {COMPANY_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value} className="bg-slate-800">
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Difficulty */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Starting Difficulty
                </label>
                <select
                  value={difficultyPref}
                  onChange={(e) => setDifficultyPref(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all appearance-none cursor-pointer"
                  disabled={isSubmitting}
                >
                  {DIFFICULTY_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value} className="bg-slate-800">
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/20 border border-red-500/50 text-red-200 text-sm p-4 rounded-xl flex items-start gap-3">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {/* Success Message */}
            {success && (
              <div className="bg-green-500/20 border border-green-500/50 text-green-200 text-sm p-4 rounded-xl flex items-start gap-3">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{success}</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-green-600 hover:bg-green-500 disabled:bg-green-600/50 text-white font-semibold py-3 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-green-600/25"
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Creating account...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  <span>Create Account</span>
                </>
              )}
            </button>
          </form>

          {/* Links */}
          <div className="mt-6 pt-6 border-t border-white/10 text-center space-y-3">
            <p className="text-slate-400 text-sm">
              Already have an account?{' '}
              <Link href="/login" className="text-blue-400 font-medium hover:text-blue-300 transition-colors">
                Sign in
              </Link>
            </p>
            <p className="text-slate-400 text-sm">
              Have a verification code?{' '}
              <Link href="/verify" className="text-blue-400 font-medium hover:text-blue-300 transition-colors">
                Verify email
              </Link>
            </p>
          </div>
        </div>

        {/* Terms */}
        <p className="text-center text-slate-500 text-xs mt-6">
          By creating an account, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
