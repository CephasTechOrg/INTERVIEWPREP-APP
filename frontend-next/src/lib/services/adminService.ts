import { apiClient } from '@/lib/api';

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
  // Dashboard
  async getStats(): Promise<DashboardStats> {
    return apiClient.get<DashboardStats>('/admin/stats');
  },

  // Users
  async getUsers(skip: number = 0, limit: number = 50, filterBanned?: boolean): Promise<{ users: User[]; total: number }> {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (filterBanned !== undefined) {
      params.append('filter_banned', filterBanned.toString());
    }
    const response = await apiClient.get<User[]>(`/admin/users?${params}`);
    return { users: response, total: response.length };
  },

  async getUserDetail(userId: number): Promise<User> {
    return apiClient.get<User>(`/admin/users/${userId}`);
  },

  async banUser(userId: number, reason?: string): Promise<{ ok: boolean; message: string }> {
    return apiClient.post<{ ok: boolean; message: string }>(`/admin/users/${userId}/ban`, {
      reason: reason || null,
    });
  },

  async unbanUser(userId: number): Promise<{ ok: boolean; message: string }> {
    return apiClient.post<{ ok: boolean; message: string }>(`/admin/users/${userId}/unban`, {});
  },

  // Audit Logs
  async getAuditLogs(skip: number = 0, limit: number = 100): Promise<{ logs: AuditLog[]; total: number }> {
    return apiClient.get<{ logs: AuditLog[]; total: number }>(`/admin/audit-logs?skip=${skip}&limit=${limit}`);
  },

  async getUsersCount(filterBanned?: boolean): Promise<{ total: number }> {
    const params = filterBanned !== undefined ? `?filter_banned=${filterBanned}` : '';
    return apiClient.get<{ total: number }>(`/admin/users-count${params}`);
  },
};
