'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { sessionService } from '@/lib/services/sessionService';
import { questionService } from '@/lib/services/questionService';
import { aiService } from '@/lib/services/aiService';
import { Icons } from '@/components/ui/Icons';
import { Message, Question, AIStatusResponse } from '@/types/api';

type InputMode = 'text' | 'code' | 'voice';

interface LoadingState {
  messages: boolean;
  sending: boolean;
  finalizing: boolean;
  ending: boolean;
  replaying: boolean;
}

export const InterviewSection = () => {
  const {
    currentSession,
    messages,
    addMessage,
    setMessages,
    setError,
    setEvaluation,
    clearSession,
  } = useSessionStore();
  const { setCurrentPage } = useUIStore();

  // State management
  const [inputMode, setInputMode] = useState<InputMode>('text');
  const [messageText, setMessageText] = useState('');
  const [codeText, setCodeText] = useState('');
  const [loading, setLoading] = useState<LoadingState>({
    messages: false,
    sending: false,
    finalizing: false,
    ending: false,
    replaying: false,
  });
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [isQuestionCollapsed, setIsQuestionCollapsed] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Memoized: extract the latest question ID from messages
  const latestQuestionId = useMemo(() => {
    if (!currentSession) return null;
    // Search backwards through messages for the latest question ID
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const qid = messages[i].current_question_id;
      if (qid) return qid;
    }
    return currentSession.current_question_id ?? null;
  }, [messages, currentSession?.current_question_id]);

  // Initialize session and load messages on mount
  useEffect(() => {
    if (currentSession) {
      loadMessages();
    }
  }, [currentSession?.id]);

  // Auto-scroll chat to bottom when messages update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isChatExpanded]);

  // Timer effect - increment elapsed seconds
  useEffect(() => {
    if (!currentSession || currentSession.stage === 'done') {
      return;
    }

    const timer = setInterval(() => {
      setElapsedSec((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [currentSession?.id, currentSession?.stage]);

  // Load AI status on mount
  useEffect(() => {
    loadAIStatus();
    const statusInterval = setInterval(loadAIStatus, 30000); // Poll every 30s
    return () => clearInterval(statusInterval);
  }, []);

  // Load current question when latest question ID changes
  useEffect(() => {
    loadCurrentQuestion();
  }, [latestQuestionId]);

  /**
   * Load session messages from backend
   * If no messages exist, start the session
   */
  const loadMessages = async () => {
    if (!currentSession) return;
    try {
      setLoading((prev) => ({ ...prev, messages: true }));
      setLocalError(null);
      const result = await sessionService.getMessages(currentSession.id);
      setMessages(result);

      // If no messages, start the session
      if (result.length === 0) {
        const firstMessage = await sessionService.startSession(currentSession.id);
        addMessage(firstMessage);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load messages';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, messages: false }));
    }
  };

  /**
   * Load AI service status
   */
  const loadAIStatus = async () => {
    try {
      const status = await aiService.getStatus();
      setAiStatus(status);
    } catch (err) {
      console.error('Failed to load AI status:', err);
    }
  };

  /**
   * Load the current question details
   */
  const loadCurrentQuestion = async () => {
    if (!latestQuestionId) {
      setQuestion(null);
      return;
    }
    try {
      const q = await questionService.getQuestion(latestQuestionId);
      setQuestion(q);
    } catch (err) {
      console.error('Failed to load question:', err);
      setQuestion(null);
    }
  };

  /**
   * Format elapsed time as MM:SS
   */
  const formatTimer = (total: number) => {
    const minutes = Math.floor(total / 60).toString().padStart(2, '0');
    const seconds = (total % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  /**
   * Build message payload based on input mode
   * - text mode: plain text
   * - code mode: markdown code block
   * - voice mode: not implemented yet
   */
  const buildMessagePayload = (): string => {
    if (inputMode === 'code') {
      const trimmed = codeText.trim();
      if (!trimmed) return '';
      return `\`\`\`\n${trimmed}\n\`\`\``;
    }
    if (inputMode === 'voice') {
      return ''; // Not implemented yet
    }
    return messageText.trim();
  };

  /**
   * Send message to backend and add AI response to chat
   */
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentSession) return;

    const payload = buildMessagePayload();
    if (!payload) {
      setLocalError('Please enter a message');
      return;
    }

    try {
      setLocalError(null);
      setLoading((prev) => ({ ...prev, sending: true }));

      // Optimistically add user message to local state
      const userMessage: Message = {
        id: Date.now(), // Temporary ID
        session_id: currentSession.id,
        role: 'student',
        content: payload,
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);

      // Send message to backend and get AI response
      const response = await sessionService.sendMessage(currentSession.id, {
        content: payload,
      });

      // Add AI response to local state
      addMessage(response);

      // Clear input fields
      setMessageText('');
      setCodeText('');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to send message';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, sending: false }));
    }
  };

  /**
   * Finalize session and navigate to results
   * This endpoint calls the scoring engine and creates evaluation
   */
  const handleFinalize = async () => {
    if (!currentSession) return;
    try {
      setLocalError(null);
      setLoading((prev) => ({ ...prev, finalizing: true }));

      const result = await sessionService.finalizeSession(currentSession.id);
      setEvaluation(result);
      setCurrentPage('results');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to finalize session';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, finalizing: false }));
    }
  };

  /**
   * Delete session and return to dashboard
   */
  const handleEndSession = async () => {
    if (!currentSession) return;
    try {
      setLocalError(null);
      setLoading((prev) => ({ ...prev, ending: true }));

      await sessionService.deleteSession(currentSession.id);
      clearSession();
      setCurrentPage('dashboard');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to end session';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, ending: false }));
    }
  };

  /**
   * Replay the last AI message as speech (if TTS enabled)
   */
  const handleReplayLast = async () => {
    const lastAiMessage = [...messages].reverse().find((m) => m.role === 'interviewer');
    if (!lastAiMessage) {
      setLocalError('No interviewer message to replay');
      return;
    }

    try {
      setLocalError(null);
      setLoading((prev) => ({ ...prev, replaying: true }));

      const result = await aiService.generateSpeech({ text: lastAiMessage.content });

      if (result.mode === 'audio' && result.audio_url) {
        if (!audioRef.current) {
          audioRef.current = new Audio();
        }
        audioRef.current.src = result.audio_url;
        audioRef.current.onerror = () => {
          setLocalError('Failed to play audio');
        };
        await audioRef.current.play();
      } else {
        setLocalError('Audio not available');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to replay audio';
      setLocalError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, replaying: false }));
    }
  };

  /**
   * Copy question text to clipboard
   */
  const copyQuestion = async () => {
    if (!question) return;
    const text = `${question.title}\n\n${question.prompt}`;
    try {
      await navigator.clipboard.writeText(text);
      // Brief visual feedback
      setTimeout(() => {
        setLocalError(null);
      }, 2000);
    } catch (err) {
      setLocalError('Failed to copy question');
    }
  };

  // If no active session, show empty state
  if (!currentSession) {
    return (
      <div className="flex items-center justify-center min-h-full">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
            {Icons.play}
          </div>
          <p className="text-lg font-semibold text-gray-900">No Active Session</p>
          <p className="text-sm text-gray-500 mt-2">
            Start a new interview from the dashboard to begin.
          </p>
        </div>
      </div>
    );
  }

  // Determine session status UI
  const statusColor =
    currentSession.stage === 'done'
      ? 'bg-emerald-500/10 text-emerald-700'
      : currentSession.stage === 'intro'
        ? 'bg-blue-500/10 text-blue-700'
        : 'bg-amber-500/10 text-amber-700';

  const aiStatusColor =
    aiStatus?.status === 'online'
      ? 'bg-emerald-50 text-emerald-700'
      : aiStatus?.status === 'offline'
        ? 'bg-red-50 text-red-700'
        : 'bg-gray-50 text-gray-600';

  const aiStatusDot =
    aiStatus?.status === 'online'
      ? 'bg-emerald-500'
      : aiStatus?.status === 'offline'
        ? 'bg-red-500'
        : 'bg-gray-400';

  return (
    <div className="flex flex-col h-[calc(100dvh-8rem)] bg-gradient-to-br from-gray-50 to-white overflow-hidden">
      {/* Error Toast */}
      {localError && (
        <div className="fixed top-4 right-4 z-50 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg animate-in fade-in slide-in-from-right">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-5 h-5 text-red-600 mt-0.5">
              {Icons.alertCircle}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900">{localError}</p>
            </div>
            <button
              onClick={() => setLocalError(null)}
              className="flex-shrink-0 text-red-600 hover:text-red-800"
            >
              {Icons.close}
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-3 sm:px-4 py-2 sm:py-3 shadow-sm flex-shrink-0">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-2 sm:gap-3">
          {/* Session Info */}
          <div className="flex-1 min-w-0 w-full lg:w-auto">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
              <div className="flex-1 min-w-0">
                <h1 className="text-lg sm:text-xl font-bold text-gray-900">Live Interview</h1>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className={`inline-flex items-center gap-1 px-2.5 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium ${statusColor}`}>
                    <span className="w-2 h-2 rounded-full bg-current" />
                    {currentSession.stage?.toUpperCase() || 'IDLE'}
                  </span>
                  <span className="text-xs sm:text-sm text-gray-600">{currentSession.role}</span>
                  <span className="text-xs text-gray-400">•</span>
                  <span className="text-xs sm:text-sm text-gray-600 capitalize">{currentSession.track?.replace(/_/g, ' ')}</span>
                  <span className="text-xs text-gray-400">•</span>
                  <span className="text-xs sm:text-sm text-gray-600 capitalize">{currentSession.difficulty}</span>
                </div>
              </div>

              {/* Timer */}
              <div className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 self-start sm:self-auto">
                <div className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600">
                  {Icons.clock}
                </div>
                <span className="font-mono font-bold text-blue-900 text-sm sm:text-base">{formatTimer(elapsedSec)}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap w-full lg:w-auto justify-start lg:justify-end">
            <button
              onClick={() => setIsChatExpanded(!isChatExpanded)}
              disabled={loading.sending || loading.finalizing}
              className="px-3 sm:px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-xs sm:text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors flex items-center gap-1.5 sm:gap-2"
              title={isChatExpanded ? 'Split view' : 'Focus on chat'}
            >
              <div className="w-4 h-4">
                {isChatExpanded ? Icons.collapse : Icons.expand}
              </div>
              <span className="hidden sm:inline">{isChatExpanded ? 'Split View' : 'Focus Chat'}</span>
            </button>

            <button
              onClick={handleReplayLast}
              disabled={loading.replaying || messages.length === 0}
              className="px-3 sm:px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-xs sm:text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {loading.replaying ? 'Playing...' : 'Replay'}
            </button>

            <button
              onClick={handleEndSession}
              disabled={loading.ending}
              className="px-3 sm:px-4 py-2 rounded-lg border border-red-300 text-red-600 text-xs sm:text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              {loading.ending ? 'Ending...' : 'End'}
            </button>

            <button
              onClick={() => setCurrentPage('dashboard')}
              className="px-3 sm:px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-xs sm:text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap"
            >
              New Session
            </button>

            <button
              onClick={handleFinalize}
              disabled={loading.finalizing || currentSession.stage === 'done'}
              className="px-3 sm:px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 text-white text-xs sm:text-sm font-semibold hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 shadow-sm transition-colors whitespace-nowrap"
            >
              {loading.finalizing ? 'Evaluating...' : 'Submit & Evaluate'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden min-h-0 p-2 sm:p-3">
        <div className={`grid gap-2 sm:gap-3 h-full ${isChatExpanded ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-[minmax(200px,280px)_1fr]'}`} style={{ gridTemplateRows: '1fr' }}>
          {/* Left Panel: Question Card (hidden in chat expanded mode) */}
          {!isChatExpanded && (
            <div className="flex flex-col gap-2 min-h-0 overflow-y-auto">
              {/* Current Question Card */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden flex flex-col flex-shrink-0">
                <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
                  <h3 className="text-xs font-semibold text-gray-900 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-500" />
                    Question
                  </h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={copyQuestion}
                      disabled={!question}
                      className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50 transition-colors"
                      title="Copy question"
                    >
                      {Icons.copy}
                    </button>
                    <button
                      onClick={() => setIsQuestionCollapsed(!isQuestionCollapsed)}
                      className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                      title={isQuestionCollapsed ? 'Expand' : 'Collapse'}
                    >
                      {isQuestionCollapsed ? Icons.chevronDown : Icons.chevronUp}
                    </button>
                  </div>
                </div>

                {!isQuestionCollapsed && (
                  <div className="px-3 py-2 space-y-2 overflow-y-auto max-h-60">
                    {question ? (
                      <>
                        <div>
                          <p className="text-xs font-bold text-gray-900">{question.title}</p>
                          <p className="text-xs text-gray-500 mt-0.5 flex flex-wrap gap-1">
                            <span>{question.company_style}</span>
                            <span>•</span>
                            <span className="capitalize">{question.difficulty}</span>
                          </p>
                        </div>
                        <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap font-mono">{question.prompt}</p>
                        {question.tags && question.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {question.tags.map((tag) => (
                              <span
                                key={tag}
                                className="inline-flex items-center px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs"
                              >
                                #{tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-xs text-gray-500 text-center py-4">
                        Question will appear here once the session starts.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Answer Flow Guide Card */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden flex flex-col flex-shrink-0">
                <div className="px-3 py-2 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
                  <h4 className="text-xs font-semibold text-gray-900">Answer Structure</h4>
                </div>
                <div className="p-2 space-y-1">
                  {[
                    { id: 'plan', title: 'Plan', desc: 'Clarify requirements & constraints' },
                    { id: 'solve', title: 'Solve', desc: 'Walk through solution approach' },
                    { id: 'optimize', title: 'Optimize', desc: 'Discuss time/space tradeoffs' },
                    { id: 'validate', title: 'Validate', desc: 'Test edge cases' },
                  ].map((step, idx) => (
                    <div
                      key={step.id}
                      className="flex gap-2 p-1.5 rounded-md bg-gradient-to-r from-gray-50 to-white border border-gray-100 hover:border-blue-200 transition-colors"
                    >
                      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-900">{step.title}: <span className="font-normal text-gray-600">{step.desc}</span></p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Right Panel: Chat */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col min-h-0 overflow-hidden">
            {/* Chat Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white flex-shrink-0">
              <h3 className="text-xs font-semibold text-gray-900">Interview Chat</h3>
              <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${aiStatusColor}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${aiStatusDot}`} />
                {aiStatus?.status === 'online' ? 'Online' : aiStatus?.status === 'offline' ? 'Offline' : '...'}
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-2 sm:p-3 space-y-2 min-h-0">
              {loading.messages ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="w-6 h-6 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin mx-auto mb-2" />
                    <p className="text-xs text-gray-600">Loading...</p>
                  </div>
                </div>
              ) : messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-2">
                      {Icons.messageCircle}
                    </div>
                    <p className="text-xs text-gray-600">Waiting for interviewer...</p>
                  </div>
                </div>
              ) : (
                messages.map((msg: Message) => (
                  <div
                    key={msg.id}
                    className={`flex gap-1.5 ${msg.role === 'student' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[90%] rounded-xl px-2.5 py-1.5 ${
                        msg.role === 'student'
                          ? 'bg-blue-600 text-white rounded-br-sm'
                          : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                      }`}
                    >
                      <p className="text-xs leading-relaxed whitespace-pre-wrap break-words">{msg.content}</p>
                      {msg.created_at && (
                        <p className={`text-xs mt-0.5 opacity-70`}>
                          {new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input Form */}
            <form onSubmit={handleSendMessage} className="border-t border-gray-100 p-2 sm:p-3 space-y-1.5 sm:space-y-2 bg-gradient-to-t from-gray-50 to-white flex-shrink-0">
              {/* Input Mode Tabs */}
              <div className="flex gap-1.5 sm:gap-2 flex-wrap">
                {(['text', 'code', 'voice'] as InputMode[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setInputMode(mode)}
                    disabled={loading.sending || currentSession.stage === 'done'}
                    className={`px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs font-medium rounded-full border transition-colors flex items-center gap-1 sm:gap-1.5 ${
                      inputMode === mode
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300 disabled:opacity-50'
                    }`}
                  >
                    {mode === 'text' ? (
                      <>
                        {Icons.pencil}
                        <span>Text</span>
                      </>
                    ) : mode === 'code' ? (
                      <>
                        {Icons.code}
                        <span>Code</span>
                      </>
                    ) : (
                      <>
                        {Icons.microphone}
                        <span>Voice</span>
                      </>
                    )}
                  </button>
                ))}
              </div>

              {/* Input Area */}
              {inputMode === 'code' ? (
                <textarea
                  value={codeText}
                  onChange={(e) => setCodeText(e.target.value)}
                  disabled={loading.sending || currentSession.stage === 'done'}
                  rows={4}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 resize-none"
                  placeholder="Paste your code here..."
                />
              ) : inputMode === 'voice' ? (
                <div className="p-3 sm:p-4 rounded-lg border-2 border-dashed border-gray-300 text-center text-xs sm:text-sm text-gray-500 bg-gray-50 flex items-center justify-center gap-2">
                  {Icons.microphone}
                  <span>Voice input coming soon. Please use text or code mode.</span>
                </div>
              ) : (
                <textarea
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  disabled={loading.sending || currentSession.stage === 'done'}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 resize-none"
                  placeholder="Share your approach or ask clarifying questions..."
                />
              )}

              {/* Submit Area */}
              <div className="flex items-center justify-between gap-2 pt-1 sm:pt-2">
                <p className="text-xs text-gray-500 items-center gap-1.5 hidden sm:flex">
                  {Icons.lightBulb}
                  <span>Plan → Solve → Optimize → Validate</span>
                </p>
                <button
                  type="submit"
                  disabled={loading.sending || currentSession.stage === 'done' || (!messageText.trim() && !codeText.trim())}
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-semibold hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 shadow-sm transition-colors ml-auto"
                >
                  {loading.sending ? 'Sending...' : 'Send'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
