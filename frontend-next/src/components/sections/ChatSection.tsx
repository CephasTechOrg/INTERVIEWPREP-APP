'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { aiService } from '@/lib/services/aiService';
import { chatService, type ChatMessage } from '@/lib/services/chatService';
import { Icons } from '@/components/ui/Icons';

type ChatThread = {
  id: number;
  title: string;
  messages: ChatMessage[];
};

const buildTitle = (messages: ChatMessage[]) => {
  const firstUser = messages.find((m) => m.role === 'user');
  const text = firstUser?.content?.trim() || 'New Chat';
  return text.length > 42 ? `${text.slice(0, 42)}...` : text;
};

export const ChatSection = () => {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Load threads from backend on mount
  useEffect(() => {
    const loadThreads = async () => {
      try {
        setIsLoading(true);
        const summaries = await chatService.listThreads();
        
        if (summaries.length === 0) {
          // Create first thread if none exist
          const newThread = await chatService.createThread('New Chat', []);
          setThreads([{ id: newThread.id, title: newThread.title, messages: newThread.messages }]);
          setActiveId(newThread.id);
        } else {
          // Load full details of first thread
          const firstThread = await chatService.getThread(summaries[0].id);
          setThreads([{ id: firstThread.id, title: firstThread.title, messages: firstThread.messages }]);
          setActiveId(firstThread.id);

          // Lazy-load other threads on demand
          for (const summary of summaries.slice(1)) {
            const thread = await chatService.getThread(summary.id);
            setThreads((prev) => [...prev, { id: thread.id, title: thread.title, messages: thread.messages }]);
          }
        }
      } catch (error) {
        console.error('Failed to load chat threads:', error);
        // Fallback: create a new thread
        const newThread = await chatService.createThread('New Chat', []);
        setThreads([{ id: newThread.id, title: newThread.title, messages: newThread.messages }]);
        setActiveId(newThread.id);
      } finally {
        setIsLoading(false);
      }
    };

    loadThreads();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeId, threads.length, isSending]);

  const activeThread = useMemo(
    () => threads.find((t) => t.id === activeId) || null,
    [threads, activeId]
  );

  const messages = activeThread?.messages ?? [];

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || !activeThread) return;

    const newMessage: ChatMessage = { role: 'user', content: text };
    const history: ChatMessage[] = [...messages, newMessage];

    setInput('');

    try {
      setIsSending(true);
      
      // Add user message to backend
      const updatedThread = await chatService.updateThread(activeThread.id, {
        messages: history,
      });

      // Get AI response
      const response = await aiService.chat({ message: text, history });
      const assistantMessage: ChatMessage = { role: 'assistant', content: response.reply };
      const nextMessages: ChatMessage[] = [...history, assistantMessage];

      // Update thread with AI response
      const finalThread = await chatService.updateThread(activeThread.id, {
        messages: nextMessages,
        title: buildTitle(nextMessages),
      });

      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? { ...t, messages: finalThread.messages, title: finalThread.title }
            : t
        )
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      const assistantMessage: ChatMessage = { role: 'assistant', content: 'AI is currently unavailable.' };
      const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: text }, assistantMessage];

      try {
        await chatService.updateThread(activeThread.id, { messages: nextMessages });
        setThreads((prev) =>
          prev.map((t) =>
            t.id === activeThread.id ? { ...t, messages: nextMessages } : t
          )
        );
      } catch {
        // Silently fail if update fails
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleNewChat = async () => {
    try {
      const newThread = await chatService.createThread('New Chat', []);
      setThreads((prev) => [{ id: newThread.id, title: newThread.title, messages: newThread.messages }, ...prev]);
      setActiveId(newThread.id);
      setInput('');
    } catch (error) {
      console.error('Failed to create new chat:', error);
    }
  };

  const handleDeleteChat = async (id: number) => {
    try {
      await chatService.deleteThread(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
      if (activeId === id) {
        const remaining = threads.filter((t) => t.id !== id);
        if (remaining.length) {
          setActiveId(remaining[0].id);
        } else {
          const freshThread = await chatService.createThread('New Chat', []);
          setThreads([{ id: freshThread.id, title: freshThread.title, messages: freshThread.messages }]);
          setActiveId(freshThread.id);
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  return (
    <div className="h-[calc(100dvh-8rem)] flex flex-col lg:flex-row gap-4 min-h-0 overflow-hidden">
      {/* Sidebar - Chat History */}
      <aside className={`bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col min-h-0 ${historyCollapsed ? 'hidden lg:flex lg:w-72' : 'flex w-full lg:w-72'} flex-shrink-0`}>
        <div className="px-4 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white flex items-center justify-between flex-shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Chats</h3>
            <p className="text-xs text-gray-500">Stored in database</p>
          </div>
          <button
            onClick={() => setHistoryCollapsed((prev) => !prev)}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"
            title="Collapse"
          >
            {Icons.chevronLeft}
          </button>
        </div>

        <div className="p-4 flex-shrink-0">
          <button
            onClick={handleNewChat}
            disabled={isLoading}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
          >
            {Icons.plus}
            New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4 min-h-0">
          {isLoading ? (
            <div className="text-xs text-gray-500 px-4 py-2">Loading chats...</div>
          ) : threads.length === 0 ? (
            <div className="text-xs text-gray-500 px-4">No chats yet.</div>
          ) : (
            threads.map((thread) => (
              <button
                key={thread.id}
                onClick={() => setActiveId(thread.id)}
                className={`w-full text-left px-4 py-3 rounded-xl transition-colors mb-2 border ${
                  thread.id === activeId
                    ? 'bg-blue-50 border-blue-200 text-blue-900'
                    : 'bg-white border-transparent hover:bg-gray-50 text-gray-700'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{thread.title}</p>
                    <p className="text-xs text-gray-500 mt-1">{thread.messages.length} messages</p>
                  </div>
                  <span
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteChat(thread.id);
                    }}
                    className="text-gray-400 hover:text-red-500"
                    title="Delete chat"
                  >
                    {Icons.trash}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white rounded-2xl border border-gray-200 shadow-sm min-h-0 overflow-hidden">
        {/* Chat Header - Fixed */}
        <div className="px-4 sm:px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white flex-shrink-0">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg sm:text-xl font-semibold text-gray-900">AI Assistant</h2>
              <p className="text-xs sm:text-sm text-gray-600">Ask anything about interviews, preparation, or questions.</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setHistoryCollapsed((prev) => !prev)}
                className="lg:hidden p-2 rounded-lg border border-gray-200 hover:bg-gray-100 text-gray-600"
                title="Toggle history"
              >
                {Icons.menu}
              </button>
              <button
                onClick={handleNewChat}
                disabled={isLoading}
                className="hidden sm:inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:bg-gray-100 text-sm font-medium text-gray-700"
              >
                {Icons.plus}
                New chat
              </button>
            </div>
          </div>
        </div>

        {/* Chat Messages - Scrollable */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-5 space-y-4 min-h-0 bg-gradient-to-b from-white to-gray-50">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <p className="text-sm">Loading chat...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center max-w-md">
                <div className="mx-auto w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
                  {Icons.messageCircle}
                </div>
                <p className="text-sm">Start a conversation. Try: “Give me a system design roadmap.”</p>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-2 sm:gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role !== 'user' && (
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold flex-shrink-0">
                    AI
                  </div>
                )}
                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-3 sm:px-4 py-2 sm:py-3 text-sm leading-relaxed shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-white text-gray-900 border border-gray-200 rounded-bl-sm'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-semibold flex-shrink-0">
                    You
                  </div>
                )}
              </div>
            ))
          )}
          {isSending && (
            <div className="flex gap-2 sm:gap-3 items-center">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold">
                AI
              </div>
              <div className="px-3 sm:px-4 py-2 rounded-2xl border border-gray-200 bg-white text-gray-500 text-sm">
                Typing...
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>

        {/* Chat Input - Fixed at Bottom */}
        <form onSubmit={handleSend} className="p-3 sm:p-4 md:p-6 border-t border-gray-200 bg-white flex-shrink-0">
          <div className="flex items-end gap-2 sm:gap-3">
            <div className="flex-1">
              <label className="sr-only" htmlFor="chatInput">Message</label>
              <textarea
                id="chatInput"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message the AI assistant..."
                className="w-full min-h-[44px] sm:min-h-[48px] max-h-32 resize-none px-3 sm:px-4 py-2.5 sm:py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                disabled={isSending || isLoading}
                rows={1}
              />
              <p className="mt-1.5 text-xs text-gray-500 hidden sm:block">Press Enter to send • Shift+Enter for a new line</p>
            </div>
            <button
              type="submit"
              disabled={isSending || !input.trim() || isLoading}
              className="h-11 sm:h-12 px-4 sm:px-5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-semibold transition-colors flex-shrink-0"
            >
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
