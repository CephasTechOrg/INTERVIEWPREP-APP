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

export interface AdminFeedbackItem {
  id: number;
  session_id: number;
  user_id: number;
  user_email: string | null;
  user_name: string | null;
  session_track: string | null;
  session_difficulty: string | null;
  session_company_style: string | null;
  rating: number;
  thumbs: 'up' | 'down' | null;
  comment: string | null;
  rating_questions: number | null;
  rating_feedback: number | null;
  rating_difficulty: number | null;
  created_at: string | null;
}

export interface AdminFeedbackStats {
  total_sessions: number;
  sessions_with_feedback: number;
  average_rating: number | null;
  rating_distribution: Record<number, number>;
  thumbs_up_count: number;
  thumbs_down_count: number;
}

export interface UserUsage {
  chat_messages_today: number;
  chat_reset_date: string;
  tts_characters_month: number;
  usage_month: string;
  total_chat_messages: number;
  total_tts_characters: number;
  total_interview_sessions: number;
}

export interface SessionSummary {
  id: number;
  track: string;
  difficulty: string;
  company_style: string;
  stage: string;
  overall_score: number | null;
  created_at: string | null;
}

export interface UserFullDetail extends User {
  usage: UserUsage | null;
  sessions: SessionSummary[];
  feedback_count: number;
}

export interface SystemHealth {
  llm: {
    configured: boolean;
    status: string;
    fallback_mode: boolean;
    last_error?: string | null;
    last_error_at?: number | null;
    last_ok_at?: number | null;
    model?: string;
    base_url?: string;
  };
  database: string;
  timestamp: string;
}

export const adminService = {
  // Dashboard
  async getStats(): Promise<DashboardStats> {
    return apiClient.get<DashboardStats>('/admin/stats');
  },

  async getSystemHealth(): Promise<SystemHealth> {
    return apiClient.get<SystemHealth>('/admin/system/health');
  },

  // Users
  async getUsers(skip: number = 0, limit: number = 50, filterBanned?: boolean, search?: string): Promise<{ users: User[]; total: number }> {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (filterBanned !== undefined) {
      params.append('filter_banned', filterBanned.toString());
    }
    if (search) {
      params.append('search', search);
    }
    const response = await apiClient.get<User[]>(`/admin/users?${params}`);
    return { users: response, total: response.length };
  },

  async getUserDetail(userId: number): Promise<User> {
    return apiClient.get<User>(`/admin/users/${userId}`);
  },

  async getUserFullDetail(userId: number): Promise<UserFullDetail> {
    return apiClient.get<UserFullDetail>(`/admin/users/${userId}/detail`);
  },

  async resetUserUsage(userId: number): Promise<{ ok: boolean; message: string }> {
    return apiClient.post<{ ok: boolean; message: string }>(`/admin/users/${userId}/reset-usage`, {});
  },

  async banUser(userId: number, reason?: string): Promise<{ ok: boolean; message: string }> {
    return apiClient.post<{ ok: boolean; message: string }>(`/admin/users/${userId}/ban`, {
      reason: reason || null,
    });
  },

  async unbanUser(userId: number): Promise<{ ok: boolean; message: string }> {
    return apiClient.post<{ ok: boolean; message: string }>(`/admin/users/${userId}/unban`, {});
  },

  async deleteUser(userId: number): Promise<{ ok: boolean; message: string }> {
    return apiClient.delete<{ ok: boolean; message: string }>(`/admin/users/${userId}`);
  },

  // Audit Logs
  async getAuditLogs(skip: number = 0, limit: number = 100): Promise<{ logs: AuditLog[]; total: number }> {
    return apiClient.get<{ logs: AuditLog[]; total: number }>(`/admin/audit-logs?skip=${skip}&limit=${limit}`);
  },

  async getUsersCount(filterBanned?: boolean): Promise<{ total: number }> {
    const params = filterBanned !== undefined ? `?filter_banned=${filterBanned}` : '';
    return apiClient.get<{ total: number }>(`/admin/users-count${params}`);
  },

  // Feedback
  async getFeedbackStats(): Promise<AdminFeedbackStats> {
    return apiClient.get<AdminFeedbackStats>('/admin/feedback/stats');
  },

  async getAllFeedback(
    skip = 0,
    limit = 50,
    minRating?: number,
    thumbs?: 'up' | 'down',
  ): Promise<{ feedback: AdminFeedbackItem[]; total: number; skip: number; limit: number }> {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (minRating !== undefined) params.append('min_rating', minRating.toString());
    if (thumbs !== undefined) params.append('thumbs', thumbs);
    return apiClient.get(`/admin/feedback?${params}`);
  },
};
