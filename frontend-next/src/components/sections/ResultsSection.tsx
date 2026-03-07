'use client';

import { Component, useEffect, useMemo, useState } from 'react';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { analyticsService } from '@/lib/services/analyticsService';
import { feedbackService } from '@/lib/services/feedbackService';
import { LevelCalibrationSection } from '@/components/sections/LevelCalibrationSection';
import { InterviewLevelOutcome, FeedbackOut, FeedbackCreate } from '@/types/api';

// ─── Error Boundary (catches LevelCalibration render crashes) ──────────────────
class LevelBoundary extends Component<{ children: React.ReactNode }, { crashed: boolean }> {
  state = { crashed: false };
  static getDerivedStateFromError() { return { crashed: true }; }
  render() { return this.state.crashed ? null : this.props.children; }
}

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
  yes:        { label: 'Hire',        bg: 'bg-blue-100 dark:bg-blue-900/40',       text: 'text-blue-700 dark:text-blue-300',    dot: 'bg-blue-500' },
  borderline: { label: 'Borderline',  bg: 'bg-amber-100 dark:bg-amber-900/40',     text: 'text-amber-700 dark:text-amber-300',  dot: 'bg-amber-500' },
  no:         { label: 'No Hire',     bg: 'bg-red-100 dark:bg-red-900/40',         text: 'text-red-700 dark:text-red-300',      dot: 'bg-red-400' },
  strong_no:  { label: 'Strong No',   bg: 'bg-red-100 dark:bg-red-900/40',         text: 'text-red-800 dark:text-red-200',      dot: 'bg-red-600' },
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
const CheckIcon  = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
const WarnIcon   = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
const ChartIcon  = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>;
const SparkIcon  = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>;
const EyeIcon    = () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.964-7.178z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;
const DownloadIcon = () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>;
const StarIcon   = ({ filled }: { filled: boolean }) => (
  <svg className={`w-7 h-7 transition-colors ${filled ? 'text-amber-400' : 'text-slate-300 dark:text-slate-600'}`} fill={filled ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
  </svg>
);

// ─── Card wrapper ──────────────────────────────────────────────────────────────
const Card = ({ children, borderColor = 'border-slate-200 dark:border-slate-700', className = '' }: { children: React.ReactNode; borderColor?: string; className?: string }) => (
  <div className={`bg-white dark:bg-slate-800 rounded-2xl border ${borderColor} shadow-sm ${className}`}>
    {children}
  </div>
);

// ─── Feedback Modal ────────────────────────────────────────────────────────────
const FeedbackModal = ({
  sessionId,
  existing,
  onClose,
  onSubmitted,
}: {
  sessionId: number;
  existing: FeedbackOut | null;
  onClose: () => void;
  onSubmitted: (fb: FeedbackOut) => void;
}) => {
  const [rating, setRating] = useState(existing?.rating ?? 0);
  const [hovered, setHovered] = useState(0);
  const [thumbs, setThumbs] = useState<'up' | 'down' | null>(existing?.thumbs ?? null);
  const [comment, setComment] = useState(existing?.comment ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitted = !!existing;

  const handleSubmit = async () => {
    if (rating === 0) { setError('Please select a star rating.'); return; }
    setSubmitting(true);
    setError(null);
    try {
      const payload: FeedbackCreate = { session_id: sessionId, rating, thumbs, comment: comment.trim() || null };
      const result = await feedbackService.submitFeedback(payload);
      onSubmitted(result);
    } catch {
      setError('Failed to submit feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-slate-200 dark:border-slate-700" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Rate Your Session</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Your feedback helps us improve</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {submitted ? (
          /* Already submitted state */
          <div className="text-center py-4 space-y-3">
            <div className="w-14 h-14 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center mx-auto">
              <svg className="w-7 h-7 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">Thank you for your feedback!</p>
              <div className="flex justify-center gap-0.5 mt-2">
                {[1,2,3,4,5].map(i => <StarIcon key={i} filled={i <= (existing?.rating ?? 0)} />)}
              </div>
              {existing?.comment && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 italic">"{existing.comment}"</p>
              )}
            </div>
            <button onClick={onClose} className="mt-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors">Close</button>
          </div>
        ) : (
          /* Rating form */
          <div className="space-y-5">
            {/* Stars */}
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Overall experience</p>
              <div className="flex gap-1" onMouseLeave={() => setHovered(0)}>
                {[1,2,3,4,5].map(i => (
                  <button key={i} type="button" onMouseEnter={() => setHovered(i)} onClick={() => setRating(i)} className="transition-transform hover:scale-110">
                    <StarIcon filled={i <= (hovered || rating)} />
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-1.5">
                {rating === 5 ? 'Excellent' : rating === 4 ? 'Very good' : rating === 3 ? 'Okay' : rating === 2 ? 'Poor' : rating === 1 ? 'Very poor' : 'Click to rate'}
              </p>
            </div>

            {/* Thumbs */}
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Quick verdict</p>
              <div className="flex gap-3">
                <button type="button" onClick={() => setThumbs(thumbs === 'up' ? null : 'up')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all ${thumbs === 'up' ? 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400' : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-emerald-300'}`}>
                  <span className="text-lg">👍</span> Helpful
                </button>
                <button type="button" onClick={() => setThumbs(thumbs === 'down' ? null : 'down')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all ${thumbs === 'down' ? 'bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-700 dark:text-red-400' : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-red-300'}`}>
                  <span className="text-lg">👎</span> Not helpful
                </button>
              </div>
            </div>

            {/* Comment */}
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Comments <span className="text-slate-400 font-normal">(optional)</span></p>
              <textarea value={comment} onChange={e => setComment(e.target.value)} maxLength={2000} rows={3}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                placeholder="What could we improve? What did you like?" />
              <p className="text-xs text-slate-400 text-right mt-0.5">{comment.length}/2000</p>
            </div>

            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

            <div className="flex gap-3 pt-1">
              <button onClick={onClose} className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                Cancel
              </button>
              <button onClick={handleSubmit} disabled={submitting || rating === 0}
                className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold disabled:opacity-50 transition-colors shadow-sm shadow-blue-500/25">
                {submitting ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Main component ────────────────────────────────────────────────────────────
export const ResultsSection = () => {
  const { currentSession, evaluation, messages, setEvaluation, setLoading, setError } = useSessionStore();
  const [levelOutcome, setLevelOutcome] = useState<InterviewLevelOutcome | null>(null);
  const [levelLoading, setLevelLoading] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [existingFeedback, setExistingFeedback] = useState<FeedbackOut | null>(null);

  useEffect(() => {
    if (currentSession) loadEvaluation();
  }, [currentSession?.id]);

  useEffect(() => {
    if (!currentSession?.id) return;
    setLevelLoading(true);
    analyticsService
      .getSessionLevelCalibration(currentSession.id)
      .then(setLevelOutcome)
      .catch(() => setLevelOutcome(null))
      .finally(() => setLevelLoading(false));
    // Load any existing feedback for this session
    feedbackService.getSessionFeedback(currentSession.id).then(setExistingFeedback);
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

  // Download conversation transcript as a plain text file
  const downloadTranscript = () => {
    if (!messages.length || !currentSession) return;
    const header = [
      'IntervIQ — Interview Transcript',
      `Session #${currentSession.id}`,
      `Role: ${currentSession.track?.replace(/_/g, ' ')}`,
      `Company Style: ${currentSession.company_style}`,
      `Difficulty: ${currentSession.difficulty}`,
      `Score: ${evaluation?.overall_score ?? 'N/A'} / 100`,
      '─'.repeat(50),
      '',
    ].join('\n');

    const body = messages
      .filter(m => m.role !== 'system')
      .map(m => {
        const speaker = m.role === 'interviewer' ? 'INTERVIEWER' : 'YOU';
        const time = m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        return `[${time}] ${speaker}\n${m.content}\n`;
      })
      .join('\n');

    const blob = new Blob([header + body], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `interviq-session-${currentSession.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const rubricItems = useMemo(() => {
    if (!evaluation?.rubric) return [];
    return Object.entries(evaluation.rubric)
      .filter(([k]) => !k.startsWith('_') && k !== 'comments')
      .map(([k, v]) => ({ label: k, score: typeof v === 'number' ? v : (v as any)?.score ?? 0 }));
  }, [evaluation?.rubric]);

  const perf = (() => {
    const s = evaluation?.overall_score ?? null;
    if (s === null) return { label: 'Pending',          color: 'text-slate-500 dark:text-slate-400' };
    if (s >= 80)    return { label: 'Excellent',         color: 'text-emerald-600 dark:text-emerald-400' };
    if (s >= 60)    return { label: 'Good',              color: 'text-blue-600 dark:text-blue-400' };
    if (s >= 40)    return { label: 'Needs Improvement', color: 'text-amber-600 dark:text-amber-400' };
    return            { label: 'Keep Practicing',        color: 'text-red-600 dark:text-red-400' };
  })();

  const summary         = evaluation?.summary as any;
  const narrative       = summary?.narrative        as string | undefined;
  const hireSignal      = summary?.hire_signal      as string | undefined;
  const patternsObs     = summary?.patterns_observed as string[] | undefined;
  const standoutMoments = summary?.standout_moments  as string[] | undefined;
  const hasTranscript   = messages.length > 0 && !!currentSession;

  if (!evaluation && !currentSession) {
    return (
      <div className="min-h-full flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-5 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
            <ChartIcon />
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No Results Yet</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Complete an interview session and click Submit & Evaluate to see your results here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-50 dark:bg-slate-900 p-4 md:p-6">
      {/* Feedback Modal */}
      {showFeedback && currentSession && (
        <FeedbackModal
          sessionId={currentSession.id}
          existing={existingFeedback}
          onClose={() => setShowFeedback(false)}
          onSubmitted={(fb) => { setExistingFeedback(fb); }}
        />
      )}

      <div className="max-w-5xl mx-auto space-y-5">

        {/* 1 ── Header: Score + Hire Signal ── */}
        <Card className="overflow-hidden">
          <div className="bg-gradient-to-r from-blue-900 to-blue-800 px-6 py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-xl font-bold text-white">Interview Results</h1>
                {currentSession && (
                  <p className="text-blue-300 text-sm mt-0.5">
                    Session #{currentSession.id} · {currentSession.track?.replace(/_/g, ' ')} · {currentSession.company_style} · {currentSession.difficulty}
                  </p>
                )}
              </div>
              {/* Action buttons */}
              {evaluation && (
                <div className="flex items-center gap-2 flex-shrink-0">
                  {hasTranscript && (
                    <button onClick={downloadTranscript}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-700 text-blue-200 hover:bg-blue-800 hover:text-white text-xs font-medium transition-colors"
                      title="Download transcript">
                      <DownloadIcon />
                      <span className="hidden sm:inline">Transcript</span>
                    </button>
                  )}
                  <button onClick={() => setShowFeedback(true)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      existingFeedback
                        ? 'border border-amber-500/50 text-amber-300 hover:bg-amber-900/30'
                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-500/30'
                    }`}>
                    <span>{existingFeedback ? '★' : '☆'}</span>
                    <span>{existingFeedback ? `Rated ${existingFeedback.rating}/5` : 'Rate Session'}</span>
                  </button>
                </div>
              )}
            </div>
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

        {/* 2 ── Level Card: level + readiness % ── */}
        <LevelBoundary>
          <LevelCalibrationSection outcome={levelOutcome} loading={levelLoading} variant="card" />
        </LevelBoundary>

        {/* 3 ── Patterns Observed ── */}
        {patternsObs && patternsObs.length > 0 && (
          <Card borderColor="border-indigo-200 dark:border-indigo-800/60" className="p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="p-1.5 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg text-indigo-600 dark:text-indigo-400"><EyeIcon /></div>
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

        {/* 4 ── Standout Moments ── */}
        {standoutMoments && standoutMoments.length > 0 && (
          <Card borderColor="border-amber-200 dark:border-amber-800/60" className="p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="p-1.5 bg-amber-100 dark:bg-amber-900/40 rounded-lg text-amber-600 dark:text-amber-400"><SparkIcon /></div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Standout Moments</h3>
            </div>
            <ul className="space-y-3">
              {standoutMoments.map((m, i) => (
                <li key={i} className="text-sm text-slate-700 dark:text-slate-300 pl-3 border-l-2 border-amber-400 dark:border-amber-600">{m}</li>
              ))}
            </ul>
          </Card>
        )}

        {/* 5 ── Strengths ── */}
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

        {/* 6 ── Areas to Improve ── */}
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

        {/* 7 ── Gaps to Next Level + Action Plan ── */}
        <LevelBoundary>
          <LevelCalibrationSection outcome={levelOutcome} loading={false} variant="gaps" />
        </LevelBoundary>

        {/* 8 ── Performance Breakdown ── */}
        <Card className="p-6">
          <div className="flex items-center gap-2.5 mb-5">
            <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400"><ChartIcon /></div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Performance Breakdown</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Scores by dimension</p>
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
