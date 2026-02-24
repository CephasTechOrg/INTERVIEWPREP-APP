'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUIStore } from '@/lib/stores/uiStore';
import { useAuthStore } from '@/lib/stores/authStore';
import { authService } from '@/lib/services/authService';
import { Icons } from '@/components/ui/Icons';

export const SettingsSection = () => {
  const router = useRouter();
  const {
    theme,
    setTheme,
    voiceEnabled,
    setVoiceEnabled,
    reduceMotion,
    setReduceMotion,
    highContrast,
    setHighContrast,
    fontScale,
    setFontScale,
    emailNotifications,
    setEmailNotifications,
    productUpdates,
    setProductUpdates,
  } = useUIStore();
  const { user, logout } = useAuthStore();
  const [deactivateOpen, setDeactivateOpen] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [openSection, setOpenSection] = useState<'profile' | 'preferences' | 'accessibility' | 'notifications' | 'security' | 'danger'>('profile');

  const handleDeactivate = async () => {
    try {
      setDeactivating(true);
      await authService.deactivateAccount();
      logout();
      router.push('/login');
    } catch {
      alert('Failed to deactivate account. Please try again.');
    } finally {
      setDeactivating(false);
      setDeactivateOpen(false);
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Settings</h2>
        <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Modern, organized controls for your account and preferences.</p>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm divide-y divide-slate-200 dark:divide-slate-800">
        {/* Profile */}
        <button
          onClick={() => setOpenSection(openSection === 'profile' ? 'preferences' : 'profile')}
          className="w-full flex items-center justify-between px-4 sm:px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-slate-600 dark:text-slate-300">{Icons.userCircle}</span>
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Profile</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Personal and account details</p>
            </div>
          </div>
          <span className="text-slate-500">{openSection === 'profile' ? Icons.arrowUp : Icons.arrowDown}</span>
        </button>
        {openSection === 'profile' && (
          <div className="px-4 sm:px-6 py-5 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 text-white flex items-center justify-center font-semibold">
                {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div>
                <p className="font-semibold text-slate-900 dark:text-white">{user?.full_name || 'User'}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{user?.email || 'Not set'}</p>
              </div>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400">Role</p>
              <p className="font-medium text-slate-900 dark:text-white">{user?.role_pref || 'Not set'}</p>
            </div>
          </div>
        )}

        {/* Preferences */}
        <button
          onClick={() => setOpenSection(openSection === 'preferences' ? 'accessibility' : 'preferences')}
          className="w-full flex items-center justify-between px-4 sm:px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-slate-600 dark:text-slate-300">{Icons.palette}</span>
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Preferences</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Theme, voice, layout</p>
            </div>
          </div>
          <span className="text-slate-500">{openSection === 'preferences' ? Icons.arrowUp : Icons.arrowDown}</span>
        </button>
        {openSection === 'preferences' && (
          <div className="px-4 sm:px-6 py-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">Theme</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Choose light or dark mode</p>
              </div>
              <button
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors text-sm"
              >
                {theme === 'light' ? 'Light' : 'Dark'}
              </button>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">Voice Output</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Enable text-to-speech responses</p>
              </div>
              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`px-4 py-2 rounded-lg transition-colors text-sm ${
                  voiceEnabled ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                }`}
              >
                {voiceEnabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
          </div>
        )}

        {/* Accessibility */}
        <button
          onClick={() => setOpenSection(openSection === 'accessibility' ? 'notifications' : 'accessibility')}
          className="w-full flex items-center justify-between px-4 sm:px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-slate-600 dark:text-slate-300">{Icons.accessibility}</span>
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Accessibility</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Reduce motion, contrast, text size</p>
            </div>
          </div>
          <span className="text-slate-500">{openSection === 'accessibility' ? Icons.arrowUp : Icons.arrowDown}</span>
        </button>
        {openSection === 'accessibility' && (
          <div className="px-4 sm:px-6 py-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">Reduce Motion</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Minimize animations and transitions</p>
              </div>
              <button
                onClick={() => setReduceMotion(!reduceMotion)}
                className={`px-4 py-2 rounded-lg transition-colors text-sm ${
                  reduceMotion ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                }`}
              >
                {reduceMotion ? 'On' : 'Off'}
              </button>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">High Contrast</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Improve text and UI contrast</p>
              </div>
              <button
                onClick={() => setHighContrast(!highContrast)}
                className={`px-4 py-2 rounded-lg transition-colors text-sm ${
                  highContrast ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                }`}
              >
                {highContrast ? 'On' : 'Off'}
              </button>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">Text Size</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Adjust global font scale</p>
                </div>
                <span className="text-sm font-medium text-slate-900 dark:text-white">{fontScale}%</span>
              </div>
              <input
                type="range"
                min={90}
                max={115}
                step={5}
                value={fontScale}
                onChange={(e) => setFontScale(Number(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>
          </div>
        )}

        {/* Notifications */}
        <button
          onClick={() => setOpenSection(openSection === 'notifications' ? 'security' : 'notifications')}
          className="w-full flex items-center justify-between px-4 sm:px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-slate-600 dark:text-slate-300">{Icons.bell}</span>
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Notifications</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Email summaries and product updates</p>
            </div>
          </div>
          <span className="text-slate-500">{openSection === 'notifications' ? Icons.arrowUp : Icons.arrowDown}</span>
        </button>
        {openSection === 'notifications' && (
          <div className="px-4 sm:px-6 py-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">Email Notifications</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Session summaries and alerts</p>
              </div>
              <button
                onClick={() => setEmailNotifications(!emailNotifications)}
                className={`px-4 py-2 rounded-lg transition-colors text-sm ${
                  emailNotifications ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                }`}
              >
                {emailNotifications ? 'On' : 'Off'}
              </button>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">Product Updates</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">New features and improvements</p>
              </div>
              <button
                onClick={() => setProductUpdates(!productUpdates)}
                className={`px-4 py-2 rounded-lg transition-colors text-sm ${
                  productUpdates ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                }`}
              >
                {productUpdates ? 'On' : 'Off'}
              </button>
            </div>
          </div>
        )}

        {/* Security */}
        <button
          onClick={() => setOpenSection(openSection === 'security' ? 'danger' : 'security')}
          className="w-full flex items-center justify-between px-4 sm:px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-slate-600 dark:text-slate-300">{Icons.shield}</span>
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Security</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Password and verification</p>
            </div>
          </div>
          <span className="text-slate-500">{openSection === 'security' ? Icons.arrowUp : Icons.arrowDown}</span>
        </button>
        {openSection === 'security' && (
          <div className="px-4 sm:px-6 py-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={() => router.push('/reset-password')}
              className="px-4 py-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-900 dark:text-white text-sm transition"
            >
              Change Password
            </button>
            <button
              onClick={() => router.push('/verify')}
              className="px-4 py-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-900 dark:text-white text-sm transition"
            >
              Verify Email
            </button>
          </div>
        )}

        {/* Danger Zone */}
        <button
          onClick={() => setOpenSection(openSection === 'danger' ? 'profile' : 'danger')}
          className="w-full flex items-center justify-between px-4 sm:px-6 py-4 hover:bg-rose-50 dark:hover:bg-rose-900/10 text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-rose-600 dark:text-rose-400">{Icons.warning}</span>
            <div>
              <p className="text-sm font-semibold text-rose-600 dark:text-rose-400">Danger Zone</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Deactivate your account</p>
            </div>
          </div>
          <span className="text-slate-500">{openSection === 'danger' ? Icons.arrowUp : Icons.arrowDown}</span>
        </button>
        {openSection === 'danger' && (
          <div className="px-4 sm:px-6 py-5">
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
              Deactivating your account will log you out and disable access until reactivated by support.
            </p>
            <button
              onClick={() => setDeactivateOpen(true)}
              className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-sm font-semibold transition"
            >
              Deactivate Account
            </button>
          </div>
        )}
      </div>

      {deactivateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 w-full max-w-md shadow-xl">
            <h4 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Deactivate account?</h4>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
              This will immediately deactivate your account and sign you out. You can reactivate by contacting support.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setDeactivateOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleDeactivate}
                disabled={deactivating}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold disabled:opacity-70"
              >
                {deactivating ? 'Deactivating...' : 'Deactivate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
