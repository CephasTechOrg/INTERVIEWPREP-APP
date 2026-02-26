'use client';

import { useEffect, useState } from 'react';
import { adminService } from '@/lib/services/adminService';

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
  const [banReason, setBanReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, [skip, filterBanned]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const filterValue = filterBanned === 'banned' ? true : filterBanned === 'active' ? false : undefined;
      const data = await adminService.getUsers(skip, limit, filterValue);
      setUsers(data.users);
    } catch (err: any) {
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleBanClick = (user: User) => {
    setSelectedUser(user);
    setBanReason(user.ban_reason || '');
    setShowModal(true);
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
    } catch (err: any) {
      alert(err.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading users...</div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800 mb-2">User Management</h1>
        <p className="text-gray-600">View and manage user accounts</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2">
          {(['all', 'active', 'banned'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => {
                setFilterBanned(filter);
                setSkip(0);
              }}
              className={`px-4 py-2 rounded-lg transition ${
                filterBanned === filter
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
              }`}
            >
              {filter === 'all' ? 'All Users' : filter === 'active' ? 'Active' : 'Banned'}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Email</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Name</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Verified</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Status</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Joined</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50 transition">
                <td className="px-6 py-4 text-sm text-gray-800">{user.email}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{user.full_name || '-'}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded text-white text-xs font-semibold ${
                    user.is_verified ? 'bg-green-500' : 'bg-yellow-500'
                  }`}>
                    {user.is_verified ? '✓ Verified' : '⏳ Pending'}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">
                  {user.is_banned ? (
                    <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs font-semibold">
                      🚫 Banned
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">
                      ✓ Active
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-sm">
                  <button
                    onClick={() => handleBanClick(user)}
                    className={`px-3 py-1 rounded text-sm transition ${
                      user.is_banned
                        ? 'bg-green-500 hover:bg-green-600 text-white'
                        : 'bg-red-500 hover:bg-red-600 text-white'
                    }`}
                  >
                    {user.is_banned ? 'Unban' : 'Ban'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex gap-2 justify-center">
        <button
          onClick={() => setSkip(Math.max(0, skip - limit))}
          disabled={skip === 0}
          className="px-4 py-2 bg-gray-300 rounded-lg disabled:opacity-50"
        >
          Previous
        </button>
        <span className="px-4 py-2">
          Page {Math.floor(skip / limit) + 1}
        </span>
        <button
          onClick={() => setSkip(skip + limit)}
          disabled={users.length < limit}
          className="px-4 py-2 bg-gray-300 rounded-lg disabled:opacity-50"
        >
          Next
        </button>
      </div>

      {/* Ban Modal */}
      {showModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">
              {selectedUser.is_banned ? 'Unban User' : 'Ban User'}
            </h2>
            <p className="text-gray-600 mb-4">{selectedUser.email}</p>

            {!selectedUser.is_banned && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Reason (optional)</label>
                <textarea
                  value={banReason}
                  onChange={(e) => setBanReason(e.target.value)}
                  placeholder="Why are you banning this user?"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                  rows={3}
                />
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 bg-gray-300 rounded-lg hover:bg-gray-400 transition"
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmBan}
                className={`flex-1 px-4 py-2 text-white rounded-lg transition ${
                  selectedUser.is_banned
                    ? 'bg-green-600 hover:bg-green-700'
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
    </div>
  );
}
