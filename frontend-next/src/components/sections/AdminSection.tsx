'use client';

import { useEffect, useState } from 'react';
import {
  adminService,
  AdminFeedbackItem,
  AdminFeedbackStats,
} from '@/lib/services/adminService';

// ── Audit log types ────────────────────────────────────────────────────────────
interface AuditLogEntry {
  id: number;
  action: string;
  user_id?: number | null;
  admin_id?: number | null;
  metadata?: Record<string, unknown> | null;
  timestamp: string;
  ip?: string | null;
}

// ── Stat card ──────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

// ── Star display ───────────────────────────────────────────────────────────────
function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <svg
          key={s}
          className={`w-4 h-4 ${s <= rating ? 'text-amber-400' : 'text-slate-300 dark:text-slate-600'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </span>
  );
}

// ── Rating distribution bar ────────────────────────────────────────────────────
function RatingBar({ star, count, total }: { star: number; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-4 text-slate-500 dark:text-slate-400 text-right">{star}</span>
      <svg className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
      </svg>
      <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
        <div className="bg-amber-400 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-slate-500 dark:text-slate-400 text-right">{count}</span>
    </div>
  );
}

// ── Feedback row ───────────────────────────────────────────────────────────────
function FeedbackRow({ item }: { item: AdminFeedbackItem }) {
  const [expanded, setExpanded] = useState(false);
  const track = item.session_track?.replace('_', ' ') ?? '—';
  const date = item.created_at ? new Date(item.created_at).toLocaleDateString() : '—';

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2">
      {/* Top row */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium text-slate-900 dark:text-white text-sm">
            {item.user_email ?? `User #${item.user_id}`}
          </p>
          {item.user_name && (
            <p className="text-xs text-slate-500 dark:text-slate-400">{item.user_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Stars rating={item.rating} />
          {item.thumbs && (
            <span className={`text-lg leading-none ${item.thumbs === 'up' ? 'text-emerald-500' : 'text-red-400'}`}>
              {item.thumbs === 'up' ? '👍' : '👎'}
            </span>
          )}
        </div>
      </div>

      {/* Session context chips */}
      <div className="flex flex-wrap gap-1.5">
        {item.session_track && (
          <span className="px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-medium capitalize">
            {track}
          </span>
        )}
        {item.session_difficulty && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
            item.session_difficulty === 'hard'
              ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
              : item.session_difficulty === 'medium'
              ? 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
              : 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
          }`}>
            {item.session_difficulty}
          </span>
        )}
        {item.session_company_style && (
          <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs capitalize">
            {item.session_company_style}
          </span>
        )}
        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 text-xs">
          {date}
        </span>
      </div>

      {/* Detailed ratings + comment (expandable) */}
      {(item.comment || item.rating_questions || item.rating_feedback || item.rating_difficulty) && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          {expanded ? 'Hide details' : 'Show details'}
        </button>
      )}
      {expanded && (
        <div className="space-y-2 pt-1 border-t border-slate-100 dark:border-slate-700">
          {(item.rating_questions || item.rating_feedback || item.rating_difficulty) && (
            <div className="grid grid-cols-3 gap-2 text-xs text-slate-600 dark:text-slate-300">
              {item.rating_questions && (
                <div>
                  <p className="text-slate-400 mb-0.5">Questions</p>
                  <Stars rating={item.rating_questions} />
                </div>
              )}
              {item.rating_feedback && (
                <div>
                  <p className="text-slate-400 mb-0.5">Feedback</p>
                  <Stars rating={item.rating_feedback} />
                </div>
              )}
              {item.rating_difficulty && (
                <div>
                  <p className="text-slate-400 mb-0.5">Difficulty</p>
                  <Stars rating={item.rating_difficulty} />
                </div>
              )}
            </div>
          )}
          {item.comment && (
            <p className="text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 italic">
              &ldquo;{item.comment}&rdquo;
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function AdminSection() {
  const [tab, setTab] = useState<'feedback' | 'audit'>('feedback');
  const [stats, setStats] = useState<AdminFeedbackStats | null>(null);
  const [feedbackList, setFeedbackList] = useState<AdminFeedbackItem[]>([]);
  const [feedbackTotal, setFeedbackTotal] = useState(0);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingFeedback, setLoadingFeedback] = useState(true);
  const [filterRating, setFilterRating] = useState<number | undefined>(undefined);
  const [filterThumbs, setFilterThumbs] = useState<'up' | 'down' | undefined>(undefined);
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  // Audit log state
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(0);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const AUDIT_LIMIT = 50;

  useEffect(() => {
    adminService.getFeedbackStats()
      .then(setStats)
      .finally(() => setLoadingStats(false));
  }, []);

  useEffect(() => {
    if (tab !== 'audit') return;
    setLoadingAudit(true);
    adminService.getAuditLogs(auditPage * AUDIT_LIMIT, AUDIT_LIMIT)
      .then((res) => { setAuditLogs(res.logs as unknown as AuditLogEntry[]); setAuditTotal(res.total); })
      .finally(() => setLoadingAudit(false));
  }, [tab, auditPage]);

  useEffect(() => {
    setLoadingFeedback(true);
    adminService.getAllFeedback(page * LIMIT, LIMIT, filterRating, filterThumbs)
      .then((res) => {
        setFeedbackList(res.feedback);
        setFeedbackTotal(res.total);
      })
      .finally(() => setLoadingFeedback(false));
  }, [page, filterRating, filterThumbs]);

  const totalPages = Math.ceil(feedbackTotal / LIMIT);
  const feedbackRate = stats
    ? stats.total_sessions > 0
      ? Math.round((stats.sessions_with_feedback / stats.total_sessions) * 100)
      : 0
    : null;

  return (
    <div className="min-h-full bg-slate-50 dark:bg-slate-900 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Admin Portal</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Platform overview and user feedback</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-200 dark:bg-slate-800 rounded-xl p-1 w-fit">
        {(['feedback', 'audit'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition-all ${
              tab === t
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'feedback' && (
        <div className="space-y-6">
          {/* Stats row */}
          {loadingStats ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 rounded-2xl h-24 animate-pulse border border-slate-200 dark:border-slate-700" />
              ))}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                label="Avg Rating"
                value={stats.average_rating ? `${stats.average_rating.toFixed(1)} ★` : '—'}
                sub={`${stats.sessions_with_feedback} responses`}
              />
              <StatCard
                label="Response Rate"
                value={feedbackRate !== null ? `${feedbackRate}%` : '—'}
                sub={`${stats.sessions_with_feedback} / ${stats.total_sessions} sessions`}
              />
              <StatCard
                label="Thumbs Up"
                value={stats.thumbs_up_count}
                sub={`${stats.thumbs_down_count} thumbs down`}
              />
              <StatCard
                label="Total Sessions"
                value={stats.total_sessions}
                sub="all time"
              />
            </div>
          ) : null}

          {/* Rating distribution */}
          {stats && stats.sessions_with_feedback > 0 && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">Rating Distribution</h3>
              <div className="space-y-2">
                {[5, 4, 3, 2, 1].map((star) => (
                  <RatingBar
                    key={star}
                    star={star}
                    count={stats.rating_distribution[star] ?? 0}
                    total={stats.sessions_with_feedback}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm text-slate-500 dark:text-slate-400 font-medium">Filter:</span>
            <select
              className="text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg px-3 py-1.5"
              value={filterRating ?? ''}
              onChange={(e) => {
                setPage(0);
                setFilterRating(e.target.value ? Number(e.target.value) : undefined);
              }}
            >
              <option value="">All ratings</option>
              {[5, 4, 3, 2, 1].map((r) => (
                <option key={r} value={r}>{r}+ stars</option>
              ))}
            </select>
            <select
              className="text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg px-3 py-1.5"
              value={filterThumbs ?? ''}
              onChange={(e) => {
                setPage(0);
                setFilterThumbs((e.target.value as 'up' | 'down') || undefined);
              }}
            >
              <option value="">All thumbs</option>
              <option value="up">👍 Thumbs up</option>
              <option value="down">👎 Thumbs down</option>
            </select>
            <span className="text-xs text-slate-400 ml-auto">{feedbackTotal} results</span>
          </div>

          {/* Feedback list */}
          {loadingFeedback ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 rounded-xl h-20 animate-pulse border border-slate-200 dark:border-slate-700" />
              ))}
            </div>
          ) : feedbackList.length === 0 ? (
            <div className="text-center py-16 text-slate-400 dark:text-slate-500">
              <p className="text-4xl mb-3">💬</p>
              <p className="font-medium">No feedback yet</p>
              <p className="text-sm mt-1">Feedback will appear here once users rate their sessions</p>
            </div>
          ) : (
            <div className="space-y-3">
              {feedbackList.map((item) => (
                <FeedbackRow key={item.id} item={item} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 pt-2">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="px-4 py-2 rounded-lg text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-slate-500 dark:text-slate-400">
                {page + 1} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
                className="px-4 py-2 rounded-lg text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {tab === 'audit' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500 dark:text-slate-400">{auditTotal} total actions logged</p>
            <button
              onClick={() => { setAuditPage(0); setLoadingAudit(true); adminService.getAuditLogs(0, AUDIT_LIMIT).then(r => { setAuditLogs(r.logs as unknown as AuditLogEntry[]); setAuditTotal(r.total); }).finally(() => setLoadingAudit(false)); }}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              Refresh
            </button>
          </div>

          {loadingAudit ? (
            <div className="space-y-2">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 rounded-xl h-14 animate-pulse border border-slate-200 dark:border-slate-700" />
              ))}
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="text-center py-16 text-slate-400 dark:text-slate-500">
              <p className="text-4xl mb-3">📋</p>
              <p className="font-medium">No audit logs yet</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80">
                      <th className="text-left px-4 py-3 font-semibold text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">Action</th>
                      <th className="text-left px-4 py-3 font-semibold text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">Admin</th>
                      <th className="text-left px-4 py-3 font-semibold text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">Target User</th>
                      <th className="text-left px-4 py-3 font-semibold text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">Timestamp</th>
                      <th className="text-left px-4 py-3 font-semibold text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">IP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                    {auditLogs.map((log) => {
                      const actionColor =
                        log.action.includes('ban') ? 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20' :
                        log.action.includes('delete') ? 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20' :
                        log.action.includes('unban') ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20' :
                        'text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700';
                      return (
                        <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                          <td className="px-4 py-3">
                            <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-mono font-medium ${actionColor}`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                            {log.admin_id ? `#${log.admin_id}` : '—'}
                          </td>
                          <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                            {log.user_id ? `#${log.user_id}` : '—'}
                            {log.metadata && (log.metadata as any).deleted_email ? (
                              <span className="ml-1 text-red-400">({(log.metadata as any).deleted_email})</span>
                            ) : null}
                          </td>
                          <td className="px-4 py-3 text-slate-400 dark:text-slate-500 text-xs whitespace-nowrap">
                            {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                          </td>
                          <td className="px-4 py-3 text-slate-400 dark:text-slate-500 text-xs font-mono">
                            {log.ip ?? '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Audit pagination */}
          {Math.ceil(auditTotal / AUDIT_LIMIT) > 1 && (
            <div className="flex justify-center gap-2 pt-2">
              <button
                disabled={auditPage === 0}
                onClick={() => setAuditPage(p => p - 1)}
                className="px-4 py-2 rounded-lg text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-slate-500 dark:text-slate-400">
                {auditPage + 1} / {Math.ceil(auditTotal / AUDIT_LIMIT)}
              </span>
              <button
                disabled={auditPage >= Math.ceil(auditTotal / AUDIT_LIMIT) - 1}
                onClick={() => setAuditPage(p => p + 1)}
                className="px-4 py-2 rounded-lg text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
