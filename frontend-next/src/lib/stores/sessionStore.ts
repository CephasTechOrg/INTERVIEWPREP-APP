import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { InterviewSession, Message, Evaluation, SessionStage, Difficulty, Track } from '@/types/api';

interface SessionStore {
  currentSession: InterviewSession | null;
  messages: Message[];
  evaluation: Evaluation | null;
  isLoading: boolean;
  error: string | null;

  setCurrentSession: (session: InterviewSession | null) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setEvaluation: (evaluation: Evaluation | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      currentSession: null,
      messages: [],
      evaluation: null,
      isLoading: false,
      error: null,

      setCurrentSession: (session) => set({ currentSession: session }),
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
      setMessages: (messages) => set({ messages }),
      setEvaluation: (evaluation) => set({ evaluation }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      clearSession: () => {
        set({
          currentSession: null,
          messages: [],
          evaluation: null,
          error: null,
        });
      },
    }),
    {
      name: 'session-store',
      storage: {
        getItem: (name) => {
          if (typeof window === 'undefined') return null;
          const item = localStorage.getItem(name);
          return item ? JSON.parse(item) : null;
        },
        setItem: (name, value) => {
          if (typeof window !== 'undefined') {
            localStorage.setItem(name, JSON.stringify(value));
          }
        },
        removeItem: (name) => {
          if (typeof window !== 'undefined') {
            localStorage.removeItem(name);
          }
        },
      },
    }
  )
);
