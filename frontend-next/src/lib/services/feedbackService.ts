import { apiClient } from '@/lib/api';
import { FeedbackCreate, FeedbackOut } from '@/types/api';

export const feedbackService = {
  async submitFeedback(data: FeedbackCreate): Promise<FeedbackOut> {
    return apiClient.post('/feedback', data);
  },

  async getSessionFeedback(sessionId: number): Promise<FeedbackOut | null> {
    try {
      return await apiClient.get(`/feedback/session/${sessionId}`);
    } catch {
      return null;
    }
  },
};
