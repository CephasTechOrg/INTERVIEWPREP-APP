'use client';

import { useEffect, useMemo } from 'react';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { analyticsService } from '@/lib/services/analyticsService';

// Score ring component with animated progress
const ScoreRing = ({ score, size = 160 }: { score: number | null; size?: number }) => {
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const actualScore = score ?? 0;
  const offset = circumference - (actualScore / 100) * circumference;
  
  const getScoreColor = (s: number) => {
    if (s >= 80) return { stroke: '#10b981', text: 'text-emerald-500' };
    if (s >= 60) return { stroke: '#3b82f6', text: 'text-blue-500' };
    if (s >= 40) return { stroke: '#f59e0b', text: 'text-amber-500' };
    return { stroke: '#ef4444', text: 'text-red-500' };
  };
  
  const colors = getScoreColor(actualScore);

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-slate-200 dark:text-slate-700"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={score !== null ? colors.stroke : 'transparent'}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={score !== null ? offset : circumference}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-4xl font-bold ${score !== null ? colors.text : 'text-slate-400 dark:text-slate-500'}`}>
          {score !== null ? score : '--'}
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-400 mt-1">out of 100</span>
      </div>
    </div>
  );
};

// Icon components
const CheckCircleIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const AlertCircleIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ArrowRightIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
  </svg>
);

const TrophyIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 3.75h3.75v3.75m0-3.75L15 9m5.25 9.75h-3.75v-3.75m3.75 3.75L15 15M7.5 3.75H3.75v3.75m0-3.75L9 9m-5.25 9.75h3.75v-3.75m-3.75 3.75L9 15" />
  </svg>
);

const ChartIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

// Rubric category progress bar
const RubricBar = ({ label, score, maxScore = 10 }: { label: string; score: number; maxScore?: number }) => {
  const percentage = (score / maxScore) * 100;
  const getBarColor = (p: number) => {
    if (p >= 80) return 'bg-emerald-500';
    if (p >= 60) return 'bg-blue-500';
    if (p >= 40) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">
          {label.replace(/_/g, ' ')}
        </span>
        <span className="text-sm font-semibold text-slate-900 dark:text-white">
          {score}/{maxScore}
        </span>
      </div>
      <div className="h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${getBarColor(percentage)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

export const ResultsSection = () => {
  const { currentSession, evaluation, setEvaluation, setLoading, setError } = useSessionStore();

  useEffect(() => {
    if (currentSession) {
      loadEvaluation();
    }
  }, [currentSession?.id]);

  const loadEvaluation = async () => {
    if (!currentSession) return;
    try {
      setLoading(true);
      const evalData = await analyticsService.getSessionResults(currentSession.id);
      setEvaluation(evalData);
    } catch (err) {
      setError('Failed to load evaluation');
    } finally {
      setLoading(false);
    }
  };

  // Parse rubric data for display
  const rubricItems = useMemo(() => {
    if (!evaluation?.rubric) return [];
    return Object.entries(evaluation.rubric)
      .filter(([key]) => !key.startsWith('_') && key !== 'comments')
      .map(([key, value]) => ({
        label: key,
        score: typeof value === 'number' ? value : (value as { score?: number })?.score ?? 0,
      }));
  }, [evaluation?.rubric]);

  const getPerformanceLabel = (score: number | null) => {
    if (score === null) return { label: 'Pending', color: 'text-slate-500' };
    if (score >= 80) return { label: 'Excellent', color: 'text-emerald-500' };
    if (score >= 60) return { label: 'Good', color: 'text-blue-500' };
    if (score >= 40) return { label: 'Needs Improvement', color: 'text-amber-500' };
    return { label: 'Keep Practicing', color: 'text-red-500' };
  };

  const performance = getPerformanceLabel(evaluation?.overall_score ?? null);

  return (
    <div className="min-h-full bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header Card with Score */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg">
                <TrophyIcon />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Interview Results</h1>
                <p className="text-indigo-100 text-sm">
                  {currentSession ? `Session #${currentSession.id}` : 'Review your performance'}
                </p>
              </div>
            </div>
          </div>
          
          <div className="p-6">
            <div className="flex flex-col md:flex-row items-center gap-8">
              {/* Score Ring */}
              <div className="flex-shrink-0">
                <ScoreRing score={evaluation?.overall_score ?? null} />
              </div>
              
              {/* Performance Summary */}
              <div className="flex-1 text-center md:text-left">
                <h2 className={`text-2xl font-bold ${performance.color}`}>
                  {performance.label}
                </h2>
                <p className="text-slate-600 dark:text-slate-400 mt-2">
                  {evaluation 
                    ? 'Your interview has been evaluated. Review the detailed feedback below to improve your skills.'
                    : 'Complete an interview session to see your personalized results and feedback here.'}
                </p>
                
                {currentSession && (
                  <div className="flex flex-wrap gap-2 mt-4 justify-center md:justify-start">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
                      {currentSession.track.replace(/_/g, ' ')}
                    </span>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300">
                      {currentSession.company_style}
                    </span>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300 capitalize">
                      {currentSession.difficulty}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Feedback Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Strengths Card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border-t-4 border-emerald-500">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg text-emerald-600 dark:text-emerald-400">
                <CheckCircleIcon />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Strengths</h3>
            </div>
            {evaluation?.summary?.strengths?.length ? (
              <ul className="space-y-3">
                {evaluation.summary.strengths.map((item, idx) => (
                  <li key={`strength-${idx}`} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400 italic">
                Complete an interview to see your strengths.
              </p>
            )}
          </div>

          {/* Weaknesses Card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border-t-4 border-amber-500">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg text-amber-600 dark:text-amber-400">
                <AlertCircleIcon />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Areas to Improve</h3>
            </div>
            {evaluation?.summary?.weaknesses?.length ? (
              <ul className="space-y-3">
                {evaluation.summary.weaknesses.map((item, idx) => (
                  <li key={`weakness-${idx}`} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-2 flex-shrink-0" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400 italic">
                Areas for improvement will appear here.
              </p>
            )}
          </div>

          {/* Next Steps Card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border-t-4 border-blue-500">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                <ArrowRightIcon />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Next Steps</h3>
            </div>
            {evaluation?.summary?.next_steps?.length ? (
              <ul className="space-y-3">
                {evaluation.summary.next_steps.map((item, idx) => (
                  <li key={`next-${idx}`} className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xs font-semibold">
                      {idx + 1}
                    </span>
                    <span className="text-sm text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400 italic">
                Recommended next steps will appear here.
              </p>
            )}
          </div>
        </div>

        {/* Rubric Breakdown */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg text-indigo-600 dark:text-indigo-400">
              <ChartIcon />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Rubric Breakdown</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">Detailed scoring by category</p>
            </div>
          </div>
          
          {rubricItems.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
              {rubricItems.map((item) => (
                <RubricBar key={item.label} label={item.label} score={item.score} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                <ChartIcon />
              </div>
              <p className="text-slate-500 dark:text-slate-400">
                Rubric details will appear after your interview is evaluated.
              </p>
            </div>
          )}
        </div>

        {/* Tips Section */}
        {!evaluation && (
          <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-2xl p-6 border border-indigo-100 dark:border-indigo-800">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">
              💡 Interview Tips
            </h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-700 dark:text-slate-300">
              <li className="flex items-start gap-2">
                <span className="text-indigo-500">•</span>
                Think out loud to show your problem-solving process
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500">•</span>
                Ask clarifying questions before diving in
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500">•</span>
                Consider edge cases and error handling
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500">•</span>
                Discuss time and space complexity
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
