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

export const ChartsSection = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const sessions: SessionSummary[] = await sessionService.listSessions();

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

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Analytics Dashboard</h2>
        <p className="text-slate-600 dark:text-slate-400">Track your interview progress and performance trends.</p>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-8 text-center text-slate-500 dark:text-slate-400 transition-colors">Loading...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Total Sessions</p>
              <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">{data?.total_sessions ?? 0}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Completed Sessions</p>
              <p className="text-3xl font-bold text-green-600 dark:text-green-400">{data?.completed_sessions ?? 0}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Avg Score</p>
              <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{data?.average_score ?? 0}</p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 transition-colors">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Performance by Track</h3>
            <div className="space-y-3">
              {data && Object.entries(data.performance_by_track).length > 0 ? (
                Object.entries(data.performance_by_track).map(([track, stats]) => (
                  <div key={track} className="flex items-center justify-between">
                    <span className="capitalize text-slate-700 dark:text-slate-300">{track.replace(/_/g, ' ')}</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {stats.average_score} ({stats.count} sessions)
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-slate-500 dark:text-slate-400">No performance data yet.</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
