'use client';

import { useUIStore } from '@/lib/stores/uiStore';
import { useAuthStore } from '@/lib/stores/authStore';

export const SettingsSection = () => {
  const { theme, setTheme, voiceEnabled, setVoiceEnabled } = useUIStore();
  const { user } = useAuthStore();

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Settings</h2>
        <p className="text-slate-600 dark:text-slate-400">Manage your preferences and profile.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profile */}
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Profile</h3>
          <div className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
            <p><span className="font-semibold">Email:</span> {user?.email || 'Not set'}</p>
            <p><span className="font-semibold">Full Name:</span> {user?.full_name || 'Not set'}</p>
            <p><span className="font-semibold">Role:</span> {user?.role_pref || 'Not set'}</p>
          </div>
        </div>

        {/* Preferences */}
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Preferences</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-700 dark:text-slate-300">Theme</span>
              <button
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                {theme === 'light' ? '☀️ Light' : '🌙 Dark'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-700 dark:text-slate-300">Voice Output</span>
              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  voiceEnabled ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white'
                }`}
              >
                {voiceEnabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
