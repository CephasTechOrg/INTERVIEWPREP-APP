'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { authService } from '@/lib/services/authService';
import { useAuthStore } from '@/lib/stores/authStore';

interface ProfileModalProps {
  open: boolean;
  onClose: () => void;
}

const ROLE_OPTIONS = [
  'SWE Intern',
  'Software Engineer',
  'Senior Engineer',
  'Cybersecurity',
  'Data Science',
  'DevOps / Cloud',
  'Product Management',
] as const;

/** Friendly labels for known profile sub-keys */
const PROFILE_KEY_LABELS: Record<string, string> = {
  company_pref: 'Company Style',
  difficulty_pref: 'Difficulty',
  focus_pref: 'Focus Area',
  years_experience: 'Experience',
  location: 'Location',
};

export const ProfileModal = ({ open, onClose }: ProfileModalProps) => {
  const { user, setUser } = useAuthStore();
  const [fullName, setFullName] = useState('');
  const [rolePref, setRolePref] = useState('');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [mounted, setMounted] = useState(false);

  // Client-only mount flag for portal
  useEffect(() => setMounted(true), []);

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setFullName(user?.full_name || '');
      setRolePref(user?.role_pref || '');
      setFeedback(null);
    }
  }, [open, user]);

  // Escape key closes
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Lock body scroll while open
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Filter profile entries — skip avatar/url keys the user doesn't need to see
  const extraDetails = useMemo(() => {
    if (!user?.profile) return [];
    const skip = new Set(['avatar_url', 'avatar', 'profile_picture', 'image_url']);
    return Object.entries(user.profile).filter(
      ([key, val]) => val != null && val !== '' && !skip.has(key)
    );
  }, [user]);

  const handleSave = useCallback(async () => {
    if (!user || saving) return;
    setSaving(true);
    setFeedback(null);
    try {
      const updated = await authService.updateProfile({
        full_name: fullName.trim() || null,
        role_pref: rolePref || undefined,
        profile: user.profile || undefined,
      });
      setUser(updated);
      if (typeof window !== 'undefined') {
        localStorage.setItem('user', JSON.stringify(updated));
      }
      setFeedback({ type: 'success', msg: 'Profile saved successfully.' });
      setTimeout(onClose, 800);
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err?.message || 'Failed to save profile.' });
    } finally {
      setSaving(false);
    }
  }, [user, fullName, rolePref, saving, onClose, setUser]);

  if (!open || !mounted) return null;

  // Derive initials (up to 2 chars from full name, else first char of email)
  const initials = user?.full_name
    ? user.full_name
        .split(/\s+/)
        .map((w) => w[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : (user?.email?.[0] || 'U').toUpperCase();

  const displayEmail = user?.email || '—';

  // Render via portal so it's never trapped inside the header stacking context
  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="profile-title"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={onClose} />

      {/* Card */}
      <div
        className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200/60 dark:border-slate-700/60 flex flex-col max-h-[min(88vh,700px)] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="px-6 pt-6 pb-4 flex items-start gap-4 flex-shrink-0">
          <div className="w-[52px] h-[52px] rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-lg flex-shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h2 id="profile-title" className="text-xl font-bold text-slate-900 dark:text-white truncate">
              {user?.full_name || 'Your Profile'}
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 truncate mt-0.5">{displayEmail}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 -mt-1 -mr-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex-shrink-0"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ── Body (scrollable) ── */}
        <div className="flex-1 overflow-y-auto px-6 pb-2 space-y-5 overscroll-contain">
          {/* Feedback */}
          {feedback && (
            <div
              className={`rounded-lg px-3.5 py-2.5 text-sm flex items-center gap-2.5 ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                  : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
              }`}
            >
              <span className="text-base leading-none">{feedback.type === 'success' ? '✓' : '✕'}</span>
              <span>{feedback.msg}</span>
            </div>
          )}

          {/* Full Name */}
          <fieldset className="space-y-1.5">
            <label htmlFor="pf-name" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Full Name
            </label>
            <input
              id="pf-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Jane Doe"
              autoComplete="name"
              className="w-full h-10 px-3.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition"
            />
          </fieldset>

          {/* Interview Role */}
          <fieldset className="space-y-1.5">
            <label htmlFor="pf-role" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Interview Role
            </label>
            <select
              id="pf-role"
              value={rolePref}
              onChange={(e) => setRolePref(e.target.value)}
              className="w-full h-10 px-3.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition cursor-pointer appearance-none"
            >
              <option value="">Select a role…</option>
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </fieldset>

          {/* Email (read-only) */}
          <fieldset className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
            <div className="w-full h-10 px-3.5 flex items-center rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 text-sm select-all">
              {displayEmail}
            </div>
          </fieldset>

          {/* Extra profile details */}
          {extraDetails.length > 0 && (
            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Additional Details
              </p>
              <div className="grid grid-cols-2 gap-2">
                {extraDetails.map(([key, value]) => (
                  <div
                    key={key}
                    className="rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60 px-3 py-2"
                  >
                    <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500 leading-tight">
                      {PROFILE_KEY_LABELS[key] || key.replace(/_/g, ' ')}
                    </div>
                    <div className="text-sm text-slate-800 dark:text-slate-200 mt-0.5 break-words">
                      {String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-end gap-2.5 flex-shrink-0 bg-slate-50/80 dark:bg-slate-800/40 rounded-b-2xl">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || feedback?.type === 'success'}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
          >
            {saving && (
              <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
