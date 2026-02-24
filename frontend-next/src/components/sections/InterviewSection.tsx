'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { sessionService } from '@/lib/services/sessionService';
import { questionService } from '@/lib/services/questionService';
import { aiService } from '@/lib/services/aiService';
import { Icons } from '@/components/ui/Icons';
import { sanitizeAiText } from '@/lib/utils/text';
import { Message, Question, AIStatusResponse } from '@/types/api';

type InputMode = 'text' | 'code' | 'voice';

interface LoadingState {
  messages: boolean;
  sending: boolean;
  finalizing: boolean;
  ending: boolean;
  replaying: boolean;
}

type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

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
  const { setCurrentPage, voiceEnabled, setVoiceEnabled } = useUIStore();

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
  const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState(false);
  const [isPageExpanded, setIsPageExpanded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);
  const [ttsProvider, setTtsProvider] = useState<string | null>(null);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceText, setVoiceText] = useState('');
  const [voiceInterim, setVoiceInterim] = useState('');
  const [audioUnlocked, setAudioUnlocked] = useState(false);
  const [needsAudioUnlock, setNeedsAudioUnlock] = useState(false);

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const lastSpokenMessageIdRef = useRef<string | null>(null);
  const startRequestedRef = useRef(false);
  const audioBlobUrls = useRef<string[]>([]);
  const loadMessagesAbortRef = useRef<AbortController | null>(null);

  // Auto-resize textarea
  const autoResizeTextarea = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 150);
      textareaRef.current.style.height = `${Math.max(40, newHeight)}px`;
    }
  }, []);

  // Memoized: extract the latest question ID from messages
  const latestQuestionId = useMemo(() => {
    if (!currentSession) return null;
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const qid = messages[i].current_question_id;
      if (qid) return qid;
    }
    return currentSession.current_question_id ?? null;
  }, [messages, currentSession?.current_question_id]);

  // Detect mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024); // lg breakpoint
      // Auto-collapse on mobile
      if (window.innerWidth < 1024) {
        setIsLeftPanelCollapsed(true);
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Initialize session and load messages on mount
  useEffect(() => {
    if (currentSession) {
      loadMessages();
    }
  }, [currentSession?.id]);

  // Auto-scroll chat to bottom when messages update
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages.length]);

  // Auto-resize textarea when text changes
  useEffect(() => {
    autoResizeTextarea();
  }, [messageText, codeText, autoResizeTextarea]);

  // Timer effect
  useEffect(() => {
    if (!currentSession) return;
    
    const timer = setInterval(() => {
      // Check stage in callback to ensure timer stops when session ends
      if (currentSession.stage !== 'done') {
        setElapsedSec((prev) => prev + 1);
      }
    }, 1000);
    
    return () => clearInterval(timer);
  }, [currentSession?.id, currentSession?.stage]);

  // Load AI status on mount and poll periodically (only when session active)
  useEffect(() => {
    if (currentSession?.stage === 'done') return;
    
    loadAIStatus();
    const statusInterval = setInterval(loadAIStatus, 30000);
    return () => clearInterval(statusInterval);
  }, [currentSession?.stage]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceSupported(false);
      return;
    }

    const recognition: SpeechRecognitionInstance = new SpeechRecognitionCtor();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: any) => {
      let finalText = '';
      let interimText = '';

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result?.[0]?.transcript ?? '';
        if (result.isFinal) {
          finalText += transcript;
        } else {
          interimText += transcript;
        }
      }

      if (finalText.trim()) {
        setVoiceText((prev) => {
          const trimmed = finalText.trim();
          return prev ? `${prev} ${trimmed}` : trimmed;
        });
      }
      setVoiceInterim(interimText.trim());
    };

    recognition.onerror = (event: any) => {
      const message = event?.error ? `Voice error: ${event.error}` : 'Voice error';
      setLocalError(message);
      setIsListening(false);
      setVoiceInterim('');
    };

    recognition.onend = () => {
      setIsListening(false);
      setVoiceInterim('');
    };

    recognitionRef.current = recognition;
    setVoiceSupported(true);

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }
      setIsListening(false);
    };
  }, []);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current.load();
      }
      // Revoke all blob URLs
      audioBlobUrls.current.forEach((url) => URL.revokeObjectURL(url));
      audioBlobUrls.current = [];
    };
  }, []);

  // Stop listening when leaving voice mode
  useEffect(() => {
    if (inputMode !== 'voice' && isListening) {
      recognitionRef.current?.stop();
    }
  }, [inputMode, isListening]);

  useEffect(() => {
    if (currentSession?.stage === 'done' && isListening) {
      recognitionRef.current?.stop();
    }
  }, [currentSession?.stage, isListening]);

  // Prevent background scroll when expanded
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (isPageExpanded) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
    document.body.style.overflow = '';
    return;
  }, [isPageExpanded]);

  // Unlock audio on first user interaction
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const unlock = () => {
      setAudioUnlocked(true);
      setNeedsAudioUnlock(false);
      window.removeEventListener('pointerdown', unlock);
      window.removeEventListener('keydown', unlock);
      window.removeEventListener('touchstart', unlock);
    };
    window.addEventListener('pointerdown', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
    window.addEventListener('touchstart', unlock, { once: true });
    return () => {
      window.removeEventListener('pointerdown', unlock);
      window.removeEventListener('keydown', unlock);
      window.removeEventListener('touchstart', unlock);
    };
  }, []);

  // Load current question when latest question ID changes
  useEffect(() => {
    loadCurrentQuestion();
  }, [latestQuestionId]);

  // Auto-play new interviewer messages
  useEffect(() => {
    if (loading.messages) return;
    const lastAiMessage = [...messages].reverse().find((m) => m.role === 'interviewer');
    if (!lastAiMessage) return;

    const key =
      typeof lastAiMessage.id === 'number'
        ? `id:${lastAiMessage.id}`
        : `ts:${lastAiMessage.created_at ?? ''}:${lastAiMessage.content}`;

    if (!lastSpokenMessageIdRef.current) {
      lastSpokenMessageIdRef.current = key;
      if (voiceEnabled && messages.length <= 1) {
        if (!audioUnlocked) {
          setNeedsAudioUnlock(true);
          return;
        }
        playTts(lastAiMessage.content);
      }
      return;
    }

    if (lastSpokenMessageIdRef.current === key) return;
    lastSpokenMessageIdRef.current = key;

    if (!voiceEnabled) return;
    if (!audioUnlocked) {
      setNeedsAudioUnlock(true);
      return;
    }
    playTts(lastAiMessage.content);
  }, [messages, voiceEnabled, loading.messages]);

  const loadMessages = async () => {
    if (!currentSession) return;
    
    // Cancel any previous load operation
    loadMessagesAbortRef.current?.abort();
    loadMessagesAbortRef.current = new AbortController();
    
    try {
      setLoading((prev) => ({ ...prev, messages: true }));
      setLocalError(null);
      const result = await sessionService.getMessages(currentSession.id);
      setMessages(result);

      if (result.length === 0) {
        if (startRequestedRef.current) return;
        startRequestedRef.current = true;
        const firstMessage = await sessionService.startSession(currentSession.id);
        addMessage(firstMessage);
        startRequestedRef.current = false;
      } else {
        startRequestedRef.current = false;
      }
    } catch (err) {
      startRequestedRef.current = false;
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') return;
      const errorMsg = err instanceof Error ? err.message : 'Failed to load messages';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, messages: false }));
    }
  };

  const loadAIStatus = async () => {
    try {
      const status = await aiService.getStatus();
      setAiStatus(status);
    } catch (err) {
      console.error('Failed to load AI status:', err);
    }
  };

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

  const formatTimer = (total: number) => {
    const minutes = Math.floor(total / 60).toString().padStart(2, '0');
    const seconds = (total % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  const buildVoiceDraft = () => {
    return [voiceText, voiceInterim].filter(Boolean).join(' ').trim();
  };

  const buildMessagePayload = (): string => {
    if (inputMode === 'code') {
      const trimmed = codeText.trim();
      if (!trimmed) return '';
      return `\`\`\`\n${trimmed}\n\`\`\``;
    }
    if (inputMode === 'voice') {
      const draft = buildVoiceDraft();
      return draft;
    }
    return messageText.trim();
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!currentSession || loading.sending) return;

    // Set loading state FIRST to prevent concurrent sends
    setLoading((prev) => ({ ...prev, sending: true }));

    const content = buildMessagePayload();
    if (!content) {
      setLoading((prev) => ({ ...prev, sending: false }));
      return;
    }

    const tempId = Date.now();
    const studentMessage: Message = {
      id: tempId,
      session_id: currentSession.id,
      role: 'student',
      content,
      created_at: new Date().toISOString(),
    };

    addMessage(studentMessage);
    if (inputMode === 'code') setCodeText('');
    else if (inputMode === 'voice') {
      setVoiceText('');
      setVoiceInterim('');
    } else setMessageText('');

    try {
      const reply = await sessionService.sendMessage(currentSession.id, { content });
      addMessage(reply);
    } catch (err) {
      // Remove the optimistic message on error
      setMessages((prevMessages) => prevMessages.filter((m) => m.id !== tempId));
      const errorMsg = err instanceof Error ? err.message : 'Failed to send message';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, sending: false }));
    }
  };

  const handleFinalize = async () => {
    if (!currentSession || loading.finalizing) return;
    try {
      setLoading((prev) => ({ ...prev, finalizing: true }));
      const evaluation = await sessionService.finalizeSession(currentSession.id);
      setEvaluation(evaluation);
      setCurrentPage('results');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to finalize session';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setLoading((prev) => ({ ...prev, finalizing: false }));
    }
  };

  const handleEndSession = async () => {
    if (!currentSession || loading.ending) return;
    try {
      setLoading((prev) => ({ ...prev, ending: true }));
      // Just clear the session and go back to dashboard
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

  const playTts = async (text: string) => {
    if (!text?.trim()) return;
    
    // Stop any current playback to prevent overlap
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    
    try {
      const response = await aiService.generateSpeech({ text });
      
      if (response.tts_provider) {
        setTtsProvider(response.tts_provider);
      }

      if (response.mode === 'audio' && response.audio_url) {
        if (!audioRef.current) {
          audioRef.current = new Audio();
          // Setup cleanup handler for blob URLs
          audioRef.current.onended = () => {
            if (audioBlobUrls.current.length > 0) {
              const oldUrl = audioBlobUrls.current.shift();
              if (oldUrl) URL.revokeObjectURL(oldUrl);
            }
          };
        }
        
        // Track blob URL for cleanup
        audioBlobUrls.current.push(response.audio_url);
        audioRef.current.src = response.audio_url;
        await audioRef.current.play();
      }
    } catch (err) {
      console.error('TTS playback error:', err);
    }
  };

  const handleReplayLast = async () => {
    const lastAiMessage = [...messages].reverse().find((m) => m.role === 'interviewer');
    if (!lastAiMessage) return;
    setLoading((prev) => ({ ...prev, replaying: true }));
    await playTts(lastAiMessage.content);
    setLoading((prev) => ({ ...prev, replaying: false }));
  };

  const startListening = () => {
    if (!recognitionRef.current || isListening) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
      setLocalError(null);
    } catch (err) {
      setLocalError('Failed to start voice recognition');
    }
  };

  const stopListening = () => {
    if (!recognitionRef.current || !isListening) return;
    recognitionRef.current.stop();
    setIsListening(false);
  };

  const copyQuestion = async () => {
    if (!question) return;
    const text = `${question.title}\n\n${question.prompt}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      setLocalError('Failed to copy question');
    }
  };

  // No active session state
  if (!currentSession) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-indigo-50 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4">
            {Icons.play}
          </div>
          <p className="text-lg font-semibold text-slate-900 dark:text-white">No Active Session</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Start a new interview from the dashboard to begin.
          </p>
        </div>
      </div>
    );
  }

  const statusColor =
    currentSession.stage === 'done'
      ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400'
      : currentSession.stage === 'intro'
        ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400'
        : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400';

  const aiStatusColor =
    aiStatus?.status === 'online'
      ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400'
      : aiStatus?.status === 'offline'
        ? 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400'
        : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';

  const aiStatusDot =
    aiStatus?.status === 'online'
      ? 'bg-emerald-500'
      : aiStatus?.status === 'offline'
        ? 'bg-red-500'
        : 'bg-slate-400';

  const lastAiMessage = [...messages].reverse().find((m) => m.role === 'interviewer');

  const containerClass = isPageExpanded
    ? 'fixed inset-0 z-50 flex flex-col bg-slate-50 dark:bg-slate-900'
    : 'flex flex-col h-[calc(100vh-8rem)] min-h-[500px] bg-slate-50 dark:bg-slate-900 -m-4 md:-m-6';

  return (
    <div className={containerClass}>
      {/* Error Toast */}
      {localError && (
        <div className="fixed top-20 right-4 z-[60] bg-red-50 dark:bg-red-900/90 border border-red-200 dark:border-red-800 rounded-xl p-3 shadow-xl max-w-xs">
          <div className="flex items-start gap-2">
            <div className="flex-shrink-0 w-4 h-4 text-red-600 dark:text-red-400 mt-0.5">{Icons.alertCircle}</div>
            <p className="text-sm text-red-900 dark:text-red-100 flex-1">{localError}</p>
            <button onClick={() => setLocalError(null)} className="text-red-600 dark:text-red-400 hover:text-red-800">{Icons.close}</button>
          </div>
        </div>
      )}

      {/* Slim Top Header Bar */}
      <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-3 py-2 flex-shrink-0">
        <div className="flex items-center justify-between gap-3">
          {/* Left: Title + Status + Timer */}
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-base font-bold text-slate-900 dark:text-white">Interview</h1>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${statusColor}`}>
              <span className="w-1.5 h-1.5 rounded-full bg-current" />
              {currentSession.stage?.toUpperCase() || 'IDLE'}
            </span>
            <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-indigo-50 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
              <div className="w-3.5 h-3.5">{Icons.clock}</div>
              <span className="font-mono font-bold text-xs">{formatTimer(elapsedSec)}</span>
            </div>
            <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <span>{currentSession.role}</span>
              <span>•</span>
              <span className="capitalize">{currentSession.difficulty}</span>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-1.5">
            {needsAudioUnlock && voiceEnabled && (
              <button
                onClick={() => { setAudioUnlocked(true); setNeedsAudioUnlock(false); if (lastAiMessage) playTts(lastAiMessage.content); }}
                className="px-2 py-1 rounded-md border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-400 text-xs hover:bg-amber-50 dark:hover:bg-amber-900/30"
              >
                Audio
              </button>
            )}
            <button
              onClick={() => setIsLeftPanelCollapsed(!isLeftPanelCollapsed)}
              className="p-1.5 rounded-md border border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700"
              title={isLeftPanelCollapsed ? 'Show panel' : 'Hide panel'}
            >
              <div className="w-4 h-4">{isLeftPanelCollapsed ? Icons.expand : Icons.collapse}</div>
            </button>
            <button
              onClick={() => setIsPageExpanded(!isPageExpanded)}
              className="p-1.5 rounded-md border border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700"
              title={isPageExpanded ? 'Exit fullscreen' : 'Fullscreen'}
            >
              <div className="w-4 h-4">{isPageExpanded ? Icons.minimize : Icons.maximize}</div>
            </button>
            <button
              onClick={handleReplayLast}
              disabled={loading.replaying || messages.length === 0}
              className="px-2 py-1 rounded-md border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
            >
              Replay
            </button>
            <button
              onClick={handleEndSession}
              disabled={loading.ending}
              className="px-2 py-1 rounded-md border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50"
            >
              End
            </button>
            <button
              onClick={handleFinalize}
              disabled={loading.finalizing || currentSession.stage === 'done'}
              className="px-3 py-1 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold disabled:opacity-50"
            >
              {loading.finalizing ? '...' : 'Submit & Evaluate'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content: Narrow Left Panel + Wide Chat */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Panel - Narrow (Question + Guide) */}
        {!isLeftPanelCollapsed && (
          <div className="w-56 xl:w-64 flex-shrink-0 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col overflow-hidden">
            {/* Question Section */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              <div>
                <h3 className="text-xs font-semibold text-slate-900 dark:text-white mb-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                  Question
                </h3>
                {question ? (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-slate-900 dark:text-white leading-snug">{question.title}</p>
                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-wrap bg-slate-50 dark:bg-slate-900/50 rounded p-2 border border-slate-100 dark:border-slate-700 max-h-40 overflow-y-auto">
                      {question.prompt}
                    </p>
                    {question.tags && question.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {question.tags.slice(0, 3).map((tag) => (
                          <span key={tag} className="px-1.5 py-0.5 rounded bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 text-[10px]">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 dark:text-slate-400 italic">Waiting for question...</p>
                )}
              </div>

              {/* Answer Guide - Compact */}
              <div>
                <h4 className="text-xs font-semibold text-slate-900 dark:text-white mb-2">Approach</h4>
                <div className="space-y-1">
                  {[
                    { n: 1, t: 'Plan', d: 'Clarify' },
                    { n: 2, t: 'Solve', d: 'Approach' },
                    { n: 3, t: 'Optimize', d: 'Tradeoffs' },
                    { n: 4, t: 'Validate', d: 'Edge cases' },
                  ].map((s) => (
                    <div key={s.n} className="flex items-center gap-2 p-1.5 rounded bg-slate-50 dark:bg-slate-700/50 border border-slate-100 dark:border-slate-600">
                      <div className="w-4 h-4 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">{s.n}</div>
                      <span className="text-[11px] text-slate-700 dark:text-slate-300"><span className="font-medium">{s.t}</span> - {s.d}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Voice Status - Bottom of left panel */}
            <div className="p-2 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80">
              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                  voiceEnabled
                    ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${voiceEnabled ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                Voice {voiceEnabled ? 'On' : 'Off'}
              </button>
            </div>
          </div>
        )}

        {/* Chat Panel - Takes remaining space */}
        <div className="flex-1 flex flex-col min-w-0 bg-slate-50 dark:bg-slate-900">
          {/* AI Status Bar */}
          <div className="px-3 py-1.5 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400">Conversation</span>
            <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${aiStatusColor}`}>
              <span className={`w-1 h-1 rounded-full ${aiStatusDot}`} />
              {aiStatus?.status === 'online' ? 'Online' : aiStatus?.status === 'offline' ? 'Offline' : '...'}
            </div>
          </div>

          {/* Messages Area - Maximum space */}
          <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3">
            {loading.messages ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-6 h-6 rounded-full border-2 border-indigo-200 dark:border-indigo-800 border-t-indigo-600 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-500 dark:text-slate-400">Loading...</p>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto mb-2">
                    {Icons.messageCircle}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Waiting for interviewer...</p>
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg: Message) => (
                  <div key={msg.id} className={`flex ${msg.role === 'student' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[85%] lg:max-w-[75%] rounded-2xl px-3 py-2 ${
                        msg.role === 'student'
                          ? 'bg-indigo-600 text-white rounded-br-sm'
                          : 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-700 rounded-bl-sm'
                      }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                        {msg.role === 'interviewer' ? sanitizeAiText(msg.content) : msg.content}
                      </p>
                      {msg.created_at && (
                        <p className={`text-[10px] mt-1.5 ${msg.role === 'student' ? 'text-indigo-200' : 'text-slate-400 dark:text-slate-500'}`}>
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                {loading.sending && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] lg:max-w-[75%] rounded-2xl px-3 py-2 bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 rounded-bl-sm">
                      <p className="text-sm leading-relaxed italic">Thinking...</p>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </>
            )}
          </div>

          {/* Compact Input Area */}
          <div className="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 md:p-3">
            <form onSubmit={handleSendMessage} className="flex flex-col gap-2">
              {/* Mode tabs + Input in one row for text mode */}
              <div className="flex items-end gap-2">
                {/* Mode Tabs - Vertical on left */}
                <div className="flex flex-col gap-1">
                  {(['text', 'code', 'voice'] as InputMode[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => {
                        // Clear voice mode data when switching away
                        if (inputMode === 'voice' && mode !== 'voice') {
                          setVoiceText('');
                          setVoiceInterim('');
                          if (isListening) {
                            recognitionRef.current?.stop();
                          }
                        }
                        setInputMode(mode);
                      }}
                      disabled={loading.sending || currentSession.stage === 'done' || (mode === 'voice' && !voiceSupported)}
                      className={`p-1.5 rounded transition-all ${
                        inputMode === mode
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50'
                      }`}
                      title={mode}
                    >
                      <div className="w-4 h-4">
                        {mode === 'text' && Icons.pencil}
                        {mode === 'code' && Icons.code}
                        {mode === 'voice' && Icons.microphone}
                      </div>
                    </button>
                  ))}
                </div>

                {/* Input Area - Grows */}
                <div className="flex-1 min-w-0">
                  {inputMode === 'code' ? (
                    <textarea
                      ref={textareaRef}
                      value={codeText}
                      onChange={(e) => setCodeText(e.target.value)}
                      disabled={loading.sending || currentSession.stage === 'done'}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 resize-none"
                      placeholder="Code..."
                      style={{ minHeight: '40px', maxHeight: '120px' }}
                    />
                  ) : inputMode === 'voice' ? (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={isListening ? stopListening : startListening}
                        disabled={!voiceSupported || currentSession.stage === 'done' || loading.sending}
                        className={`px-3 py-2 rounded-lg text-xs font-medium border flex items-center gap-1.5 ${
                          isListening
                            ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                            : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-600'
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${isListening ? 'bg-red-500 animate-pulse' : 'bg-slate-400'}`} />
                        {isListening ? 'Stop' : 'Record'}
                      </button>
                      <input
                        type="text"
                        value={voiceText}
                        onChange={(e) => setVoiceText(e.target.value)}
                        className="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder={voiceInterim || 'Speak or type...'}
                      />
                    </div>
                  ) : (
                    <textarea
                      ref={textareaRef}
                      value={messageText}
                      onChange={(e) => setMessageText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      disabled={loading.sending || currentSession.stage === 'done'}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 resize-none"
                      placeholder="Type your response... (Enter to send)"
                      style={{ minHeight: '40px', maxHeight: '120px' }}
                    />
                  )}
                </div>

                {/* Send Button */}
                <button
                  type="submit"
                  disabled={
                    loading.sending ||
                    currentSession.stage === 'done' ||
                    (inputMode === 'code' ? !codeText.trim() : inputMode === 'voice' ? !buildVoiceDraft() : !messageText.trim())
                  }
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold disabled:opacity-50 shadow-sm transition-all flex items-center gap-1.5 h-[40px]"
                >
                  {loading.sending ? (
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  ) : (
                    <>
                      Send
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
