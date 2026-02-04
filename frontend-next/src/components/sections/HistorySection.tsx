'use client';

import { useEffect, useState } from 'react';
import { sessionService } from '@/lib/services/sessionService';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { SessionSummary } from '@/types/api';
import { Icons } from '@/components/ui/Icons';

export const HistorySection = () => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
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
      case 'done': return 'bg-green-100 text-green-700';
      case 'warmup': return 'bg-purple-100 text-purple-700';
      case 'main': return 'bg-blue-100 text-blue-700';
      case 'behavioral': return 'bg-amber-100 text-amber-700';
      default: return 'bg-gray-100 text-gray-700';
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
          <h1 className="text-2xl font-bold text-gray-900">Session History</h1>
          <p className="text-gray-500 mt-1">Resume any session or view your results</p>
        </div>
        <button
          onClick={loadSessions}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          <span className={isLoading ? 'animate-spin' : ''}>{Icons.refresh}</span>
          Refresh
        </button>
      </div>

      {/* Session List */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 mb-2">{Icons.spinner}</div>
            <p className="text-gray-500 text-sm">Loading sessions...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4 text-gray-400">
              {Icons.history}
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">No sessions yet</h3>
            <p className="text-gray-500 text-sm mb-4">
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
          <div className="divide-y divide-gray-100">
            {sessions.map((session) => (
              <div
                key={session.id}
                className="p-5 hover:bg-gray-50 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  {/* Session Info */}
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      session.stage === 'done' 
                        ? 'bg-green-100 text-green-600' 
                        : 'bg-blue-100 text-blue-600'
                    }`}>
                      {session.stage === 'done' ? Icons.checkCircle : Icons.play}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 capitalize">
                        {session.track?.replace(/_/g, ' ') || 'Interview Session'}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="text-sm text-gray-500 capitalize">
                          {session.difficulty}
                        </span>
                        <span className="text-gray-300">•</span>
                        <span className="text-sm text-gray-500">
                          {session.company_style || 'General'}
                        </span>
                        <span className="text-gray-300">•</span>
                        <span className="text-sm text-gray-400">
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
                        className="inline-flex items-center gap-1.5 px-3 py-2 border border-red-200 text-red-600 hover:bg-red-50 text-sm rounded-lg font-medium transition-colors disabled:opacity-50"
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
                          className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm rounded-lg font-medium transition-colors"
                        >
                          {Icons.play}
                          Resume
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
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{sessions.length}</div>
            <div className="text-sm text-gray-500">Total Sessions</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-green-600">
              {sessions.filter(s => s.stage === 'done').length}
            </div>
            <div className="text-sm text-gray-500">Completed</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-blue-600">
              {sessions.filter(s => s.stage !== 'done').length}
            </div>
            <div className="text-sm text-gray-500">In Progress</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">
              {Math.round((sessions.filter(s => s.stage === 'done').length / sessions.length) * 100) || 0}%
            </div>
            <div className="text-sm text-gray-500">Completion Rate</div>
          </div>
        </div>
      )}
    </div>
  );
};
