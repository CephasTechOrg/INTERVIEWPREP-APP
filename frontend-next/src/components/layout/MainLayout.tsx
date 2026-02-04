'use client';

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

interface MainLayoutProps {
  children: ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  return (
    <div className="min-h-[100dvh] bg-gray-50 overflow-hidden">
      <Sidebar />
      <TopBar />
      {/* Main content area - scrollable by default, children can override */}
      <main className="pt-16 lg:pl-64 h-[100dvh]">
        <div className="h-[calc(100dvh-4rem)] p-4 md:p-6 overflow-y-auto overscroll-contain">
          <div className="max-w-7xl mx-auto w-full">{children}</div>
        </div>
      </main>
    </div>
  );
};
