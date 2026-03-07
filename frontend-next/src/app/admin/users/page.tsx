'use client';

import { useEffect, useState, useCallback } from 'react';
import { adminService, UserFullDetail } from '@/lib/services/adminService';
import { RefreshIcon, CheckCircleIcon, BanIcon } from '@/components/icons/AdminIcons';

interface User {
  id: number;
  email: string;
  full_name?: string;
  is_verified: boolean;
  is_banned: boolean;
  ban_reason?: string;
  created_at: string;
}

const CHAT_DAILY_LIMIT = 30;
const TTS_MONTHLY_LIMIT = 3000;

function UsageBar({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1 text-slate-600 dark:text-slate-400">
        <span>{label}</span>
        <span>{value.toLocaleString()} / {max.toLocaleString()}</span>
      </div>
      <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-400 text-xs">-</span>;
  const color =
    score >= 80 ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' :
    score >= 60 ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' :
    score >= 40 ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' :
    'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>{score}</span>;
}

function UserDetailDrawer({
  userId,
  onClose,
  onBan,
  onDelete,
}: {
  userId: number;
  onClose: () => void;
  onBan: (user: User) => void;
  onDelete: (user: User) => void;
}) {
  const [detail, setDetail] = useState<UserFullDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState('');

  useEffect(() => {
    adminService.getUserFullDetail(userId).then((d) => {
      setDetail(d);
      setLoading(false);
    });
  }, [userId]);

  const handleResetUsage = async () => {
    if (!detail) return;
    setResetting(true);
    try {
      await adminService.resetUserUsage(userId);
      const updated = await adminService.getUserFullDetail(userId);
      setDetail(updated);
      setResetMsg('Usage reset successfully');
      setTimeout(() => setResetMsg(''), 3000);
    } catch {
      setResetMsg('Failed to reset usage');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/40" onClick={onClose} />

      {/* Drawer panel */}
      <div className="w-full max-w-lg bg-white dark:bg-slate-900 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-bold text-slate-800 dark:text-white">User Detail</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-slate-500 dark:text-slate-400">
            <RefreshIcon className="w-5 h-5 animate-spin mr-2" /> Loading...
          </div>
        ) : !detail ? (
          <div className="flex-1 flex items-center justify-center text-red-500">Failed to load</div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* User info */}
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
                {(detail.full_name || detail.email).charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-slate-800 dark:text-white truncate">{detail.full_name || 'No name'}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400 truncate">{detail.email}</p>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${detail.is_verified ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'}`}>
                    {detail.is_verified ? 'Verified' : 'Unverified'}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${detail.is_banned ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' : 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'}`}>
                    {detail.is_banned ? 'Banned' : 'Active'}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                    {detail.role_pref}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-slate-500 dark:text-slate-400 text-xs">Joined</p>
                <p className="text-slate-800 dark:text-white font-medium">{new Date(detail.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-slate-500 dark:text-slate-400 text-xs">Last Login</p>
                <p className="text-slate-800 dark:text-white font-medium">{detail.last_login_at ? new Date(detail.last_login_at).toLocaleDateString() : '—'}</p>
              </div>
              <div>
                <p className="text-slate-500 dark:text-slate-400 text-xs">Feedback Submitted</p>
                <p className="text-slate-800 dark:text-white font-medium">{detail.feedback_count}</p>
              </div>
              {detail.is_banned && detail.ban_reason && (
                <div className="col-span-2">
                  <p className="text-slate-500 dark:text-slate-400 text-xs">Ban Reason</p>
                  <p className="text-red-600 dark:text-red-400 font-medium">{detail.ban_reason}</p>
                </div>
              )}
            </div>

            {/* Rate limits */}
            <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold text-slate-800 dark:text-white text-sm">Rate Limit Usage</h3>
                <button
                  onClick={handleResetUsage}
                  disabled={resetting}
                  className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {resetting ? 'Resetting...' : 'Reset Limits'}
                </button>
              </div>
              {resetMsg && <p className="text-xs text-emerald-600 dark:text-emerald-400">{resetMsg}</p>}
              {detail.usage ? (
                <>
                  <UsageBar
                    label="Chat messages today"
                    value={detail.usage.chat_messages_today}
                    max={CHAT_DAILY_LIMIT}
                  />
                  <UsageBar
                    label="TTS characters this month"
                    value={detail.usage.tts_characters_month}
                    max={TTS_MONTHLY_LIMIT}
                  />
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    {[
                      { label: 'Total chats', value: detail.usage.total_chat_messages },
                      { label: 'Total TTS chars', value: detail.usage.total_tts_characters },
                      { label: 'Total sessions', value: detail.usage.total_interview_sessions },
                    ].map((s) => (
                      <div key={s.label} className="text-center">
                        <p className="text-lg font-bold text-slate-800 dark:text-white">{s.value.toLocaleString()}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{s.label}</p>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-400">No usage data recorded yet</p>
              )}
            </div>

            {/* Recent sessions */}
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-white text-sm mb-3">
                Recent Sessions ({detail.sessions.length})
              </h3>
              {detail.sessions.length === 0 ? (
                <p className="text-sm text-slate-400">No sessions yet</p>
              ) : (
                <div className="space-y-2">
                  {detail.sessions.map((s) => (
                    <div key={s.id} className="flex items-center justify-between bg-slate-50 dark:bg-slate-800 rounded-lg px-3 py-2 text-sm">
                      <div className="min-w-0 flex-1">
                        <p className="text-slate-800 dark:text-white font-medium truncate capitalize">
                          {s.track.replace(/_/g, ' ')} · {s.difficulty}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {s.company_style} · {s.stage === 'done' ? 'Completed' : `In progress (${s.stage})`}
                          {s.created_at ? ` · ${new Date(s.created_at).toLocaleDateString()}` : ''}
                        </p>
                      </div>
                      <ScoreBadge score={s.overall_score} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => onBan(detail as unknown as User)}
                className={`flex-1 px-4 py-2.5 rounded-lg font-medium text-sm transition-colors ${
                  detail.is_banned
                    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-200'
                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200'
                }`}
              >
                {detail.is_banned ? 'Unban User' : 'Ban User'}
              </button>
              <button
                onClick={() => onDelete(detail as unknown as User)}
                className="flex-1 px-4 py-2.5 rounded-lg font-medium text-sm bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                Delete User
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterBanned, setFilterBanned] = useState<'all' | 'banned' | 'active'>('all');
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const limit = 50;

  const [detailUserId, setDetailUserId] = useState<number | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const filterValue = filterBanned === 'banned' ? true : filterBanned === 'active' ? false : undefined;
      const data = await adminService.getUsers(skip, limit, filterValue, search || undefined);
      setUsers(data.users);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj?.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [skip, filterBanned, search]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearch = () => {
    setSearch(searchInput);
    setSkip(0);
  };

  const handleBanClick = (user: User) => {
    setSelectedUser(user);
    setBanReason(user.ban_reason || '');
    setShowModal(true);
    setDetailUserId(null);
  };

  const handleDeleteClick = (user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
    setDetailUserId(null);
  };

  const handleConfirmDelete = async () => {
    if (!selectedUser) return;
    try {
      setActionLoading(true);
      await adminService.deleteUser(selectedUser.id);
      await fetchUsers();
      setShowDeleteModal(false);
      setSelectedUser(null);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      alert(errorObj?.message || 'Failed to delete user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmBan = async () => {
    if (!selectedUser) return;
    try {
      setActionLoading(true);
      if (selectedUser.is_banned) {
        await adminService.unbanUser(selectedUser.id);
      } else {
        await adminService.banUser(selectedUser.id, banReason);
      }
      await fetchUsers();
      setShowModal(false);
      setSelectedUser(null);
      setBanReason('');
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      alert(errorObj?.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
          <RefreshIcon className="w-5 h-5 animate-spin" />
          <span>Loading users...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-lg">
        <p className="font-medium">Error loading users</p>
        <p className="text-sm mt-1">{error}</p>
        <button onClick={fetchUsers} className="mt-3 text-sm font-medium text-red-600 dark:text-red-400 hover:underline">
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">User Management</h1>
          <p className="text-slate-600 dark:text-slate-400">View and manage user accounts — <span className="text-blue-500">click any row</span> to see sessions, usage & rate limits</p>
        </div>
        <button
          onClick={fetchUsers}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
        >
          <RefreshIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters + Search */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex gap-2">
            {(['all', 'active', 'banned'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => { setFilterBanned(filter); setSkip(0); }}
                className={`px-4 py-2 rounded-lg font-medium transition-colors text-sm ${
                  filterBanned === filter
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                }`}
              >
                {filter === 'all' ? 'All Users' : filter === 'active' ? 'Active' : 'Banned'}
              </button>
            ))}
          </div>
          <div className="flex gap-2 flex-1">
            <input
              type="text"
              placeholder="Search by email or name..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1 px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-800 dark:text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Search
            </button>
            {search && (
              <button
                onClick={() => { setSearch(''); setSearchInput(''); setSkip(0); }}
                className="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Email</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Name</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Verified</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Status</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Joined</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500 dark:text-slate-400">
                  {search ? `No users matching "${search}"` : 'No users found'}
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr
                  key={user.id}
                  className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
                  onClick={() => setDetailUserId(user.id)}
                >
                  <td className="px-6 py-4 text-sm text-slate-800 dark:text-white font-medium">{user.email}</td>
                  <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">{user.full_name || '-'}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                      user.is_verified
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                        : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                    }`}>
                      {user.is_verified ? <><CheckCircleIcon className="w-3.5 h-3.5" /> Verified</> : 'Pending'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {user.is_banned ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-full text-xs font-medium">
                        <BanIcon className="w-3.5 h-3.5" /> Banned
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-full text-xs font-medium">
                        <CheckCircleIcon className="w-3.5 h-3.5" /> Active
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-sm" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-2 flex-wrap">
                      <button
                        onClick={() => setDetailUserId(user.id)}
                        className="px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                      >
                        Details
                      </button>
                      <button
                        onClick={() => handleBanClick(user)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          user.is_banned
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-200 dark:hover:bg-emerald-900/50'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
                        }`}
                      >
                        {user.is_banned ? 'Unban' : 'Ban'}
                      </button>
                      <button
                        onClick={() => handleDeleteClick(user)}
                        className="px-3 py-1.5 rounded-lg text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex gap-2 justify-center items-center">
        <button
          onClick={() => setSkip(Math.max(0, skip - limit))}
          disabled={skip === 0}
          className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          Previous
        </button>
        <span className="px-4 py-2 text-slate-600 dark:text-slate-400">Page {Math.floor(skip / limit) + 1}</span>
        <button
          onClick={() => setSkip(skip + limit)}
          disabled={users.length < limit}
          className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          Next
        </button>
      </div>

      {/* User Detail Drawer */}
      {detailUserId !== null && (
        <UserDetailDrawer
          userId={detailUserId}
          onClose={() => setDetailUserId(null)}
          onBan={handleBanClick}
          onDelete={handleDeleteClick}
        />
      )}

      {/* Ban Modal */}
      {showModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 max-w-md w-full border border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-2">
              {selectedUser.is_banned ? 'Unban User' : 'Ban User'}
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-4">{selectedUser.email}</p>
            {!selectedUser.is_banned && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Reason (optional)</label>
                <textarea
                  value={banReason}
                  onChange={(e) => setBanReason(e.target.value)}
                  placeholder="Why are you banning this user?"
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  rows={3}
                />
              </div>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2.5 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors font-medium"
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmBan}
                className={`flex-1 px-4 py-2.5 text-white rounded-lg transition-colors font-medium ${selectedUser.is_banned ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}`}
                disabled={actionLoading}
              >
                {actionLoading ? 'Processing...' : selectedUser.is_banned ? 'Unban' : 'Ban'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 max-w-md w-full border border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-2">Delete User</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-2">Are you sure you want to permanently delete this user?</p>
            <p className="text-slate-800 dark:text-white font-medium mb-4">{selectedUser.email}</p>
            <p className="text-red-600 dark:text-red-400 text-sm mb-4">
              ⚠️ This action cannot be undone. All user data including interviews and messages will be deleted.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowDeleteModal(false); setSelectedUser(null); }}
                className="flex-1 px-4 py-2.5 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors font-medium"
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-medium"
                disabled={actionLoading}
              >
                {actionLoading ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
