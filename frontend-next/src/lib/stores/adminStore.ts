import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AdminStoreState {
  admin_token: string | null;
  admin_id: number | null;
  username: string | null;
  full_name: string | null;

  // Actions
  setAdminToken: (token: string, adminId: number, username: string, fullName?: string) => void;
  getToken: () => string | null;
  isAuthenticated: () => boolean;
  logout: () => void;
}

export const useAdminStore = create<AdminStoreState>()(
  persist(
    (set, get) => ({
      admin_token: null,
      admin_id: null,
      username: null,
      full_name: null,

      setAdminToken: (token: string, adminId: number, username: string, fullName?: string) => {
        set({
          admin_token: token,
          admin_id: adminId,
          username: username,
          full_name: fullName || null,
        });
      },

      getToken: () => get().admin_token,

      isAuthenticated: () => !!get().admin_token,

      logout: () => {
        set({
          admin_token: null,
          admin_id: null,
          username: null,
          full_name: null,
        });
      },
    }),
    {
      name: 'admin-store',
      partialize: (state) => ({
        admin_token: state.admin_token,
        admin_id: state.admin_id,
        username: state.username,
        full_name: state.full_name,
      }),
    }
  )
);
