'use client';

import { useEffect, useState } from 'react';
import { adminService } from '@/lib/services/adminService';
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

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterBanned, setFilterBanned] = useState<'all' | 'banned' | 'active'>('all');
  const [skip, setSkip] = useState(0);
  const limit = 50;
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, [skip, filterBanned]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError('');
      const filterValue = filterBanned === 'banned' ? true : filterBanned === 'active' ? false : undefined;
      const data = await adminService.getUsers(skip, limit, filterValue);
      setUsers(data.users);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj?.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleBanClick = (user: User) => {
    setSelectedUser(user);
    setBanReason(user.ban_reason || '');
    setShowModal(true);
  };

  const handleDeleteClick = (user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
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
        <button
          onClick={fetchUsers}
          className="mt-3 text-sm font-medium text-red-600 dark:text-red-400 hover:underline"
        >
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
          <p className="text-slate-600 dark:text-slate-400">View and manage user accounts</p>
        </div>
        <button
          onClick={fetchUsers}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
        >
          <RefreshIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex gap-2">
          {(['all', 'active', 'banned'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => {
                setFilterBanned(filter);
                setSkip(0);
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterBanned === filter
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
              }`}
            >
              {filter === 'all' ? 'All Users' : filter === 'active' ? 'Active' : 'Banned'}
            </button>
          ))}
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
                  No users found
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                  <td className="px-6 py-4 text-sm text-slate-800 dark:text-white font-medium">{user.email}</td>
                  <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">{user.full_name || '-'}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                      user.is_verified 
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' 
                        : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                    }`}>
                      {user.is_verified ? (
                        <><CheckCircleIcon className="w-3.5 h-3.5" /> Verified</>
                      ) : (
                        'Pending'
                      )}
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
                  <td className="px-6 py-4 text-sm">
                    <div className="flex gap-2">
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
        <span className="px-4 py-2 text-slate-600 dark:text-slate-400">
          Page {Math.floor(skip / limit) + 1}
        </span>
        <button
          onClick={() => setSkip(skip + limit)}
          disabled={users.length < limit}
          className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          Next
        </button>
      </div>

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
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Reason (optional)
                </label>
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
                className={`flex-1 px-4 py-2.5 text-white rounded-lg transition-colors font-medium ${
                  selectedUser.is_banned
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
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
            <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-2">
              Delete User
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-2">
              Are you sure you want to permanently delete this user?
            </p>
            <p className="text-slate-800 dark:text-white font-medium mb-4">
              {selectedUser.email}
            </p>
            <p className="text-red-600 dark:text-red-400 text-sm mb-4">
              ⚠️ This action cannot be undone. All user data including interviews and messages will be deleted.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setSelectedUser(null);
                }}
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
