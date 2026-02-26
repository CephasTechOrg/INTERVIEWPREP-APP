import axios from 'axios';
import { useAdminStore } from '@/lib/stores/adminStore';

const API_BASE = 'https://interviq-backend.onrender.com/api/v1';

interface AdminLoginRequest {
  username: string;
  password: string;
}

interface AdminLoginResponse {
  access_token: string;
  admin_id: number;
  username: string;
  full_name?: string;
}

interface DashboardStats {
  total_users: number;
  verified_users: number;
  banned_users: number;
  active_interviews: number;
  total_questions: number;
  timestamp: string;
}

interface User {
  id: number;
  email: string;
  full_name?: string;
  is_verified: boolean;
  is_banned: boolean;
  ban_reason?: string;
  banned_at?: string;
  created_at: string;
  role_pref: string;
  last_login_at?: string;
}

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

export const adminService = {
  // Auth
  async login(username: string, password: string): Promise<AdminLoginResponse> {
    const response = await axios.post(`${API_BASE}/admin/login`, {
      username,
      password,
    });
    return response.data;
  },

  // Dashboard
  async getStats(): Promise<DashboardStats> {
    const token = useAdminStore.getState().getToken();
    const response = await axios.get(`${API_BASE}/admin/stats`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },

  // Users
  async getUsers(skip: number = 0, limit: number = 50, filterBanned?: boolean): Promise<{ users: User[]; total: number }> {
    const token = useAdminStore.getState().getToken();
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (filterBanned !== undefined) {
      params.append('filter_banned', filterBanned.toString());
    }

    const response = await axios.get(`${API_BASE}/admin/users?${params}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return { users: response.data, total: response.data.length };
  },

  async getUserDetail(userId: number): Promise<User> {
    const token = useAdminStore.getState().getToken();
    const response = await axios.get(`${API_BASE}/admin/users/${userId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },

  async banUser(userId: number, reason?: string): Promise<{ ok: boolean; message: string }> {
    const token = useAdminStore.getState().getToken();
    const response = await axios.post(
      `${API_BASE}/admin/users/${userId}/ban`,
      { reason: reason || null },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  async unbanUser(userId: number): Promise<{ ok: boolean; message: string }> {
    const token = useAdminStore.getState().getToken();
    const response = await axios.post(`${API_BASE}/admin/users/${userId}/unban`, {}, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },

  // Audit Logs
  async getAuditLogs(skip: number = 0, limit: number = 100): Promise<{ logs: AuditLog[]; total: number }> {
    const token = useAdminStore.getState().getToken();
    const response = await axios.get(`${API_BASE}/admin/audit-logs?skip=${skip}&limit=${limit}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },

  async getUsersCount(filterBanned?: boolean): Promise<{ total: number }> {
    const token = useAdminStore.getState().getToken();
    const params = filterBanned !== undefined ? `?filter_banned=${filterBanned}` : '';
    const response = await axios.get(`${API_BASE}/admin/users-count${params}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },
};
