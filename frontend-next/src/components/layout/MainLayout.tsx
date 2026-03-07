'use client';

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useUIStore } from '@/lib/stores/uiStore';

interface MainLayoutProps {
  children: ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  const { reduceMotion, highContrast, fontScale, sidebarCollapsed } = useUIStore();

  return (
    <div
      className={`app-root min-h-[100dvh] bg-slate-50 dark:bg-slate-900 overflow-hidden transition-colors duration-300 ${
        reduceMotion ? 'reduce-motion' : ''
      } ${highContrast ? 'high-contrast' : ''}`}
      style={{ fontSize: `${fontScale}%` }}
    >
      <Sidebar />
      <TopBar />
      {/* Main content area — shifts right based on sidebar expanded/collapsed state */}
      <main className={`pt-16 h-[100dvh] transition-all duration-300 ${sidebarCollapsed ? 'lg:pl-14' : 'lg:pl-64'}`}>
        <div className="h-[calc(100dvh-4rem)] p-4 md:p-6 overflow-y-auto overscroll-contain">
          <div className="max-w-7xl mx-auto w-full">{children}</div>
        </div>
      </main>
    </div>
  );
};
