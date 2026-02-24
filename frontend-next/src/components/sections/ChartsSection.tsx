'use client';

import { useEffect, useState } from 'react';
import { sessionService } from '@/lib/services/sessionService';
import { SessionSummary } from '@/types/api';

interface AnalyticsData {
  total_sessions: number;
  completed_sessions: number;
  average_score: number;
  performance_by_track: Record<string, { average_score: number; count: number }>;
}

type ScoreBand = 'excellent' | 'good' | 'average' | 'needsWork';

export const ChartsSection = () => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const sessions: SessionSummary[] = await sessionService.listSessions();
      setSessions(sessions);

      const total = sessions.length;
      const completed = sessions.filter((s) => s.stage === 'done');
      const scores = completed.map((s) => s.overall_score).filter((s): s is number => typeof s === 'number');
      const average = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;

      const byTrack: Record<string, { average_score: number; count: number }> = {};
      completed.forEach((s) => {
        const key = s.track;
        if (!byTrack[key]) {
          byTrack[key] = { average_score: 0, count: 0 };
        }
        if (typeof s.overall_score === 'number') {
          byTrack[key].average_score += s.overall_score;
          byTrack[key].count += 1;
        }
      });

      Object.keys(byTrack).forEach((key) => {
        if (byTrack[key].count > 0) {
          byTrack[key].average_score = Math.round(byTrack[key].average_score / byTrack[key].count);
        }
      });

      setData({
        total_sessions: total,
        completed_sessions: completed.length,
        average_score: average,
        performance_by_track: byTrack,
      });
    } catch (err) {
      console.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const completed = sessions.filter((s) => s.stage === 'done');
  
  // Use actual scores from completed sessions
  const recentScores = completed.slice(0, 10).map((s) => ({
    score: s.overall_score ?? 0,
    date: s.created_at ? new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
  })).filter(s => s.score > 0).reverse();

  const getScoreBand = (score: number): ScoreBand => {
    if (score >= 90) return 'excellent';
    if (score >= 75) return 'good';
    if (score >= 60) return 'average';
    return 'needsWork';
  };

  const scoreBandColors: Record<ScoreBand, string> = {
    excellent: 'bg-green-500',
    good: 'bg-indigo-500',
    average: 'bg-amber-500',
    needsWork: 'bg-red-500',
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Performance Analytics</h2>
        <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">In-depth insights into your interview journey and AI-powered skill evaluation.</p>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-12 text-center">
          <p className="text-slate-500 dark:text-slate-400">Loading analytics data...</p>
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center justify-between mb-4">
                <span className="p-2 bg-indigo-500/5 rounded-lg text-indigo-600 dark:text-indigo-400 text-2xl">📊</span>
                <span className="text-xs font-bold text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded">Live</span>
              </div>
              <p className="text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Total Sessions</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-50">{data?.total_sessions ?? 0}</p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center justify-between mb-4">
                <span className="p-2 bg-emerald-500/5 rounded-lg text-emerald-600 dark:text-emerald-400 text-2xl">✅</span>
                <span className="text-xs font-bold text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded">+{Math.round((data?.completed_sessions ?? 0) / Math.max(data?.total_sessions ?? 1, 1) * 100)}%</span>
              </div>
              <p className="text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Completed</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-50">{data?.completed_sessions ?? 0}</p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center justify-between mb-4">
                <span className="p-2 bg-purple-500/5 rounded-lg text-purple-600 dark:text-purple-400 text-2xl">🎯</span>
                <span className="text-xs font-bold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 px-2 py-1 rounded">Score</span>
              </div>
              <p className="text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Avg Score</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-50">{data?.average_score ?? 0}%</p>
            </div>
          </div>

          {/* Main Analytics Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Score Trend - Takes 2 columns */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="font-bold text-lg text-slate-900 dark:text-white">Score Trend</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Your recent interview scores</p>
                </div>
              </div>
              {recentScores.length > 0 ? (
                <div className="h-64 flex items-end justify-between gap-3 pb-4">
                  {recentScores.map((item, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                      <div className="w-full h-full relative">
                        <div 
                          className={`w-full rounded-t-lg ${scoreBandColors[getScoreBand(item.score)]} transition-all group-hover:shadow-lg relative`}
                          style={{ height: `${item.score}%` }}
                          title={`${item.score}%`}
                        >
                          <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-900 dark:bg-slate-700 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                            {item.score}%
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap mt-2">{item.date}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-slate-400">
                  <p className="text-sm">No score data yet</p>
                </div>
              )}
            </div>

            {/* Performance by Track */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
              <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-6">Performance by Track</h3>
              <div className="space-y-5 flex-1">
                {data && Object.entries(data.performance_by_track).length > 0 ? (
                  Object.entries(data.performance_by_track).map(([track, stats]) => (
                    <div key={track}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{track.replace(/_/g, ' ')}</span>
                        <span className="text-sm font-bold text-slate-900 dark:text-white">{stats.average_score}%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-indigo-500 dark:bg-indigo-400 rounded-full transition-all"
                          style={{ width: `${stats.average_score}%` }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{stats.count} sessions</p>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-500 dark:text-slate-400 text-sm">No performance data yet.</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
