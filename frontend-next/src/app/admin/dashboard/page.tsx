'use client';

import { useEffect, useState } from 'react';
import { adminService, SystemHealth } from '@/lib/services/adminService';
import {
  UsersIcon,
  CheckCircleIcon,
  BanIcon,
  MicrophoneIcon,
  QuestionIcon,
  ChartIcon,
  RefreshIcon,
} from '@/components/icons/AdminIcons';

interface Stats {
  total_users: number;
  verified_users: number;
  banned_users: number;
  active_interviews: number;
  total_questions: number;
}

type ServiceKey = 'database' | 'ai' | 'sendgrid' | 'supabase';

const SERVICE_META: Record<ServiceKey, { label: string; sub: (s: NonNullable<SystemHealth['services'][ServiceKey]>) => string }> = {
  database: {
    label: 'Database',
    sub: (s) => s.type === 'supabase' ? 'Supabase PostgreSQL' : 'Local PostgreSQL',
  },
  ai: {
    label: 'AI Model (DeepSeek)',
    sub: (s) => s.fallback_mode ? 'Fallback mode active' : (s.model || 'deepseek-chat'),
  },
  sendgrid: {
    label: 'Email (SendGrid)',
    sub: (s) => s.note || (s.configured ? 'SendGrid API' : 'Dev console mode'),
  },
  supabase: {
    label: 'Supabase Storage',
    sub: (s) => s.url ? s.url.replace('https://', '').split('.')[0] + '.supabase.co' : 'Not configured',
  },
};

function StatusDot({ status }: { status: string }) {
  const styles: Record<string, string> = {
    online: 'bg-emerald-500 animate-pulse shadow-emerald-500/50 shadow-sm',
    offline: 'bg-red-500',
    error: 'bg-red-400',
    unconfigured: 'bg-slate-400',
  };
  return <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${styles[status] || 'bg-slate-400'}`} />;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    online: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    offline: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    error: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    unconfigured: 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
  };
  const labels: Record<string, string> = {
    online: 'Online',
    offline: 'Offline',
    error: 'Error',
    unconfigured: 'Not Configured',
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${styles[status] || styles.unconfigured}`}>
      {labels[status] || status}
    </span>
  );
}

function SystemHealthPanel() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);

  const doFetch = async () => {
    setLoading(true);
    setFetchError(false);
    try {
      const data = await adminService.getSystemHealth();
      setHealth(data);
    } catch {
      setFetchError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { doFetch(); }, []);

  const services = health?.services;
  const allOnline = services && Object.values(services).every(s => s.status === 'online');
  const anyOffline = services && Object.values(services).some(s => s.status === 'offline' || s.status === 'error');

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white">System Health</h3>
          {!loading && services && (
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              allOnline
                ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                : anyOffline
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                  : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
            }`}>
              {allOnline ? 'All Systems Operational' : anyOffline ? 'Degraded' : 'Partial'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {health?.timestamp && (
            <span className="text-xs text-slate-400">
              Checked {new Date(health.timestamp).toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={doFetch}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 transition-colors"
            title="Refresh health"
          >
            <RefreshIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Service rows */}
      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {fetchError ? (
          <div className="px-6 py-4 text-sm text-red-600 dark:text-red-400">
            Failed to load health status.{' '}
            <button onClick={doFetch} className="underline">Retry</button>
          </div>
        ) : (
          (['database', 'ai', 'sendgrid', 'supabase'] as ServiceKey[]).map((key) => {
            const svc = services?.[key];
            const meta = SERVICE_META[key];
            return (
              <div key={key} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <StatusDot status={loading ? 'unconfigured' : (svc?.status || 'unconfigured')} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-800 dark:text-white">{meta.label}</p>
                      <p className="text-xs text-slate-400 truncate">
                        {loading ? 'Checking...' : svc ? meta.sub(svc) : '—'}
                      </p>
                    </div>
                  </div>
                  {loading ? (
                    <span className="text-xs text-slate-400 animate-pulse">...</span>
                  ) : (
                    <StatusBadge status={svc?.status || 'unconfigured'} />
                  )}
                </div>

                {/* Warnings / errors */}
                {!loading && svc?.status === 'online' && key === 'ai' && svc.fallback_mode && (
                  <div className="mt-2 ml-5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-1.5 text-xs text-amber-700 dark:text-amber-400">
                    Fallback mode active — AI responses may be limited.
                  </div>
                )}
                {!loading && (svc?.status === 'offline' || svc?.status === 'error') && svc?.error && (
                  <div className="mt-2 ml-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-3 py-1.5 text-xs text-red-600 dark:text-red-400 break-all">
                    {svc.error}
                  </div>
                )}
                {!loading && key === 'ai' && svc?.last_error && svc.status !== 'online' && (
                  <div className="mt-2 ml-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-3 py-1.5">
                    <p className="text-xs font-medium text-red-700 dark:text-red-400">Last error</p>
                    <p className="text-xs text-red-500 break-all">{svc.last_error}</p>
                    {svc.last_error_at && (
                      <p className="text-xs text-red-400 mt-0.5">{new Date(svc.last_error_at * 1000).toLocaleString()}</p>
                    )}
                  </div>
                )}
                {!loading && svc?.status === 'unconfigured' && (
                  <div className="mt-1 ml-5 text-xs text-slate-400">
                    {svc.error || 'Not configured in environment'}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await adminService.getStats();
      setStats(data);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj?.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
          <RefreshIcon className="w-5 h-5 animate-spin" />
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-lg">
        <p className="font-medium">Error loading dashboard</p>
        <p className="text-sm mt-1">{error}</p>
        <button
          onClick={fetchStats}
          className="mt-3 text-sm font-medium text-red-600 dark:text-red-400 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!stats) {
    return <div className="text-center py-8 text-slate-600 dark:text-slate-400">No data available</div>;
  }

  const statCards = [
    {
      title: 'Total Users',
      value: stats.total_users,
      icon: UsersIcon,
      bgColor: 'bg-blue-500',
      lightBg: 'bg-blue-50 dark:bg-blue-900/20',
      iconColor: 'text-blue-500',
    },
    {
      title: 'Verified Users',
      value: stats.verified_users,
      icon: CheckCircleIcon,
      bgColor: 'bg-emerald-500',
      lightBg: 'bg-emerald-50 dark:bg-emerald-900/20',
      iconColor: 'text-emerald-500',
    },
    {
      title: 'Banned Users',
      value: stats.banned_users,
      icon: BanIcon,
      bgColor: 'bg-red-500',
      lightBg: 'bg-red-50 dark:bg-red-900/20',
      iconColor: 'text-red-500',
    },
    {
      title: 'Active Interviews',
      value: stats.active_interviews,
      icon: MicrophoneIcon,
      bgColor: 'bg-purple-500',
      lightBg: 'bg-purple-50 dark:bg-purple-900/20',
      iconColor: 'text-purple-500',
    },
    {
      title: 'Total Questions',
      value: stats.total_questions,
      icon: QuestionIcon,
      bgColor: 'bg-amber-500',
      lightBg: 'bg-amber-50 dark:bg-amber-900/20',
      iconColor: 'text-amber-500',
    },
  ];

  const verificationRate = stats.total_users > 0 ? ((stats.verified_users / stats.total_users) * 100).toFixed(1) : '0';
  const banRate = stats.total_users > 0 ? ((stats.banned_users / stats.total_users) * 100).toFixed(2) : '0';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Dashboard</h1>
          <p className="text-slate-600 dark:text-slate-400">Welcome to the InterviewPrep admin panel</p>
        </div>
        <button
          onClick={fetchStats}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
        >
          <RefreshIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{card.title}</p>
                  <p className="text-2xl font-bold text-slate-800 dark:text-white mt-1">
                    {card.value.toLocaleString()}
                  </p>
                </div>
                <div className={`p-3 rounded-lg ${card.lightBg}`}>
                  <Icon className={`w-6 h-6 ${card.iconColor}`} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Analytics Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Verification Rate */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <ChartIcon className="w-5 h-5 text-blue-500" />
            </div>
            <h3 className="text-lg font-semibold text-slate-800 dark:text-white">User Verification Rate</h3>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-bold text-slate-800 dark:text-white">{verificationRate}%</span>
            <span className="text-sm text-slate-500 dark:text-slate-400 mb-1">of users verified</span>
          </div>
          <div className="mt-4 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${verificationRate}%` }}
            />
          </div>
        </div>

        {/* Quick Stats */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">Quick Stats</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="border-l-4 border-red-500 pl-4 py-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">Ban Rate</p>
              <p className="text-xl font-semibold text-slate-800 dark:text-white">{banRate}%</p>
            </div>
            <div className="border-l-4 border-amber-500 pl-4 py-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">Unverified Users</p>
              <p className="text-xl font-semibold text-slate-800 dark:text-white">
                {stats.total_users - stats.verified_users}
              </p>
            </div>
            <div className="border-l-4 border-purple-500 pl-4 py-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">Active Interviews</p>
              <p className="text-xl font-semibold text-slate-800 dark:text-white">{stats.active_interviews}</p>
            </div>
            <div className="border-l-4 border-emerald-500 pl-4 py-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">Questions in System</p>
              <p className="text-xl font-semibold text-slate-800 dark:text-white">{stats.total_questions}</p>
            </div>
          </div>
        </div>
      </div>

      {/* System Health */}
      <SystemHealthPanel />
    </div>
  );
}
