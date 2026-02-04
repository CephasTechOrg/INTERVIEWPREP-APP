'use client';

import { useUIStore } from '@/lib/stores/uiStore';
import { useAuthStore } from '@/lib/stores/authStore';

export const SettingsSection = () => {
  const { theme, setTheme, voiceEnabled, setVoiceEnabled } = useUIStore();
  const { user } = useAuthStore();

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Settings</h2>
        <p className="text-gray-600">Manage your preferences and profile.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profile */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Profile</h3>
          <div className="space-y-2 text-sm text-gray-700">
            <p><span className="font-semibold">Email:</span> {user?.email || 'Not set'}</p>
            <p><span className="font-semibold">Full Name:</span> {user?.full_name || 'Not set'}</p>
            <p><span className="font-semibold">Role:</span> {user?.role_pref || 'Not set'}</p>
          </div>
        </div>

        {/* Preferences */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Preferences</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-700">Theme</span>
              <button
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                {theme === 'light' ? 'Light' : 'Dark'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-700">Voice Output</span>
              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`px-4 py-2 rounded-lg ${
                  voiceEnabled ? 'bg-blue-600 text-white' : 'bg-gray-100'
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
