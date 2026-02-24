'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { aiService } from '@/lib/services/aiService';
import { chatService, type ChatMessage } from '@/lib/services/chatService';
import { sanitizeAiText } from '@/lib/utils/text';
import { Icons } from '@/components/ui/Icons';

type UIChatMessage = ChatMessage & { pending?: boolean };

type ChatThread = {
  id: number;
  title: string;
  messages: UIChatMessage[];
};

const buildTitle = (messages: ChatMessage[]) => {
  const firstUser = messages.find((m) => m.role === 'user');
  if (!firstUser?.content) return 'New Chat';
  
  let text = firstUser.content.trim();
  
  // Remove common question words for cleaner titles
  text = text.replace(/^(can you|could you|please|how do i|how to|what is|what are|tell me about|explain)\s+/i, '');
  
  // Capitalize first letter
  text = text.charAt(0).toUpperCase() + text.slice(1);
  
  // Remove trailing punctuation
  text = text.replace(/[?.!]+$/, '');
  
  // Truncate with smart word boundary
  if (text.length > 50) {
    const truncated = text.slice(0, 50);
    const lastSpace = truncated.lastIndexOf(' ');
    text = (lastSpace > 30 ? truncated.slice(0, lastSpace) : truncated) + '...';
  }
  
  return text;
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
          // Load full details of first thread only
          const firstThread = await chatService.getThread(summaries[0].id);
          setThreads([{ id: firstThread.id, title: firstThread.title, messages: firstThread.messages }]);
          setActiveId(firstThread.id);

          // Store other thread summaries for lazy loading (just IDs and titles)
          const otherSummaries = summaries.slice(1).map(s => ({
            id: s.id,
            title: s.title,
            messages: [] as UIChatMessage[] // Empty until clicked
          }));
          
          setThreads((prev) => [...prev, ...otherSummaries]);
        }
      } catch (error) {
        console.error('Failed to load chat threads:', error);
        // Fallback: create a new thread
        try {
          const newThread = await chatService.createThread('New Chat', []);
          setThreads([{ id: newThread.id, title: newThread.title, messages: newThread.messages }]);
          setActiveId(newThread.id);
        } catch (fallbackError) {
          console.error('Critical: Cannot create fallback thread', fallbackError);
          // Show error to user - they cannot use chat at all
          setThreads([]);
          setActiveId(0);
        }
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
  const hasPending = messages.some((m) => m.pending);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Set loading state FIRST to prevent concurrent sends
    if (isSending || isLoading) return;
    setIsSending(true);
    
    const text = input.trim();
    if (!text || !activeThread) {
      setIsSending(false);
      return;
    }

    const newMessage: ChatMessage = { role: 'user', content: text };
    const history: ChatMessage[] = [...messages.filter((m) => !m.pending), newMessage];
    const optimisticUser: UIChatMessage = { role: 'user', content: text };
    const pendingAssistant: UIChatMessage = { role: 'assistant', content: 'Thinking...', pending: true };

    setInput('');
    setThreads((prev) =>
      prev.map((t) =>
        t.id === activeThread.id
          ? { ...t, messages: [...t.messages.filter((m) => !m.pending), optimisticUser, pendingAssistant] }
          : t
      )
    );

    try {
      
      // Add user message to backend
      const updatedThread = await chatService.updateThread(activeThread.id, {
        messages: history,
      });

      // Get AI response
      const response = await aiService.chat({ message: text, history });
      const assistantMessage: ChatMessage = { role: 'assistant', content: sanitizeAiText(response.reply) };
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
      
      // Remove optimistic messages on error
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? { ...t, messages: t.messages.filter((m) => !m.pending && m.role !== 'user' || m.content !== text) }
            : t
        )
      );
      
      // Show error message
      const errorMessage: UIChatMessage = { 
        role: 'assistant', 
        content: 'Failed to send message. Please try again.'
      };
      
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? { ...t, messages: [...messages.filter((m) => !m.pending), errorMessage] }
            : t
        )
      );
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
    if (!confirm('Delete this chat? This cannot be undone.')) return;
    
    try {
      await chatService.deleteThread(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
      
      if (activeId === id) {
        setThreads((prevThreads) => {
          const remaining = prevThreads.filter((t) => t.id !== id);
          if (remaining.length) {
            setActiveId(remaining[0].id);
          } else {
            // Create new thread asynchronously
            chatService.createThread('New Chat', []).then((freshThread) => {
              setThreads([{ id: freshThread.id, title: freshThread.title, messages: freshThread.messages }]);
              setActiveId(freshThread.id);
            }).catch((error) => {
              console.error('Failed to create replacement thread:', error);
            });
          }
          return remaining;
        });
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
      alert('Failed to delete chat. Please try again.');
    }
  };

  return (
    <div className="h-[calc(100dvh-6rem)] flex flex-col lg:flex-row gap-0 min-h-0 overflow-hidden relative -m-6">
      {/* Sidebar - Chat History */}
      <aside
        className={`bg-white dark:bg-slate-800 flex flex-col min-h-0 transition-all duration-300 ease-in-out ${
          historyCollapsed 
            ? 'w-0 lg:w-0 opacity-0 pointer-events-none absolute -left-full lg:relative lg:left-0' 
            : 'w-full lg:w-64 opacity-100 relative lg:relative'
        } flex-shrink-0 z-20 lg:z-auto border-r border-slate-200 dark:border-slate-700 md:rounded-l-xl lg:rounded-none`}
      >
        {/* Mobile overlay backdrop */}
        {!historyCollapsed && (
          <div 
            className="fixed inset-0 bg-black/50 lg:hidden -z-10"
            onClick={() => setHistoryCollapsed(true)}
          />
        )}
        <div className="px-4 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-700 flex items-center justify-between flex-shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Chats</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Stored in database</p>
          </div>
          <button
            onClick={() => setHistoryCollapsed((prev) => !prev)}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
            title="Collapse"
          >
            {Icons.chevronLeft}
          </button>
        </div>

        <div className="p-4 flex-shrink-0">
          <button
            onClick={handleNewChat}
            disabled={isLoading}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 transition-colors"
          >
            {Icons.plus}
            New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4 min-h-0">
          {isLoading ? (
            <div className="text-xs text-slate-500 dark:text-slate-400 px-4 py-2">Loading chats...</div>
          ) : threads.length === 0 ? (
            <div className="text-xs text-slate-500 dark:text-slate-400 px-4">No chats yet.</div>
          ) : (
            threads.map((thread) => (
              <button
                key={thread.id}
                onClick={async () => {
                  // Load thread messages if not already loaded
                  if (thread.messages.length === 0 && thread.id !== activeId) {
                    try {
                      const fullThread = await chatService.getThread(thread.id);
                      setThreads((prev) =>
                        prev.map((t) =>
                          t.id === thread.id
                            ? { ...t, messages: fullThread.messages, title: fullThread.title }
                            : t
                        )
                      );
                    } catch (error) {
                      console.error('Failed to load thread:', error);
                    }
                  }
                  setActiveId(thread.id);
                }}
                className={`w-full text-left px-4 py-3 rounded-xl transition-colors mb-2 border ${
                  thread.id === activeId
                    ? 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-700 text-indigo-900 dark:text-indigo-200'
                    : 'bg-white dark:bg-slate-800 border-transparent hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{thread.title}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{thread.messages.length} messages</p>
                  </div>
                  <span
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteChat(thread.id);
                    }}
                    className="text-slate-400 dark:text-slate-500 hover:text-red-500"
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
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-800 min-h-0 overflow-hidden transition-colors border-l border-slate-200 dark:border-slate-700 md:rounded-r-xl lg:rounded-none relative">
        {/* Floating menu button */}
        <button
          onClick={() => setHistoryCollapsed((prev) => !prev)}
          className="absolute top-3 left-3 z-10 p-2 rounded-full bg-white/90 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md text-slate-700 dark:text-slate-300 transition"
          title={historyCollapsed ? 'Show history' : 'Hide history'}
        >
          {Icons.menu}
        </button>

        {/* Chat Messages - Scrollable */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 sm:py-8 space-y-8 min-h-0 bg-gradient-to-b from-white to-slate-50 dark:from-slate-800 dark:to-slate-900">
          <div className="max-w-4xl mx-auto space-y-8">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
              <div className="text-center">
                <p className="text-sm">Loading chat...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-500 dark:text-slate-400 px-4">
              <div className="text-center max-w-xl space-y-4">
                <div className="mx-auto w-16 h-16 rounded-full bg-indigo-50 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-6">
                  {Icons.messageCircle}
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Start a Conversation</h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Ask me anything about technical interviews, coding problems, or career advice.</p>
                </div>
                <div className="pt-4 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Try asking:</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <span className="px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-700 text-xs text-slate-700 dark:text-slate-300">System design roadmap</span>
                    <span className="px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-700 text-xs text-slate-700 dark:text-slate-300">Common interview questions</span>
                    <span className="px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-700 text-xs text-slate-700 dark:text-slate-300">Algorithm practice tips</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 sm:gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role !== 'user' && (
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center text-xs sm:text-sm font-bold flex-shrink-0 shadow-md">
                    AI
                  </div>
                )}
                <div
                  className={`max-w-[75%] sm:max-w-[65%] lg:max-w-[60%] rounded-2xl px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base leading-relaxed shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-sm'
                      : 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-bl-sm'
                  }`}
                >
                  <p className={`whitespace-pre-wrap break-words ${msg.pending ? 'text-slate-500 dark:text-slate-400 italic' : ''}`}>
                    {msg.role === 'assistant' ? sanitizeAiText(msg.content) : msg.content}
                  </p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 dark:from-slate-500 dark:to-slate-700 text-white flex items-center justify-center text-xs sm:text-sm font-bold flex-shrink-0 shadow-md">
                    You
                  </div>
                )}
              </div>
            ))
          )}
          {isSending && !hasPending && (
            <div className="flex gap-3 sm:gap-4 items-center">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center text-xs sm:text-sm font-bold shadow-md">
                AI
              </div>
              <div className="px-4 sm:px-5 py-3 rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 text-sm flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
                <span>Thinking...</span>
              </div>
            </div>
          )}
          </div>
          <div ref={scrollRef} />
        </div>

        {/* Chat Input - Minimal ChatGPT Style */}
        <form onSubmit={handleSend} className="px-4 sm:px-6 md:px-8 lg:px-12 py-4 sm:py-5 bg-white dark:bg-slate-800 flex-shrink-0">
          <div className="flex items-end gap-2 sm:gap-3 max-w-4xl mx-auto">
            <textarea
              id="chatInput"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
              placeholder="Message AI..."
              className="flex-1 min-h-[40px] max-h-32 resize-none px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm transition-all"
              disabled={isSending || isLoading}
              rows={1}
            />
            <button
              type="submit"
              disabled={isSending || !input.trim() || isLoading}
              className="h-10 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 text-white text-sm font-medium transition-all flex-shrink-0 disabled:cursor-not-allowed"
            >
              {isSending ? '...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
