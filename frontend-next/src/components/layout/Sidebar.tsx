'use client';

import { useUIStore } from '@/lib/stores/uiStore';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';

const Icons = {
  dashboard: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v2a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 13a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1h-4a1 1 0 01-1-1v-6z" />
    </svg>
  ),
  history: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  performance: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 13h4v8H3zM10 9h4v12h-4zM17 5h4v16h-4z" />
    </svg>
  ),
  interview: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  ),
  chat: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
    </svg>
  ),
  results: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  settings: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 010 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.212-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 010-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  logout: (
    <svg className="w-[22px] h-[22px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
    </svg>
  ),
  close: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  chevronRight: (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
};

export const Sidebar = () => {
  const { currentPage, setCurrentPage, sidebarOpen, toggleSidebar } = useUIStore();
  const { logout, user } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const mainNavItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Icons.dashboard, shortcut: '⌘1' },
    { id: 'interview', label: 'Interview', icon: Icons.interview, shortcut: '⌘2' },
    { id: 'history', label: 'History', icon: Icons.history, shortcut: '⌘3' },
    { id: 'results', label: 'Results', icon: Icons.results, shortcut: '⌘4' },
  ];

  const secondaryNavItems = [
    { id: 'performance', label: 'Analytics', icon: Icons.performance },
    { id: 'chat', label: 'AI Assistant', icon: Icons.chat },
    { id: 'settings', label: 'Settings', icon: Icons.settings },
  ];

  const NavButton = ({ item }: { item: { id: string; label: string; icon: React.ReactNode; shortcut?: string } }) => {
    const isActive = currentPage === item.id;
    return (
      <button
        onClick={() => {
          setCurrentPage(item.id as any);
          if (window.innerWidth < 1024) toggleSidebar();
        }}
        className={`group relative w-full flex items-center gap-3 px-3.5 py-2 rounded-lg text-[13px] font-medium transition-all duration-200 ${
          isActive
            ? 'bg-blue-700/50 text-white'
            : 'text-blue-100 hover:text-white hover:bg-blue-800/40'
        }`}
      >
        {/* Active left border indicator */}
        <span className={`absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full transition-all duration-200 ${
          isActive 
            ? 'bg-blue-300' 
            : 'bg-transparent group-hover:bg-blue-700'
        }`} />
        
        <span className={`flex-shrink-0 transition-all duration-200 ${
          isActive
            ? 'text-blue-200'
            : 'text-blue-100 group-hover:text-white'
        }`}>
          {item.icon}
        </span>
        <span className="flex-1 text-left">{item.label}</span>
        
        {/* Keyboard shortcut hint (shown on hover) */}
        {item.shortcut && (
          <span className="hidden group-hover:flex items-center text-[10px] font-mono text-blue-300 bg-blue-900 px-1.5 py-0.5 rounded">
            {item.shortcut}
          </span>
        )}
        
        {/* Active indicator arrow */}
        {isActive && (
          <span className="text-blue-300">
            {Icons.chevronRight}
          </span>
        )}
      </button>
    );
  };

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm lg:hidden z-30 transition-opacity"
          onClick={toggleSidebar}
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-screen w-64 z-40 transform transition-transform duration-300 ease-out flex flex-col
          bg-blue-900 dark:bg-blue-900
          border-r border-blue-800 dark:border-blue-800
          shadow-sm dark:shadow-none
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Brand Header */}
        <div className="px-5 h-16 flex items-center flex-shrink-0">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/25">
                <svg className="w-4.5 h-4.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <div className="flex flex-col">
                <span className="text-[15px] font-bold text-white tracking-tight">
                  IntervIQ
                </span>
                <span className="text-[10px] text-blue-300 font-medium -mt-0.5">
                  AI Interview Coach
                </span>
              </div>
            </div>
            <button
              onClick={toggleSidebar}
              className="lg:hidden text-blue-200 hover:text-white p-1.5 rounded-lg hover:bg-blue-800 transition-colors"
            >
              {Icons.close}
            </button>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-2 overflow-y-auto overflow-x-hidden scrollbar-hide">
          {/* Main */}
          <div className="mb-4">
            <p className="px-3 mb-2 text-[10px] font-semibold text-blue-200 uppercase tracking-wider">
              Main
            </p>
            <div className="space-y-0.5">
              {mainNavItems.map(item => <NavButton key={item.id} item={item} />)}
            </div>
          </div>

          {/* Tools */}
          <div>
            <p className="px-3 mb-2 text-[10px] font-semibold text-blue-200 uppercase tracking-wider">
              Tools
            </p>
            <div className="space-y-0.5">
              {secondaryNavItems.map(item => <NavButton key={item.id} item={item} />)}
            </div>
          </div>
        </nav>

        {/* Footer: User info + Sign out */}
        <div className="px-3 py-4 flex-shrink-0 border-t border-blue-900 space-y-1">
          {/* User mini-card */}
          <div className="flex items-center gap-2.5 px-3 py-2">
            <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0">
              {(user?.profile as any)?.avatar_url ? (
                <img src={(user?.profile as any)?.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full bg-blue-600 flex items-center justify-center text-white text-[11px] font-bold">
                  {((user?.full_name?.split(/\s+/).map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)) ||
                    (user?.email?.[0] || 'U').toUpperCase())}
                </div>
              )}
            </div>
            <div className="min-w-0">
              <p className="text-[12px] font-semibold text-white truncate leading-tight">
                {user?.full_name || user?.email?.split('@')[0] || 'User'}
              </p>
              <p className="text-[10px] text-blue-300 truncate leading-tight">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-blue-100 hover:text-white hover:bg-blue-800/40 transition-colors"
          >
            {Icons.logout}
            <span>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
};
