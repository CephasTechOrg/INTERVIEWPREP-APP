import { apiClient } from '@/lib/api';

export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

export type ChatThread = {
  id: number;
  user_id: number;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
};

export type ChatThreadSummary = {
  id: number;
  title: string;
  message_count: number;
  updated_at: string;
};

class ChatService {
  async createThread(title: string, messages: ChatMessage[] = []): Promise<ChatThread> {
    return apiClient.post('/chat-threads', {
      title,
      messages,
    });
  }

  async listThreads(limit: number = 50, offset: number = 0): Promise<ChatThreadSummary[]> {
    return apiClient.get(`/chat-threads?limit=${limit}&offset=${offset}`);
  }

  async getThread(threadId: number): Promise<ChatThread> {
    return apiClient.get(`/chat-threads/${threadId}`);
  }

  async updateThread(
    threadId: number,
    updates: { title?: string; messages?: ChatMessage[] }
  ): Promise<ChatThread> {
    return apiClient.put(`/chat-threads/${threadId}`, updates);
  }

  async deleteThread(threadId: number): Promise<void> {
    return apiClient.delete(`/chat-threads/${threadId}`);
  }

  async addMessage(
    threadId: number,
    role: 'user' | 'assistant',
    content: string
  ): Promise<ChatThread> {
    const thread = await this.getThread(threadId);
    const messages = [...thread.messages, { role, content }];
    return this.updateThread(threadId, { messages });
  }
}

export const chatService = new ChatService();
