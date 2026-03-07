'use client';

import { InterviewLevelOutcome, LevelGap } from '@/types/api';

// ─── Confidence Badge ──────────────────────────────────────────────────────────
const ConfidenceBadge = ({ confidence }: { confidence: 'low' | 'medium' | 'high' }) => {
  const config = {
    low:    { bg: 'bg-amber-500/20',    text: 'text-amber-200',   label: 'Low Confidence' },
    medium: { bg: 'bg-blue-500/20',     text: 'text-blue-200',    label: 'Medium Confidence' },
    high:   { bg: 'bg-emerald-500/20',  text: 'text-emerald-200', label: 'High Confidence' },
  };
  const cfg = config[confidence];
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
};

// ─── Readiness Bar ─────────────────────────────────────────────────────────────
const ReadinessBar = ({ percent, nextLevel }: { percent: number; nextLevel: string }) => {
  const label = nextLevel.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm text-slate-600 dark:text-slate-400">
          Readiness to <span className="font-medium text-slate-700 dark:text-slate-300">{label}</span>
        </span>
        <span className="text-sm font-bold text-slate-900 dark:text-white">{percent}%</span>
      </div>
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

// ─── Gap Card ──────────────────────────────────────────────────────────────────
const GapCard = ({ gap }: { gap: LevelGap }) => {
  const severity =
    gap.gap >= 10 ? { color: 'text-red-600 dark:text-red-400',    bg: 'bg-red-50 dark:bg-red-900/20',    label: 'Significant' } :
    gap.gap >= 5  ? { color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20', label: 'Notable' }     :
                    { color: 'text-blue-600 dark:text-blue-400',   bg: 'bg-blue-50 dark:bg-blue-900/20',  label: 'Minor' };
  return (
    <div className={`flex items-start gap-3 p-3 ${severity.bg} rounded-lg`}>
      <svg className="w-4 h-4 mt-0.5 text-amber-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-slate-900 dark:text-white capitalize">
            {gap.dimension.replace(/_/g, ' ')}
          </span>
          <span className={`text-xs font-medium ${severity.color}`}>{severity.label}</span>
        </div>
        <div className={`text-sm font-medium mt-0.5 ${severity.color}`}>
          {gap.actual_score.toFixed(0)} → {gap.target_score.toFixed(0)}
          <span className="font-normal opacity-75 ml-1">(need +{gap.gap.toFixed(0)})</span>
        </div>
        <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">{gap.interpretation}</div>
      </div>
    </div>
  );
};

// ─── Skeleton ─────────────────────────────────────────────────────────────────
const LevelSkeleton = () => (
  <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden animate-pulse">
    <div className="h-16 bg-gradient-to-r from-violet-600/20 to-indigo-600/20" />
    <div className="p-6 space-y-3">
      <div className="h-7 bg-slate-200 dark:bg-slate-700 rounded-lg w-3/4" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-full" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-2/3" />
    </div>
  </div>
);

// ─── Props ────────────────────────────────────────────────────────────────────
interface Props {
  outcome: InterviewLevelOutcome | null;
  loading?: boolean;
  /** "card" = level + readiness bar only. "gaps" = gaps + action plan only. */
  variant: 'card' | 'gaps';
}

// ─── Main component ───────────────────────────────────────────────────────────
export const LevelCalibrationSection = ({ outcome, loading = false, variant }: Props) => {

  // ── Card variant ────────────────────────────────────────────────────────────
  if (variant === 'card') {
    if (loading) return <LevelSkeleton />;
    if (!outcome) return null;

    const roleLabel = outcome.role.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const tierLabel = outcome.company_tier.charAt(0).toUpperCase() + outcome.company_tier.slice(1);

    return (
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-violet-200 dark:border-violet-900/60 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-violet-600 to-indigo-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-white font-bold text-base">Level Assessment</h3>
              <p className="text-violet-200 text-sm mt-0.5">{roleLabel} · {tierLabel} Tier</p>
            </div>
            <ConfidenceBadge confidence={outcome.confidence} />
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div className="text-2xl font-bold text-slate-900 dark:text-white">
            {outcome.estimated_level_display}
          </div>
          {outcome.next_level ? (
            <ReadinessBar percent={outcome.readiness_percent} nextLevel={outcome.next_level} />
          ) : (
            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-900">
              <p className="text-sm text-emerald-700 dark:text-emerald-300 font-medium">
                🎉 You've reached the highest level for this role and tier. Keep practicing to maintain your edge.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Gaps variant ────────────────────────────────────────────────────────────
  if (loading || !outcome) return null;

  const hasGaps    = outcome.gaps.length > 0;
  const hasActions = outcome.next_actions.length > 0;
  if (!hasGaps && !hasActions) return null;

  return (
    <div className="space-y-5">

      {hasGaps && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="border-b border-slate-200 dark:border-slate-700 px-6 py-4">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">Gaps to Next Level</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Dimensions holding you back — with exact deficit
            </p>
          </div>
          <div className="p-6 space-y-3">
            {outcome.gaps.map(gap => <GapCard key={gap.dimension} gap={gap} />)}
          </div>
        </div>
      )}

      {hasActions && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="border-b border-slate-200 dark:border-slate-700 px-6 py-4">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">Level-Up Action Plan</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Role-specific steps to close the gap and reach the next bar
            </p>
          </div>
          <div className="p-6 space-y-2">
            {outcome.next_actions.map((action, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs font-bold">
                  {idx + 1}
                </span>
                <span className="text-sm text-slate-700 dark:text-slate-300 pt-0.5">{action}</span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
