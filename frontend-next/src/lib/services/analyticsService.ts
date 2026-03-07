import { apiClient } from '@/lib/api';
import { Evaluation, InterviewLevelOutcome } from '@/types/api';

export const analyticsService = {
  async getSessionResults(sessionId: number): Promise<Evaluation> {
    return apiClient.get(`/analytics/sessions/${sessionId}/results`);
  },

  async getSessionLevelCalibration(sessionId: number): Promise<InterviewLevelOutcome> {
    return apiClient.get(`/analytics/sessions/${sessionId}/level-calibration`);
  },
};
