'use client';

import { useEffect, useMemo } from 'react';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { analyticsService } from '@/lib/services/analyticsService';

// ─── Score Ring ────────────────────────────────────────────────────────────────
const ScoreRing = ({ score, size = 160 }: { score: number | null; size?: number }) => {
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const actualScore = score ?? 0;
  const offset = circumference - (actualScore / 100) * circumference;
  const getColor = (s: number) => {
    if (s >= 80) return { stroke: '#10b981', text: 'text-emerald-500' };
    if (s >= 60) return { stroke: '#3b82f6', text: 'text-blue-500' };
    if (s >= 40) return { stroke: '#f59e0b', text: 'text-amber-500' };
    return { stroke: '#ef4444', text: 'text-red-500' };
  };
  const colors = getColor(actualScore);
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} className="text-slate-200 dark:text-slate-700" />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={score !== null ? colors.stroke : 'transparent'} strokeWidth={strokeWidth} strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={score !== null ? offset : circumference} className="transition-all duration-1000 ease-out" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-4xl font-bold ${score !== null ? colors.text : 'text-slate-400'}`}>
          {score !== null ? score : '--'}
        </span>
        <span className="text-xs text-slate-500 mt-1">/ 100</span>
      </div>
    </div>
  );
};

// ─── Hire Signal Badge ─────────────────────────────────────────────────────────
const HIRE_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  strong_yes: { label: 'Strong Hire', bg: 'bg-emerald-100 dark:bg-emerald-900/40', text: 'text-emerald-700 dark:text-emerald-300', dot: 'bg-emerald-500' },
  yes:        { label: 'Hire',        bg: 'bg-blue-100 dark:bg-blue-900/40',    text: 'text-blue-700 dark:text-blue-300',    dot: 'bg-blue-500' },
  borderline: { label: 'Borderline',  bg: 'bg-amber-100 dark:bg-amber-900/40',  text: 'text-amber-700 dark:text-amber-300',  dot: 'bg-amber-500' },
  no:         { label: 'No Hire',     bg: 'bg-red-100 dark:bg-red-900/40',      text: 'text-red-700 dark:text-red-300',      dot: 'bg-red-400' },
  strong_no:  { label: 'Strong No',   bg: 'bg-red-100 dark:bg-red-900/40',      text: 'text-red-800 dark:text-red-200',      dot: 'bg-red-600' },
};

const HireSignalBadge = ({ signal }: { signal?: string }) => {
  if (!signal) return null;
  const cfg = HIRE_CONFIG[signal] ?? HIRE_CONFIG.borderline;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
};

// ─── Rubric Bar ────────────────────────────────────────────────────────────────
const RubricBar = ({ label, score, maxScore = 10 }: { label: string; score: number; maxScore?: number }) => {
  const pct = (score / maxScore) * 100;
  const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-blue-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{label.replace(/_/g, ' ')}</span>
        <span className="text-sm font-bold text-slate-900 dark:text-white">{score}/{maxScore}</span>
      </div>
      <div className="h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

// ─── Section icons ─────────────────────────────────────────────────────────────
const CheckIcon = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
const WarnIcon  = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
const ArrowIcon = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>;
const ChartIcon = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>;
const SparkIcon = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>;
const EyeIcon  = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.964-7.178z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;

// ─── Card wrapper ──────────────────────────────────────────────────────────────
const Card = ({ children, borderColor = 'border-slate-200 dark:border-slate-700', className = '' }: { children: React.ReactNode; borderColor?: string; className?: string }) => (
  <div className={`bg-white dark:bg-slate-800 rounded-2xl border ${borderColor} shadow-sm ${className}`}>
    {children}
  </div>
);

// ─── Main component ────────────────────────────────────────────────────────────
export const ResultsSection = () => {
  const { currentSession, evaluation, setEvaluation, setLoading, setError } = useSessionStore();

  useEffect(() => {
    if (currentSession) loadEvaluation();
  }, [currentSession?.id]);

  const loadEvaluation = async () => {
    if (!currentSession) return;
    try {
      setLoading(true);
      setEvaluation(await analyticsService.getSessionResults(currentSession.id));
    } catch {
      setError('Failed to load evaluation');
    } finally {
      setLoading(false);
    }
  };

  const rubricItems = useMemo(() => {
    if (!evaluation?.rubric) return [];
    return Object.entries(evaluation.rubric)
      .filter(([k]) => !k.startsWith('_') && k !== 'comments')
      .map(([k, v]) => ({ label: k, score: typeof v === 'number' ? v : (v as any)?.score ?? 0 }));
  }, [evaluation?.rubric]);

  const perf = (() => {
    const s = evaluation?.overall_score ?? null;
    if (s === null) return { label: 'Pending',           color: 'text-slate-500 dark:text-slate-400' };
    if (s >= 80)    return { label: 'Excellent',          color: 'text-emerald-600 dark:text-emerald-400' };
    if (s >= 60)    return { label: 'Good',               color: 'text-blue-600 dark:text-blue-400' };
    if (s >= 40)    return { label: 'Needs Improvement',  color: 'text-amber-600 dark:text-amber-400' };
    return            { label: 'Keep Practicing',         color: 'text-red-600 dark:text-red-400' };
  })();

  const summary = evaluation?.summary as any;
  const narrative       = summary?.narrative       as string | undefined;
  const hireSignal      = summary?.hire_signal     as string | undefined;
  const patternsObs     = summary?.patterns_observed as string[] | undefined;
  const standoutMoments = summary?.standout_moments  as string[] | undefined;

  if (!evaluation && !currentSession) {
    return (
      <div className="min-h-full flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-5 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
            <ChartIcon />
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No Results Yet</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Complete an interview session and click Finalize to see your results here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-50 dark:bg-slate-900 p-4 md:p-6">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* ── Header: Score + Hire Signal ── */}
        <Card className="overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-6 py-4">
            <h1 className="text-xl font-bold text-white">Interview Results</h1>
            {currentSession && (
              <p className="text-blue-200 text-sm mt-0.5">
                Session #{currentSession.id} · {currentSession.track.replace(/_/g, ' ')} · {currentSession.company_style} · {currentSession.difficulty}
              </p>
            )}
          </div>
          <div className="p-6">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div className="flex-shrink-0">
                <ScoreRing score={evaluation?.overall_score ?? null} />
              </div>
              <div className="flex-1 text-center sm:text-left space-y-2">
                <div className="flex flex-wrap items-center gap-2 justify-center sm:justify-start">
                  <h2 className={`text-2xl font-bold ${perf.color}`}>{perf.label}</h2>
                  {hireSignal && <HireSignalBadge signal={hireSignal} />}
                </div>
                {narrative ? (
                  <p className="text-slate-700 dark:text-slate-300 text-[15px] leading-relaxed">{narrative}</p>
                ) : (
                  <p className="text-slate-500 dark:text-slate-400 text-sm italic">
                    {evaluation ? 'Review the detailed feedback below.' : 'Complete an interview to see your evaluation.'}
                  </p>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* ── Patterns Observed (if available) ── */}
        {patternsObs && patternsObs.length > 0 && (
          <Card borderColor="border-indigo-200 dark:border-indigo-800/60" className="p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="p-1.5 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg text-indigo-600 dark:text-indigo-400">
                <EyeIcon />
              </div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Patterns Observed Across Questions</h3>
            </div>
            <ul className="space-y-2">
              {patternsObs.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* ── Standout Moments (if available) ── */}
        {standoutMoments && standoutMoments.length > 0 && (
          <Card borderColor="border-amber-200 dark:border-amber-800/60" className="p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="p-1.5 bg-amber-100 dark:bg-amber-900/40 rounded-lg text-amber-600 dark:text-amber-400">
                <SparkIcon />
              </div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Standout Moments</h3>
            </div>
            <ul className="space-y-3">
              {standoutMoments.map((m, i) => (
                <li key={i} className="text-sm text-slate-700 dark:text-slate-300 pl-3 border-l-2 border-amber-400 dark:border-amber-600">
                  {m}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* ── Strengths / Weaknesses / Next Steps ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <Card borderColor="border-emerald-200 dark:border-emerald-800/60" className="p-5 border-t-4 border-t-emerald-500">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg text-emerald-600 dark:text-emerald-400"><CheckIcon /></div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Strengths</h3>
            </div>
            {summary?.strengths?.length ? (
              <ul className="space-y-3">
                {summary.strengths.map((s: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">{s}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-400 italic">Complete an interview to see your strengths.</p>
            )}
          </Card>

          <Card borderColor="border-amber-200 dark:border-amber-800/60" className="p-5 border-t-4 border-t-amber-500">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 bg-amber-100 dark:bg-amber-900/30 rounded-lg text-amber-600 dark:text-amber-400"><WarnIcon /></div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Areas to Improve</h3>
            </div>
            {summary?.weaknesses?.length ? (
              <ul className="space-y-3">
                {summary.weaknesses.map((w: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">{w}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-400 italic">Areas for improvement will appear here.</p>
            )}
          </Card>

          <Card borderColor="border-blue-200 dark:border-blue-800/60" className="p-5 border-t-4 border-t-blue-500">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400"><ArrowIcon /></div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Next Steps</h3>
            </div>
            {summary?.next_steps?.length ? (
              <ol className="space-y-3">
                {summary.next_steps.map((s: string, i: number) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 flex items-center justify-center text-xs font-bold">{i + 1}</span>
                    <span className="text-sm text-slate-700 dark:text-slate-300">{s}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-slate-400 italic">Recommended next steps will appear here.</p>
            )}
          </Card>
        </div>

        {/* ── Rubric Breakdown ── */}
        <Card className="p-6">
          <div className="flex items-center gap-2.5 mb-5">
            <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400"><ChartIcon /></div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Rubric Breakdown</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Detailed scoring by dimension</p>
            </div>
          </div>
          {rubricItems.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-5">
              {rubricItems.map(item => <RubricBar key={item.label} label={item.label} score={item.score} />)}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-6 italic">Rubric details appear after evaluation.</p>
          )}
        </Card>

        {/* ── Pre-interview tips if no eval yet ── */}
        {!evaluation && (
          <Card className="p-5 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/10 dark:to-indigo-900/10 border-blue-100 dark:border-blue-800/40">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-3">Interview Tips</h3>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-slate-700 dark:text-slate-300">
              {[
                'Think out loud — verbalize your reasoning',
                'Clarify constraints before diving in',
                'Cover complexity (Big O) for every solution',
                'Always discuss edge cases and tests',
              ].map((t, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">•</span>{t}
                </li>
              ))}
            </ul>
          </Card>
        )}

      </div>
    </div>
  );
};
