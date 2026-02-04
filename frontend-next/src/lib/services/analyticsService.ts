import { apiClient } from '@/lib/api';
import { Evaluation } from '@/types/api';

export const analyticsService = {
  async getSessionResults(sessionId: number): Promise<Evaluation> {
    return apiClient.get(`/analytics/sessions/${sessionId}/results`);
  },
};
