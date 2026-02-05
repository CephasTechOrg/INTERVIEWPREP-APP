import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type CurrentPage =
  | 'dashboard'
  | 'history'
  | 'performance'
  | 'interview'
  | 'chat'
  | 'results'
  | 'settings';

interface UIStore {
  currentPage: CurrentPage;
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  voiceEnabled: boolean;
  voiceEnabledTouched: boolean;

  setCurrentPage: (page: CurrentPage) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setVoiceEnabled: (enabled: boolean) => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      currentPage: 'dashboard',
      sidebarOpen: true,
      theme: 'light',
      voiceEnabled: true,
      voiceEnabledTouched: false,

      setCurrentPage: (page) => set({ currentPage: page }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
      setVoiceEnabled: (enabled) => set({ voiceEnabled: enabled, voiceEnabledTouched: true }),
    }),
    {
      name: 'ui-store',
      merge: (persisted, current) => {
        const merged = { ...current, ...(persisted as object) } as UIStore;
        if (!merged.voiceEnabledTouched) {
          merged.voiceEnabled = true;
        }
        return merged;
      },
      storage: {
        getItem: (name) => {
          if (typeof window === 'undefined') return null;
          const item = localStorage.getItem(name);
          return item ? JSON.parse(item) : null;
        },
        setItem: (name, value) => {
          if (typeof window !== 'undefined') {
            localStorage.setItem(name, JSON.stringify(value));
          }
        },
        removeItem: (name) => {
          if (typeof window !== 'undefined') {
            localStorage.removeItem(name);
          }
        },
      },
    }
  )
);
