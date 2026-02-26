'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAdminStore } from '@/lib/stores/adminStore';
import { AdminGuard } from '@/components/AdminGuard';

interface AdminLayoutProps {
  children: React.ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();
  const logout = useAdminStore((state) => state.logout);
  const username = useAdminStore((state) => state.username);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    router.push('/admin');
  };

  const navItems = [
    { label: 'Dashboard', href: '/admin/dashboard', icon: '📊' },
    { label: 'Users', href: '/admin/users', icon: '👥' },
    { label: 'Audit Logs', href: '/admin/audit-logs', icon: '📋' },
  ];

  return (
    <AdminGuard>
      <div className="flex h-screen bg-gray-100">
        {/* Sidebar */}
        <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-indigo-900 text-white transition-all duration-300 flex flex-col`}>
          <div className="p-4 border-b border-indigo-800">
            <div className="flex items-center justify-between">
              {sidebarOpen && <h1 className="text-xl font-bold">InterviewPrep</h1>}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-1 hover:bg-indigo-800 rounded"
              >
                {sidebarOpen ? '◀' : '▶'}
              </button>
            </div>
            {sidebarOpen && <p className="text-sm text-indigo-300 mt-1">Admin Portal</p>}
          </div>

          <nav className="flex-1 p-4 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-indigo-800 transition"
              >
                <span className="text-xl">{item.icon}</span>
                {sidebarOpen && <span>{item.label}</span>}
              </Link>
            ))}
          </nav>

          <div className="p-4 border-t border-indigo-800">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-8 h-8 bg-indigo-400 rounded-full flex items-center justify-center text-sm font-bold">
                {username?.charAt(0).toUpperCase()}
              </div>
              {sidebarOpen && <span className="text-sm truncate">{username}</span>}
            </div>
            <button
              onClick={handleLogout}
              className="w-full text-left px-3 py-2 rounded-lg hover:bg-indigo-800 transition text-sm"
            >
              {sidebarOpen ? 'Logout' : '🚪'}
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar */}
          <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-800">Admin Dashboard</h2>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Logged in as: <strong>{username}</strong></span>
            </div>
          </div>

          {/* Page Content */}
          <div className="flex-1 overflow-auto p-6">
            {children}
          </div>
        </div>
      </div>
    </AdminGuard>
  );
}
