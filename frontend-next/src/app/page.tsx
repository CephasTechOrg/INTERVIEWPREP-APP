'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout/MainLayout';
import { DashboardSection } from '@/components/sections/DashboardSection';
import { InterviewSection } from '@/components/sections/InterviewSection';
import { ResultsSection } from '@/components/sections/ResultsSection';
import { HistorySection } from '@/components/sections/HistorySection';
import { PerformanceSection } from '../components/sections/PerformanceSection';
import { ChatSection } from '@/components/sections/ChatSection';
import { SettingsSection } from '@/components/sections/SettingsSection';
import { useUIStore } from '@/lib/stores/uiStore';
import { useAuth } from '@/lib/hooks/useAuth';

export default function Home() {
  const router = useRouter();
  const { currentPage } = useUIStore();
  const { isAuthenticated, initialized } = useAuth();

  useEffect(() => {
    if (initialized && !isAuthenticated) {
      router.push('/login');
    }
  }, [initialized, isAuthenticated, router]);

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 transition-colors">
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 transition-colors">
        Redirecting to login...
      </div>
    );
  }

  const renderSection = () => {
    switch (currentPage) {
      case 'interview':
        return <InterviewSection />;
      case 'history':
        return <HistorySection />;
      case 'performance':
        return <PerformanceSection />;
      case 'chat':
        return <ChatSection />;
      case 'results':
        return <ResultsSection />;
      case 'settings':
        return <SettingsSection />;
      case 'dashboard':
      default:
        return <DashboardSection />;
    }
  };

  return (
    <MainLayout>
      <div className="transition-opacity duration-300">
        {renderSection()}
      </div>
    </MainLayout>
  );
}
