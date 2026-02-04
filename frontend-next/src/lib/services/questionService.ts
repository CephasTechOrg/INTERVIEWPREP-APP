import { apiClient } from '@/lib/api';
import { Question, QuestionCoverageResponse } from '@/types/api';

export const questionService = {
  async listQuestions(params?: {
    track?: string;
    company_style?: string;
    difficulty?: string;
  }): Promise<Question[]> {
    const queryString = params
      ? '?' + new URLSearchParams(params as Record<string, string>).toString()
      : '';
    return apiClient.get(`/questions${queryString}`);
  },

  async getQuestion(questionId: number): Promise<Question> {
    return apiClient.get(`/questions/${questionId}`);
  },

  async getQuestionCoverage(params: {
    track: string;
    company_style: string;
    difficulty: string;
    include_behavioral?: boolean;
  }): Promise<QuestionCoverageResponse> {
    const queryString = '?' + new URLSearchParams({
      track: params.track,
      company_style: params.company_style,
      difficulty: params.difficulty,
      include_behavioral: params.include_behavioral ? 'true' : 'false',
    }).toString();
    return apiClient.get(`/questions/coverage${queryString}`);
  },
};
