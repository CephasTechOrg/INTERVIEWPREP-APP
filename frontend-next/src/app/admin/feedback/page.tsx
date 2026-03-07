'use client';

import { useEffect, useState } from 'react';
import { adminService, AdminFeedbackItem, AdminFeedbackStats } from '@/lib/services/adminService';
import { RefreshIcon, StarIcon, ThumbUpIcon } from '@/components/icons/AdminIcons';

// ── Stars display ──────────────────────────────────────────────────────────────
function Stars({ rating, size = 4 }: { rating: number; size?: number }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <StarIcon
          key={s}
          className={`w-${size} h-${size} ${s <= rating ? 'text-amber-400 fill-amber-400' : 'text-slate-300 dark:text-slate-600'}`}
          style={{ fill: s <= rating ? '#fbbf24' : 'none' }}
        />
      ))}
    </span>
  );
}

// ── Rating distribution bar ────────────────────────────────────────────────────
function RatingBar({ star, count, total }: { star: number; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-4 text-slate-500 dark:text-slate-400 text-right font-medium">{star}</span>
      <StarIcon className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" style={{ fill: '#fbbf24' }} />
      <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-amber-400 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-slate-600 dark:text-slate-400 font-medium">{count}</span>
      <span className="w-10 text-right text-slate-400 text-xs">{pct}%</span>
    </div>
  );
}

// ── Feedback row ───────────────────────────────────────────────────────────────
function FeedbackRow({ item }: { item: AdminFeedbackItem }) {
  const [expanded, setExpanded] = useState(false);
  const track = item.session_track?.replace(/_/g, ' ') ?? '—';
  const date = item.created_at ? new Date(item.created_at).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  }) : '—';

  const hasDetails = !!(item.comment || item.rating_questions || item.rating_feedback || item.rating_difficulty);

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 space-y-3 shadow-sm hover:shadow-md transition-shadow">
      {/* Top row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-slate-900 dark:text-white truncate">
            {item.user_email ?? `User #${item.user_id}`}
          </p>
          {item.user_name && (
            <p className="text-sm text-slate-500 dark:text-slate-400">{item.user_name}</p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <Stars rating={item.rating} />
          <span className="text-sm font-bold text-slate-700 dark:text-slate-300">{item.rating}/5</span>
          {item.thumbs && (
            <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
              item.thumbs === 'up'
                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400'
            }`}>
              <ThumbUpIcon
                className={`w-3.5 h-3.5 ${item.thumbs === 'down' ? 'rotate-180' : ''}`}
              />
              {item.thumbs === 'up' ? 'Helpful' : 'Not helpful'}
            </span>
          )}
        </div>
      </div>

      {/* Context chips */}
      <div className="flex flex-wrap gap-2">
        {item.session_track && (
          <span className="px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-medium capitalize">
            {track}
          </span>
        )}
        {item.session_difficulty && (
          <span className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
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
          <span className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs capitalize">
            {item.session_company_style}
          </span>
        )}
        <span className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 text-xs">
          {date}
        </span>
      </div>

      {/* Expandable details */}
      {hasDetails && (
        <>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
          >
            {expanded ? '▲ Hide details' : '▼ Show details'}
          </button>
          {expanded && (
            <div className="space-y-3 pt-2 border-t border-slate-100 dark:border-slate-700">
              {(item.rating_questions || item.rating_feedback || item.rating_difficulty) && (
                <div className="grid grid-cols-3 gap-3">
                  {item.rating_questions != null && (
                    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1.5">Question quality</p>
                      <Stars rating={item.rating_questions} size={3} />
                    </div>
                  )}
                  {item.rating_feedback != null && (
                    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1.5">AI feedback</p>
                      <Stars rating={item.rating_feedback} size={3} />
                    </div>
                  )}
                  {item.rating_difficulty != null && (
                    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1.5">Difficulty fit</p>
                      <Stars rating={item.rating_difficulty} size={3} />
                    </div>
                  )}
                </div>
              )}
              {item.comment && (
                <blockquote className="text-sm text-slate-700 dark:text-slate-300 bg-amber-50 dark:bg-amber-900/10 border-l-4 border-amber-400 rounded-r-lg pl-4 pr-3 py-3 italic">
                  &ldquo;{item.comment}&rdquo;
                </blockquote>
              )}
            </div>
          )}
        </>
      )}

      {/* Inline comment preview (non-expanded) */}
      {!hasDetails && item.comment && (
        <p className="text-sm text-slate-600 dark:text-slate-300 italic">
          &ldquo;{item.comment}&rdquo;
        </p>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────
export default function FeedbackPage() {
  const [stats, setStats] = useState<AdminFeedbackStats | null>(null);
  const [feedbackList, setFeedbackList] = useState<AdminFeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingList, setLoadingList] = useState(true);
  const [filterRating, setFilterRating] = useState<number | undefined>();
  const [filterThumbs, setFilterThumbs] = useState<'up' | 'down' | undefined>();
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  const fetchStats = () => {
    setLoadingStats(true);
    adminService.getFeedbackStats()
      .then(setStats)
      .finally(() => setLoadingStats(false));
  };

  const fetchList = () => {
    setLoadingList(true);
    adminService.getAllFeedback(page * LIMIT, LIMIT, filterRating, filterThumbs)
      .then((res) => { setFeedbackList(res.feedback); setTotal(res.total); })
      .finally(() => setLoadingList(false));
  };

  useEffect(() => { fetchStats(); }, []);
  useEffect(() => { fetchList(); }, [page, filterRating, filterThumbs]);

  const totalPages = Math.ceil(total / LIMIT);
  const responseRate = stats && stats.total_sessions > 0
    ? ((stats.sessions_with_feedback / stats.total_sessions) * 100).toFixed(1)
    : '0';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Feedback &amp; Ratings</h1>
          <p className="text-slate-600 dark:text-slate-400">What users think about their interview experience</p>
        </div>
        <button
          onClick={() => { fetchStats(); fetchList(); }}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
        >
          <RefreshIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats row */}
      {loadingStats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-slate-800 rounded-xl h-28 animate-pulse border border-slate-200 dark:border-slate-700 shadow-sm" />
          ))}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Avg Rating */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Avg Rating</p>
              <div className="p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <StarIcon className="w-5 h-5 text-amber-500" style={{ fill: '#f59e0b' }} />
              </div>
            </div>
            <p className="text-3xl font-bold text-slate-800 dark:text-white">
              {stats.average_rating ? stats.average_rating.toFixed(1) : '—'}
            </p>
            <div className="mt-2">
              {stats.average_rating && <Stars rating={Math.round(stats.average_rating)} />}
            </div>
          </div>

          {/* Response Rate */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Response Rate</p>
              <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <ThumbUpIcon className="w-5 h-5 text-blue-500" />
              </div>
            </div>
            <p className="text-3xl font-bold text-slate-800 dark:text-white">{responseRate}%</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {stats.sessions_with_feedback} of {stats.total_sessions} sessions
            </p>
          </div>

          {/* Thumbs Up */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Thumbs Up</p>
              <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                <ThumbUpIcon className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
            <p className="text-3xl font-bold text-slate-800 dark:text-white">{stats.thumbs_up_count}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{stats.thumbs_down_count} thumbs down</p>
          </div>

          {/* Total Sessions */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Sessions</p>
              <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <StarIcon className="w-5 h-5 text-purple-500" />
              </div>
            </div>
            <p className="text-3xl font-bold text-slate-800 dark:text-white">{stats.total_sessions}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">all time</p>
          </div>
        </div>
      ) : null}

      {/* Rating distribution */}
      {stats && stats.sessions_with_feedback > 0 && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-6">
          <h3 className="font-semibold text-slate-800 dark:text-white mb-4">Rating Distribution</h3>
          <div className="space-y-2.5 max-w-lg">
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

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 items-center bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-5 py-3 shadow-sm">
        <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Filter:</span>
        <select
          className="text-sm border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filterRating ?? ''}
          onChange={(e) => { setPage(0); setFilterRating(e.target.value ? Number(e.target.value) : undefined); }}
        >
          <option value="">All ratings</option>
          {[5, 4, 3, 2, 1].map((r) => (
            <option key={r} value={r}>{r}+ stars</option>
          ))}
        </select>
        <select
          className="text-sm border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filterThumbs ?? ''}
          onChange={(e) => { setPage(0); setFilterThumbs((e.target.value as 'up' | 'down') || undefined); }}
        >
          <option value="">All thumbs</option>
          <option value="up">👍 Thumbs up</option>
          <option value="down">👎 Thumbs down</option>
        </select>
        <span className="ml-auto text-sm text-slate-500 dark:text-slate-400">{total} results</span>
      </div>

      {/* Feedback list */}
      {loadingList ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-slate-800 rounded-xl h-24 animate-pulse border border-slate-200 dark:border-slate-700" />
          ))}
        </div>
      ) : feedbackList.length === 0 ? (
        <div className="text-center py-20 text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <StarIcon className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="font-semibold text-lg">No feedback yet</p>
          <p className="text-sm mt-1">Feedback will appear here once users rate their sessions</p>
        </div>
      ) : (
        <div className="space-y-4">
          {feedbackList.map((item) => (
            <FeedbackRow key={item.id} item={item} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-slate-600 dark:text-slate-400">
            Page {page + 1} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
