'use client';

import { useEffect, useState } from 'react';
import { sessionService } from '@/lib/services/sessionService';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { Message, SessionSummary } from '@/types/api';
import { Icons } from '@/components/ui/Icons';

// ── Transcript Modal ───────────────────────────────────────────────────────────
function TranscriptModal({
  session,
  onClose,
}: {
  session: SessionSummary;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    sessionService.getMessages(session.id)
      .then(setMessages)
      .finally(() => setLoading(false));
  }, [session.id]);

  const handleDownload = () => {
    const lines = messages.map((m) => {
      const speaker = m.role === 'user' ? 'You' : 'Interviewer';
      const time = m.created_at ? new Date(m.created_at).toLocaleTimeString() : '';
      return `[${speaker}${time ? ' · ' + time : ''}]\n${m.content}`;
    });
    const text = [
      `Interview Transcript`,
      `Track: ${session.track?.replace(/_/g, ' ')} | Difficulty: ${session.difficulty} | Company: ${session.company_style}`,
      `Date: ${session.created_at ? new Date(session.created_at).toLocaleDateString() : ''}`,
      '─'.repeat(60),
      '',
      ...lines.map(l => l + '\n'),
    ].join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `interview-transcript-${session.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col border border-slate-200 dark:border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-white capitalize">
              {session.track?.replace(/_/g, ' ')} — Transcript
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {session.created_at ? new Date(session.created_at).toLocaleDateString() : ''} · {session.difficulty} · {session.company_style}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg transition-colors"
              >
                {Icons.download}
                Download
              </button>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {Icons.close}
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-slate-400">
              <span className="animate-spin mr-2">{Icons.spinner}</span>
              Loading transcript...
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <p>No messages found for this session.</p>
            </div>
          ) : (
            messages
              .filter(m => m.role !== 'system')
              .map((m) => {
                const isUser = m.role === 'user';
                return (
                  <div key={m.id} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                    <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold text-white ${
                      isUser ? 'bg-blue-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                    }`}>
                      {isUser ? 'Y' : 'I'}
                    </div>
                    <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                      <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-br-sm'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white rounded-bl-sm'
                      }`}>
                        {m.content}
                      </div>
                      {m.created_at && (
                        <span className="text-[10px] text-slate-400 px-1">
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
          )}
        </div>
      </div>
    </div>
  );
}

export const HistorySection = () => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [transcriptSession, setTranscriptSession] = useState<SessionSummary | null>(null);
  const { setCurrentSession, currentSession, clearSession } = useSessionStore();
  const { setCurrentPage } = useUIStore();

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      const result = await sessionService.listSessions();
      setSessions(result);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    const confirmed = window.confirm('Delete this session? This cannot be undone.');
    if (!confirmed) return;

    try {
      setDeletingId(sessionId);
      await sessionService.deleteSession(sessionId);
      setSessions((prev) => prev.filter((session) => session.id !== sessionId));
      if (currentSession?.id === sessionId) {
        clearSession();
      }
    } catch {
      // ignore
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusColor = (stage: string) => {
    switch (stage) {
      case 'done': return 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400';
      case 'warmup': return 'bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-400';
      case 'main': return 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-400';
      case 'behavioral': return 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400';
      default: return 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300';
    }
  };

  const getStatusLabel = (stage: string) => {
    switch (stage) {
      case 'done': return 'Completed';
      case 'warmup': return 'Warmup';
      case 'main': return 'In Progress';
      case 'behavioral': return 'Behavioral';
      default: return stage;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Session History</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Resume any session or view your results</p>
        </div>
        <button
          onClick={loadSessions}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          <span className={isLoading ? 'animate-spin' : ''}>{Icons.refresh}</span>
          Refresh
        </button>
      </div>

      {/* Session List */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="text-slate-400 mb-2">{Icons.spinner}</div>
            <p className="text-slate-500 dark:text-slate-400 text-sm">Loading sessions...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mx-auto mb-4 text-slate-400">
              {Icons.history}
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">No sessions yet</h3>
            <p className="text-slate-500 dark:text-slate-400 text-sm mb-4">
              Start your first interview from the dashboard
            </p>
            <button
              onClick={() => setCurrentPage('dashboard')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors"
            >
              {Icons.play}
              Start Interview
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {sessions.map((session) => (
              <div
                key={session.id}
                className="p-5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  {/* Session Info */}
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      session.stage === 'done' 
                        ? 'bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400' 
                        : 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    }`}>
                      {session.stage === 'done' ? Icons.checkCircle : Icons.play}
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white capitalize">
                        {session.track?.replace(/_/g, ' ') || 'Interview Session'}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="text-sm text-slate-500 dark:text-slate-400 capitalize">
                          {session.difficulty}
                        </span>
                        <span className="text-slate-300 dark:text-slate-600">•</span>
                        <span className="text-sm text-slate-500 dark:text-slate-400">
                          {session.company_style || 'General'}
                        </span>
                        <span className="text-slate-300 dark:text-slate-600">•</span>
                        <span className="text-sm text-slate-400">
                          {session.created_at 
                            ? new Date(session.created_at as string).toLocaleDateString()
                            : ''}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Status & Actions */}
                  <div className="flex items-center gap-3 sm:gap-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(session.stage)}`}>
                      {getStatusLabel(session.stage)}
                    </span>
                    
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDeleteSession(session.id)}
                        disabled={deletingId === session.id}
                        className="inline-flex items-center gap-1.5 px-3 py-2 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 text-sm rounded-lg font-medium transition-colors disabled:opacity-50"
                        title="Delete session"
                      >
                        {Icons.trash}
                        {deletingId === session.id ? 'Deleting...' : 'Delete'}
                      </button>
                      {session.stage !== 'done' && (
                        <button
                          onClick={() => {
                            setCurrentSession(session as any);
                            setCurrentPage('interview');
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg font-medium transition-colors"
                        >
                          {Icons.play}
                          Resume
                        </button>
                      )}
                      {session.stage === 'done' && (
                        <button
                          onClick={() => setTranscriptSession(session)}
                          className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm rounded-lg font-medium transition-colors"
                        >
                          {Icons.fileText}
                          Transcript
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setCurrentSession(session as any);
                          setCurrentPage('results');
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg font-medium transition-colors"
                      >
                        {Icons.results}
                        Results
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary Stats */}
      {sessions.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 transition-colors">
            <div className="text-2xl font-bold text-slate-900 dark:text-white">{sessions.length}</div>
            <div className="text-sm text-slate-500 dark:text-slate-400">Total Sessions</div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 transition-colors">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {sessions.filter(s => s.stage === 'done').length}
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">Completed</div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 transition-colors">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {sessions.filter(s => s.stage !== 'done').length}
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">In Progress</div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 transition-colors">
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {Math.round((sessions.filter(s => s.stage === 'done').length / sessions.length) * 100) || 0}%
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">Completion Rate</div>
          </div>
        </div>
      )}

      {/* Transcript Modal */}
      {transcriptSession && (
        <TranscriptModal
          session={transcriptSession}
          onClose={() => setTranscriptSession(null)}
        />
      )}
    </div>
  );
};
