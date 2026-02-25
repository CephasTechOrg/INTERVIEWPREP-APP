'use client';

import { useEffect, useState } from 'react';
import { sessionService } from '@/lib/services/sessionService';
import { SessionSummary } from '@/types/api';
import { Icons } from '@/components/ui/Icons';

type ScoreBand = 'excellent' | 'good' | 'average' | 'needsWork';

interface PerformanceStats {
  totalSessions: number;
  completedSessions: number;
  avgScore: number;
  bestScore: number;
  medianScore: number;
  streak: number;
  completionRate: number;
}

export const PerformanceSection = () => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<PerformanceStats>({
    totalSessions: 0,
    completedSessions: 0,
    avgScore: 0,
    bestScore: 0,
    medianScore: 0,
    streak: 0,
    completionRate: 0,
  });

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    calculateStats();
  }, [sessions]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const result = await sessionService.listSessions();
      setSessions(result);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = () => {
    const completed = sessions.filter((s) => s.stage === 'done');
    // Use actual scores from API (filter out null/undefined/0)
    const scores = completed
      .map((s) => s.overall_score)
      .filter((s): s is number => typeof s === 'number' && s > 0)
      .sort((a, b) => b - a);

    const avgScore = scores.length 
      ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) 
      : 0;
    const bestScore = scores.length ? Math.max(...scores) : 0;
    const medianScore = scores.length 
      ? scores[Math.floor(scores.length / 2)] 
      : 0;
    const completionRate = sessions.length 
      ? Math.round((completed.length / sessions.length) * 100) 
      : 0;

    // Calculate actual streak
    const sortedDates = completed
      .map(s => s.created_at ? new Date(s.created_at).toDateString() : null)
      .filter((d): d is string => d !== null)
      .filter((v, i, a) => a.indexOf(v) === i)
      .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
    
    let streak = 0;
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    if (sortedDates.includes(today) || sortedDates.includes(yesterday)) {
      streak = 1;
      for (let i = 1; i < sortedDates.length; i++) {
        const curr = new Date(sortedDates[i - 1]).getTime();
        const prev = new Date(sortedDates[i]).getTime();
        const diffDays = Math.round((curr - prev) / 86400000);
        if (diffDays === 1) {
          streak++;
        } else {
          break;
        }
      }
    }

    setStats({
      totalSessions: sessions.length,
      completedSessions: completed.length,
      avgScore,
      bestScore,
      medianScore,
      streak,
      completionRate,
    });
  };

  const completed = sessions.filter((s) => s.stage === 'done');
  
  // Use actual scores from completed sessions
  const recentScores = completed.slice(0, 10).map((s) => ({
    score: s.overall_score ?? 0,
    date: s.created_at ? new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
  })).filter(s => s.score > 0).reverse();

  // By difficulty
  const byDifficulty = {
    easy: sessions.filter(s => s.difficulty === 'easy').length,
    medium: sessions.filter(s => s.difficulty === 'medium').length,
    hard: sessions.filter(s => s.difficulty === 'hard').length,
  };
  const difficultyTotal = byDifficulty.easy + byDifficulty.medium + byDifficulty.hard || 1;

  // By track - use actual scores
  const byTrack: Record<string, { count: number; avgScore: number; totalScore: number }> = {};
  completed.forEach((s) => {
    const key = s.track || 'unknown';
    if (!byTrack[key]) {
      byTrack[key] = { count: 0, avgScore: 0, totalScore: 0 };
    }
    const score = s.overall_score ?? 0;
    if (score > 0) {
      byTrack[key].count += 1;
      byTrack[key].totalScore += score;
    }
  });
  Object.keys(byTrack).forEach((key) => {
    if (byTrack[key].count > 0) {
      byTrack[key].avgScore = Math.round(byTrack[key].totalScore / byTrack[key].count);
    }
  });

  // Score bands
  const getScoreBand = (score: number): ScoreBand => {
    if (score >= 90) return 'excellent';
    if (score >= 75) return 'good';
    if (score >= 60) return 'average';
    return 'needsWork';
  };

  const scoreBandColors: Record<ScoreBand, string> = {
    excellent: 'bg-green-500',
    good: 'bg-blue-500',
    average: 'bg-amber-500',
    needsWork: 'bg-red-500',
  };

  const scoreBandLabels: Record<ScoreBand, string> = {
    excellent: 'Excellent (90+)',
    good: 'Good (75-89)',
    average: 'Average (60-74)',
    needsWork: 'Needs Work (<60)',
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Performance Analytics</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm font-medium mt-1">Track your interview progress and identify areas for improvement</p>
        </div>
        <button
          onClick={loadSessions}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg font-medium transition-colors disabled:opacity-50 w-fit"
        >
          <span className={loading ? 'animate-spin' : ''}>{Icons.refresh}</span>
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-8 text-center transition-colors">
          <div className="text-slate-400 mb-2">{Icons.spinner}</div>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Loading performance data...</p>
        </div>
      ) : (
        <>
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 transition-all hover:shadow-md">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400 mb-2">
                {Icons.play}
              </div>
              <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.totalSessions}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Total Sessions</div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 transition-all hover:shadow-md">
              <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-2">
                {Icons.checkCircle}
              </div>
              <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.completedSessions}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Completed</div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 transition-all hover:shadow-md">
              <div className="w-8 h-8 bg-violet-100 dark:bg-violet-900/50 rounded-lg flex items-center justify-center text-violet-600 dark:text-violet-400 mb-2">
                {Icons.chart}
              </div>
              <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.avgScore || '-'}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Avg Score</div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 transition-all hover:shadow-md">
              <div className="w-8 h-8 bg-amber-100 dark:bg-amber-900/50 rounded-lg flex items-center justify-center text-amber-600 dark:text-amber-400 mb-2">
                {Icons.trophy}
              </div>
              <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.bestScore || '-'}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Best Score</div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 transition-all hover:shadow-md">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400 mb-2">
                {Icons.results}
              </div>
              <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.medianScore || '-'}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Median Score</div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 transition-all hover:shadow-md">
              <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900/50 rounded-lg flex items-center justify-center text-orange-600 dark:text-orange-400 mb-2">
                {Icons.fire}
              </div>
              <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.streak}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Day Streak</div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Score Trend Chart */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-colors">
              <div className="mb-8">
                <h3 className="font-bold text-lg text-slate-900 dark:text-white">Score Trend</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Your recent interview scores</p>
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

            {/* Difficulty Breakdown */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
              <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-8">Difficulty Breakdown</h3>
              <div className="space-y-6 flex-1">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400 font-medium">Easy</span>
                    <span className="font-bold text-slate-900 dark:text-white">{byDifficulty.easy}</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-500 rounded-full transition-all"
                      style={{ width: `${(byDifficulty.easy / difficultyTotal) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400 font-medium">Medium</span>
                    <span className="font-bold text-slate-900 dark:text-white">{byDifficulty.medium}</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-amber-500 rounded-full transition-all"
                      style={{ width: `${(byDifficulty.medium / difficultyTotal) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400 font-medium">Hard</span>
                    <span className="font-bold text-slate-900 dark:text-white">{byDifficulty.hard}</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-rose-500 rounded-full transition-all"
                      style={{ width: `${(byDifficulty.hard / difficultyTotal) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="mt-8 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-xs text-slate-500 dark:text-slate-400">
                Focus on <span className="text-rose-500 font-bold">Hard</span> level questions to reach your target score.
              </div>
            </div>

            {/* Performance by Track */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-6">Performance by Track</h3>
              <div className="space-y-4">
                {Object.entries(byTrack).length > 0 ? (
                  Object.entries(byTrack).map(([track, data]) => (
                    <div key={track} className="flex items-center gap-4">
                      <div className="size-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-blue-400">
                        📈
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-sm font-semibold text-slate-900 dark:text-white capitalize">{track.replace(/_/g, ' ')}</span>
                          <span className="text-sm text-slate-600 dark:text-slate-400">{data.avgScore}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-blue-500 rounded-full transition-all"
                            style={{ width: `${data.avgScore}%` }}
                          />
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{data.count} sessions</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-slate-400 py-6">
                    <p className="text-sm">Complete interviews to see track performance</p>
                  </div>
                )}
              </div>
            </div>

            {/* Score Distribution */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-6">Score Distribution</h3>
              <div className="space-y-3">
                {(['excellent', 'good', 'average', 'needsWork'] as ScoreBand[]).map((band) => {
                  const scores = completed.map(s => s.overall_score ?? 80);
                  const count = scores.filter(s => getScoreBand(s) === band).length;
                  const percentage = completed.length ? Math.round((count / completed.length) * 100) : 0;
                    
                    return (
                      <div key={band} className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${scoreBandColors[band]}`} />
                        <span className="flex-1 text-sm text-slate-700 dark:text-slate-300">{scoreBandLabels[band]}</span>
                        <span className="text-sm font-medium text-slate-900 dark:text-white">{count}</span>
                        <span className="text-xs text-slate-500 dark:text-slate-400 w-10 text-right">{percentage}%</span>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>

          {/* Session Completion CTA */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl p-8 text-white relative overflow-hidden">
            {/* Background Accent */}
            <div className="absolute -right-12 -bottom-12 size-64 bg-white/10 rounded-full blur-3xl"></div>
            <div className="flex flex-col md:flex-row items-center gap-8 relative z-10">
              <div className="flex-1 space-y-4 text-center md:text-left">
                <h3 className="text-2xl font-bold">You're on track to your goal!</h3>
                <p className="text-blue-100 opacity-90 max-w-lg">Keep practicing consistently to improve your scores and master technical interviews.</p>
                <div className="flex items-center gap-2 text-sm font-medium">
                  <span>Completion Rate:</span>
                  <span className="text-xl font-bold">{stats.completionRate}%</span>
                </div>
              </div>
              <div className="w-full md:w-48 space-y-3">
                <div className="flex justify-between text-sm font-bold">
                  <span>Progress</span>
                  <span>{stats.completedSessions}/{stats.totalSessions}</span>
                </div>
                <div className="w-full h-3 bg-white/20 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-white rounded-full transition-all"
                    style={{ width: `${stats.completionRate}%` }}
                  />
                </div>
                <p className="text-[11px] font-medium opacity-70 text-center">{stats.completedSessions} sessions completed</p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
