'use client';

import { useEffect, useState } from 'react';
import { adminService } from '@/lib/services/adminService';

interface AuditLog {
  id: number;
  action: string;
  user_id?: number;
  admin_id?: number;
  target_type?: string;
  target_id?: number;
  metadata?: Record<string, any>;
  timestamp: string;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [skip, setSkip] = useState(0);
  const limit = 100;

  useEffect(() => {
    fetchLogs();
  }, [skip]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await adminService.getAuditLogs(skip, limit);
      setLogs(data.logs);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action: string) => {
    if (action.includes('ban')) return 'bg-red-100 text-red-800';
    if (action.includes('login')) return 'bg-blue-100 text-blue-800';
    if (action.includes('create')) return 'bg-green-100 text-green-800';
    if (action.includes('delete')) return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return <div className="text-center py-8">Loading audit logs...</div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Audit Logs</h1>
        <p className="text-gray-600">View system activity and admin actions</p>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Action</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Admin ID</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Target</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Timestamp</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-800">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50 transition text-sm">
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${getActionColor(log.action)}`}>
                    {log.action.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-600">{log.admin_id || '-'}</td>
                <td className="px-6 py-4 text-gray-600">
                  {log.target_type && log.target_id
                    ? `${log.target_type} #${log.target_id}`
                    : log.user_id
                      ? `User #${log.user_id}`
                      : '-'}
                </td>
                <td className="px-6 py-4 text-gray-600">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-6 py-4 text-gray-600 max-w-xs truncate">
                  {log.metadata ? JSON.stringify(log.metadata) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {logs.length === 0 && (
        <div className="text-center py-8 text-gray-600">No audit logs found</div>
      )}

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
          disabled={logs.length < limit}
          className="px-4 py-2 bg-gray-300 rounded-lg disabled:opacity-50"
        >
          Next
        </button>
      </div>

      <button
        onClick={fetchLogs}
        className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
      >
        Refresh Logs
      </button>
    </div>
  );
}
