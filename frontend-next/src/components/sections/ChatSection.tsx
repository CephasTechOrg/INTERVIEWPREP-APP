'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { aiService } from '@/lib/services/aiService';
import { chatService, type ChatMessage } from '@/lib/services/chatService';
import { sanitizeAiText } from '@/lib/utils/text';
import { Icons } from '@/components/ui/Icons';
import { useAuthStore } from '@/lib/stores/authStore';
import { useSessionStore } from '@/lib/stores/sessionStore';

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
  const { user } = useAuthStore();
  const { currentSession } = useSessionStore();
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [rateLimitMessage, setRateLimitMessage] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const baseInputRef = useRef('');

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
    if (typeof window === 'undefined') return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    setSpeechSupported(true);
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      let finalText = '';
      let interimText = '';

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0]?.transcript ?? '';
        if (event.results[i].isFinal) {
          finalText += transcript;
        } else {
          interimText += transcript;
        }
      }

      setInput(`${baseInputRef.current}${finalText}${interimText}`);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.onresult = null;
      recognition.onend = null;
      recognition.onerror = null;
      recognition.stop?.();
      recognitionRef.current = null;
    };
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

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    

    if (isListening) {
      recognitionRef.current?.stop?.();
      setIsListening(false);
    }
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
    } catch (error: any) {
      console.error('Failed to send message:', error);
      
      // Check for rate limit error (429)
      const isRateLimit = error?.response?.status === 429;
      const rateLimitDetail = error?.response?.data?.detail;
      
      if (isRateLimit && rateLimitDetail?.message) {
        setRateLimitMessage(rateLimitDetail.message);
        // Auto-dismiss after 5 seconds
        setTimeout(() => setRateLimitMessage(null), 5000);
      }
      
      // Remove optimistic messages on error
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? { ...t, messages: t.messages.filter((m) => !m.pending && m.role !== 'user' || m.content !== text) }
            : t
        )
      );
      
      // Show error message in chat
      const errorContent = isRateLimit && rateLimitDetail?.message
        ? rateLimitDetail.message
        : 'Failed to send message. Please try again.';
      const errorMessage: UIChatMessage = { 
        role: 'assistant', 
        content: errorContent
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

  const toggleListening = () => {
    if (!speechSupported) return;
    const recognition = recognitionRef.current;
    if (!recognition) return;

    if (isListening) {
      recognition.stop?.();
      return;
    }

    baseInputRef.current = input ? `${input} ` : '';
    try {
      recognition.start?.();
      setIsListening(true);
    } catch {
      setIsListening(false);
    }
  };

  const renderInline = (text: string, keyPrefix: string) => {
    const boldParts = text.split(/(\*\*[^*]+\*\*)/g);
    return boldParts.flatMap((boldPart, bIdx) => {
      if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
        const content = boldPart.slice(2, -2);
        return (
          <strong key={`${keyPrefix}-b-${bIdx}`} className="font-semibold text-slate-900 dark:text-slate-100">
            {content}
          </strong>
        );
      }

      const codeParts = boldPart.split(/(`[^`]+`)/g);
      return codeParts.map((codePart, cIdx) => {
        if (codePart.startsWith('`') && codePart.endsWith('`')) {
          const content = codePart.slice(1, -1);
          return (
            <code
              key={`${keyPrefix}-c-${bIdx}-${cIdx}`}
              className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[0.9em] font-mono"
            >
              {content}
            </code>
          );
        }

        return (
          <span key={`${keyPrefix}-t-${bIdx}-${cIdx}`}>
            {codePart}
          </span>
        );
      });
    });
  };

  const renderTextBlock = (block: string, keyPrefix: string) => {
    const lines = block.split('\n');
    const elements: React.ReactNode[] = [];
    let listItems: string[] = [];

    const flushList = (idx: number) => {
      if (!listItems.length) return;
      elements.push(
        <ul key={`${keyPrefix}-list-${idx}`} className="list-disc pl-5 space-y-1">
          {listItems.map((item, li) => (
            <li key={`${keyPrefix}-li-${idx}-${li}`}>
              {renderInline(item, `${keyPrefix}-li-${idx}-${li}`)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
    };

    lines.forEach((line, idx) => {
      const bulletMatch = line.match(/^\s*[-*]\s+(.*)$/);
      if (bulletMatch) {
        listItems.push(bulletMatch[1]);
        return;
      }

      flushList(idx);

      if (!line.trim()) {
        elements.push(<div key={`${keyPrefix}-sp-${idx}`} className="h-2" />);
        return;
      }

      elements.push(
        <p key={`${keyPrefix}-p-${idx}`} className="whitespace-pre-wrap break-words">
          {renderInline(line, `${keyPrefix}-p-${idx}`)}
        </p>
      );
    });

    flushList(lines.length);
    return elements;
  };

  const renderAiMessage = (text: string) => {
    const safe = sanitizeAiText(text);
    const parts = safe.split(/```/g);

    return parts.map((part, idx) => {
      if (idx % 2 === 1) {
        const lines = part.split('\n');
        let language = '';
        let code = part;

        if (lines.length > 1 && /^[a-zA-Z0-9#.+_-]+$/.test(lines[0].trim())) {
          language = lines[0].trim();
          code = lines.slice(1).join('\n');
        }

        return (
          <div key={`code-${idx}`} className="space-y-2">
            {language && (
              <span className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                {language}
              </span>
            )}
            <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs sm:text-sm overflow-x-auto">
              <code className="font-mono whitespace-pre-wrap">{code.trimEnd()}</code>
            </pre>
          </div>
        );
      }

      return (
        <div key={`txt-${idx}`} className="space-y-2">
          {renderTextBlock(part, `txt-${idx}`)}
        </div>
      );
    });
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
      {/* Rate Limit Info Toast */}
      {rateLimitMessage && (
        <div className="fixed top-20 right-4 z-[60] bg-amber-50 dark:bg-amber-900/90 border border-amber-200 dark:border-amber-800 rounded-xl p-3 shadow-xl max-w-sm">
          <div className="flex items-start gap-2">
            <div className="flex-shrink-0 w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5">{Icons.alertCircle}</div>
            <p className="text-sm text-amber-900 dark:text-amber-100 flex-1">{rateLimitMessage}</p>
            <button onClick={() => setRateLimitMessage(null)} className="text-amber-600 dark:text-amber-400 hover:text-amber-800">{Icons.close}</button>
          </div>
        </div>
      )}

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
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 transition-colors"
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
                    ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 text-blue-900 dark:text-blue-200'
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
                <div className="mx-auto w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-6">
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
                className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role !== 'user' && (
                  <div className="w-7 h-7 rounded-full overflow-hidden flex-shrink-0 shadow-sm">
                    {currentSession?.interviewer?.image_url ? (
                      <img src={currentSession.interviewer.image_url} alt="Interviewer" className="w-full h-full object-cover object-top" />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-blue-500 to-blue-600 text-white flex items-center justify-center text-xs font-bold">
                        {currentSession?.interviewer?.name?.[0] || 'AI'}
                      </div>
                    )}
                  </div>
                )}
                <div
                  className={`max-w-[75%] sm:max-w-[65%] lg:max-w-[60%] rounded-xl px-3 py-2 text-sm leading-relaxed shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-bl-sm'
                  }`}
                >
                  <div className={msg.pending ? 'text-slate-500 dark:text-slate-400 italic' : ''}>
                    {msg.role === 'assistant' ? renderAiMessage(msg.content) : msg.content}
                  </div>
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full overflow-hidden flex-shrink-0 shadow-sm">
                    {user?.profile && typeof user.profile === 'object' && 'avatar_url' in user.profile && (user.profile as any).avatar_url ? (
                      <img src={(user.profile as any).avatar_url} alt="Your avatar" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-slate-700 to-slate-900 dark:from-slate-500 dark:to-slate-700 text-white flex items-center justify-center text-xs font-bold">
                        {(user?.full_name?.split(/\s+/)[0]?.[0] || user?.email?.[0] || 'U').toUpperCase()}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
          {isSending && !hasPending && (
            <div className="flex gap-3 sm:gap-4 items-center">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-white flex items-center justify-center text-xs sm:text-sm font-bold shadow-md">
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
              onChange={(e) => {
                const value = e.target.value;
                if (isListening) {
                  baseInputRef.current = value;
                }
                setInput(value);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
              placeholder="Message AI..."
              className="flex-1 min-h-[40px] max-h-32 resize-none px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-600 text-sm transition-all"
              disabled={isSending || isLoading}
              rows={1}
            />
            <button
              type="button"
              onClick={toggleListening}
              disabled={!speechSupported || isLoading}
              className={`h-10 w-10 rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-all ${
                isListening ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700'
              } ${!speechSupported ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={speechSupported ? (isListening ? 'Stop voice input' : 'Start voice input') : 'Voice input not supported'}
            >
              {Icons.mic}
            </button>
            <button
              type="submit"
              disabled={isSending || !input.trim() || isLoading}
              className="h-10 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 text-white text-sm font-medium transition-all flex-shrink-0 disabled:cursor-not-allowed"
            >
              {isSending ? '...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
