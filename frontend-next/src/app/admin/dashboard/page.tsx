'use client';

import { useEffect, useState } from 'react';
import { adminService } from '@/lib/services/adminService';

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
      const data = await adminService.getStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded">{error}</div>;
  }

  if (!stats) {
    return <div className="text-center py-8">No data available</div>;
  }

  const StatCard = ({
    title,
    value,
    icon,
    bgColor,
  }: {
    title: string;
    value: number;
    icon: string;
    bgColor: string;
  }) => (
    <div className={`${bgColor} rounded-lg shadow p-6 text-white`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm opacity-90">{title}</p>
          <p className="text-3xl font-bold mt-1">{value.toLocaleString()}</p>
        </div>
        <div className="text-4xl opacity-50">{icon}</div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Dashboard</h1>
        <p className="text-gray-600">Welcome to the InterviewPrep admin panel</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Users"
          value={stats.total_users}
          icon="👥"
          bgColor="bg-blue-500"
        />
        <StatCard
          title="Verified Users"
          value={stats.verified_users}
          icon="✓"
          bgColor="bg-green-500"
        />
        <StatCard
          title="Banned Users"
          value={stats.banned_users}
          icon="🚫"
          bgColor="bg-red-500"
        />
        <StatCard
          title="Active Interviews"
          value={stats.active_interviews}
          icon="🎤"
          bgColor="bg-purple-500"
        />
        <StatCard
          title="Total Questions"
          value={stats.total_questions}
          icon="❓"
          bgColor="bg-orange-500"
        />
        <div className="bg-indigo-500 rounded-lg shadow p-6 text-white flex items-center justify-between">
          <div>
            <p className="text-sm opacity-90">User Verification Rate</p>
            <p className="text-3xl font-bold mt-1">
              {stats.total_users > 0 ? ((stats.verified_users / stats.total_users) * 100).toFixed(1) : 0}%
            </p>
          </div>
          <div className="text-4xl opacity-50">📈</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Quick Stats</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="border-l-4 border-blue-500 pl-4 py-2">
            <p className="text-gray-600">Ban Rate</p>
            <p className="text-xl font-semibold text-gray-800">
              {stats.total_users > 0 ? ((stats.banned_users / stats.total_users) * 100).toFixed(2) : 0}%
            </p>
          </div>
          <div className="border-l-4 border-green-500 pl-4 py-2">
            <p className="text-gray-600">Unverified Users</p>
            <p className="text-xl font-semibold text-gray-800">
              {stats.total_users - stats.verified_users}
            </p>
          </div>
          <div className="border-l-4 border-purple-500 pl-4 py-2">
            <p className="text-gray-600">Active Interviews</p>
            <p className="text-xl font-semibold text-gray-800">{stats.active_interviews}</p>
          </div>
          <div className="border-l-4 border-orange-500 pl-4 py-2">
            <p className="text-gray-600">Questions in System</p>
            <p className="text-xl font-semibold text-gray-800">{stats.total_questions}</p>
          </div>
        </div>
      </div>

      <button
        onClick={fetchStats}
        className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
      >
        Refresh Stats
      </button>
    </div>
  );
}
