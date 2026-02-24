import axios from 'axios';
import { apiClient } from '@/lib/api';
import { AIStatusResponse, AIChatRequest, AIChatResponse, TTSRequest, TTSResponse } from '@/types/api';

const getBaseURL = () =>
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  'http://127.0.0.1:8000/api/v1';

export const aiService = {
  async getStatus(): Promise<AIStatusResponse> {
    return apiClient.get('/ai/status');
  },

  async chat(data: AIChatRequest): Promise<AIChatResponse> {
    return apiClient.post('/ai/chat', data);
  },
  async generateSpeech(data: TTSRequest): Promise<TTSResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const response = await axios.post(`${getBaseURL()}/tts`, data, {
      responseType: 'arraybuffer',
      timeout: 15000, // 15 second timeout
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    const contentType = response.headers['content-type'] as string | undefined;
    const provider = response.headers['x-tts-provider'] as string | undefined;

    if (contentType && contentType.startsWith('audio/')) {
      if (typeof window === 'undefined') {
        return { mode: 'audio', audio_url: '', tts_provider: provider };
      }
      const blob = new Blob([response.data], { type: contentType });
      const audioUrl = URL.createObjectURL(blob);
      return { mode: 'audio', audio_url: audioUrl, tts_provider: provider };
    }

    const text = new TextDecoder().decode(response.data);
    try {
      const parsed = JSON.parse(text) as { text?: string; tts_provider?: string };
      return { mode: 'text', text: parsed.text || '', tts_provider: parsed.tts_provider };
    } catch {
      return { mode: 'text', text };
    }
  },
};
