'use client';

import { useEffect, useState } from 'react';
import { adminService } from '@/lib/services/adminService';
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
    </div>
  );
}
