'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { sessionService } from '@/lib/services/sessionService';
import { SessionSummary, Track, Difficulty, InterviewerProfile } from '@/types/api';
import { useAuthStore } from '@/lib/stores/authStore';
import { Icons } from '@/components/ui/Icons';

const INTERVIEWERS: Array<InterviewerProfile & { gender: string }> = [
  { id: 'cephas', name: 'Cephas', gender: 'Male', image_url: '/cephas.png' },
  { id: 'mason', name: 'Mason', gender: 'Male', image_url: '/mason.jpg' },
  { id: 'erica', name: 'Erica', gender: 'Female', image_url: '/erica.jpeg' },
  { id: 'maya', name: 'Maya', gender: 'Female', image_url: '/maya.jpg' },
];

const ROLE_TO_TRACK: Record<string, Track> = {
  'swe_intern': 'swe_intern',
  'swe intern': 'swe_intern',
  'software engineer intern': 'swe_intern',
  'intern': 'swe_intern',
  'swe_engineer': 'swe_engineer',
  'software engineer': 'swe_engineer',
  'senior_engineer': 'swe_engineer',
  'senior engineer': 'swe_engineer',
  'senior software engineer': 'swe_engineer',
  'cybersecurity': 'cybersecurity',
  'data_science': 'data_science',
  'data science': 'data_science',
  'devops_cloud': 'devops_cloud',
  'devops / cloud': 'devops_cloud',
  'devops': 'devops_cloud',
  'product_management': 'product_management',
  'product management': 'product_management',
};

const COMPANY_STYLE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'general', label: 'General Tech' },
  { value: 'amazon', label: 'Amazon' },
  { value: 'apple', label: 'Apple' },
  { value: 'bloomberg', label: 'Bloomberg' },
  { value: 'google', label: 'Google' },
  { value: 'jpmorgan_chase', label: 'JPMorgan Chase' },
  { value: 'microsoft', label: 'Microsoft' },
  { value: 'morgan_stanley', label: 'Morgan Stanley' },
  { value: 'salesforce', label: 'Salesforce' },
  { value: 'tesla', label: 'Tesla' },
  { value: 'Y_combinator', label: 'Y Combinator' },
];

const supportsCompanyStyles = (track: Track) => track === 'swe_intern' || track === 'swe_engineer';

const ROLE_VALUE_NORMALIZATION: Record<string, string> = {
  'swe_intern': 'swe_intern',
  'swe intern': 'swe_intern',
  'software engineer intern': 'swe_intern',
  'intern': 'swe_intern',
  'swe_engineer': 'swe_engineer',
  'software engineer': 'swe_engineer',
  'senior_engineer': 'senior_engineer',
  'senior engineer': 'senior_engineer',
  'senior software engineer': 'senior_engineer',
  'cybersecurity': 'cybersecurity',
  'data_science': 'data_science',
  'data science': 'data_science',
  'devops_cloud': 'devops_cloud',
  'devops / cloud': 'devops_cloud',
  'devops': 'devops_cloud',
  'product_management': 'product_management',
  'product management': 'product_management',
};

const normalizeRoleValue = (rawRole?: string | null): string => {
  const value = (rawRole || '').trim().toLowerCase();
  if (!value) return 'swe_intern';
  return ROLE_VALUE_NORMALIZATION[value] || 'swe_intern';
};

const getGreeting = () => {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
};

const selectCls = 'w-full px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-colors appearance-none cursor-pointer';

export const DashboardSection = () => {
  const { setCurrentSession, setLoading, setError } = useSessionStore();
  const { user } = useAuthStore();
  const { setCurrentPage, setVoiceEnabled } = useUIStore();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [role, setRole] = useState(normalizeRoleValue(user?.role_pref));
  const [companyStyle, setCompanyStyle] = useState('general');
  const [difficulty, setDifficulty] = useState<Difficulty>('medium');
  const [behavioralTarget, setBehavioralTarget] = useState(2);
  const [selectedInterviewer, setSelectedInterviewer] = useState<string>('cephas');
  const [isStarting, setIsStarting] = useState(false);
  const [adaptiveDifficultyEnabled, setAdaptiveDifficultyEnabled] = useState(false);

  const track: Track = ROLE_TO_TRACK[(role || '').trim().toLowerCase()] || 'swe_intern';
  const companyStyleOptions = supportsCompanyStyles(track)
    ? COMPANY_STYLE_OPTIONS
    : [{ value: 'general', label: 'General (Only option)' }];

  const [stats, setStats] = useState({ avgScore: 0, bestScore: 0, dayStreak: 0, lastSession: '' });

  useEffect(() => { loadSessions(); }, []);
  useEffect(() => {
    if (!supportsCompanyStyles(track) && companyStyle !== 'general') setCompanyStyle('general');
  }, [track, companyStyle]);
  useEffect(() => { if (sessions.length > 0) calculateStats(); }, [sessions]);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      const result = await sessionService.listSessions();
      setSessions(result);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const calculateStats = () => {
    const completed = sessions.filter(s => s.stage === 'done');
    if (completed.length === 0) {
      setStats({ avgScore: 0, bestScore: 0, dayStreak: 0, lastSession: 'Never' });
      return;
    }
    const scores = completed.map(s => s.overall_score).filter((s): s is number => typeof s === 'number' && s > 0);
    const avgScore = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    const bestScore = scores.length > 0 ? Math.max(...scores) : 0;

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
        const diffDays = Math.round((new Date(sortedDates[i - 1]).getTime() - new Date(sortedDates[i]).getTime()) / 86400000);
        if (diffDays === 1) streak++; else break;
      }
    }

    const lastDate = completed[0]?.created_at ? new Date(completed[0].created_at) : null;
    let lastSession = 'Never';
    if (lastDate) {
      const d = Math.floor((Date.now() - lastDate.getTime()) / 86400000);
      lastSession = d === 0 ? 'Today' : d === 1 ? 'Yesterday' : `${d}d ago`;
    }
    setStats({ avgScore, bestScore, dayStreak: streak, lastSession });
  };

  const handleStartInterview = async () => {
    const interviewer = INTERVIEWERS.find(i => i.id === selectedInterviewer);
    try {
      setIsStarting(true);
      setLoading(true);
      setVoiceEnabled(true);
      const session = await sessionService.createSession({
        role, track, company_style: companyStyle, difficulty,
        interviewer: interviewer ? { id: interviewer.id, name: interviewer.name, gender: interviewer.gender, image_url: interviewer.image_url } : undefined,
        behavioral_questions_target: behavioralTarget,
        adaptive_difficulty_enabled: adaptiveDifficultyEnabled,
      });
      setCurrentSession(session);
      setCurrentPage('interview');
    } catch {
      setError('Failed to create interview session');
    } finally {
      setIsStarting(false);
      setLoading(false);
    }
  };

  const completedSessions = sessions.filter(s => s.stage === 'done').length;
  const inProgressSessions = sessions.filter(s => s.stage !== 'done').length;
  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there';
  const initials = (user?.full_name?.split(' ').map(w => w[0]).slice(0, 2).join('') || user?.email?.[0] || 'U').toUpperCase();

  const statCards = [
    { label: 'Avg Score', value: stats.avgScore || '—', icon: Icons.chart, color: 'from-blue-500 to-blue-600', bg: 'bg-blue-50 dark:bg-blue-500/10', text: 'text-blue-600 dark:text-blue-400' },
    { label: 'Best Score', value: stats.bestScore || '—', icon: Icons.trophy, color: 'from-emerald-500 to-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400' },
    { label: 'Day Streak', value: stats.dayStreak || '—', icon: Icons.fire, color: 'from-orange-500 to-orange-600', bg: 'bg-orange-50 dark:bg-orange-500/10', text: 'text-orange-600 dark:text-orange-400' },
    { label: 'Last Session', value: stats.lastSession || '—', icon: Icons.clock, color: 'from-violet-500 to-violet-600', bg: 'bg-violet-50 dark:bg-violet-500/10', text: 'text-violet-600 dark:text-violet-400' },
  ];

  return (
    <div className="space-y-6">

      {/* ── Welcome ── */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{getGreeting()}</p>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">{firstName}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {completedSessions === 0
              ? 'Ready to start your first practice interview?'
              : `${completedSessions} interview${completedSessions > 1 ? 's' : ''} completed — keep it up.`}
          </p>
        </div>
        <button
          onClick={() => setCurrentPage('interview')}
          className="hidden sm:inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold text-sm transition-colors"
        >
          {Icons.play}
          Quick Start
        </button>
      </div>

      {/* ── Stats Row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {statCards.map((s) => (
          <div key={s.label} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 flex items-center gap-3 shadow-sm">
            <div className={`w-10 h-10 rounded-xl ${s.bg} ${s.text} flex items-center justify-center flex-shrink-0`}>
              {s.icon}
            </div>
            <div className="min-w-0">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{s.label}</p>
              <p className="text-xl font-bold text-slate-900 dark:text-white leading-tight">{s.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Main grid ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* Start Interview Card */}
        <div className="xl:col-span-2 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600 dark:text-blue-400">
              {Icons.play}
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">New Interview</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Configure and launch your session</p>
            </div>
          </div>

          <div className="p-5 space-y-5">
            {/* Role + Company + Difficulty + Behavioral */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wide">Role</label>
                <select value={role} onChange={e => setRole(e.target.value)} className={selectCls}>
                  <option value="swe_intern">SWE Intern</option>
                  <option value="swe_engineer">Software Engineer</option>
                  <option value="senior_engineer">Senior Engineer</option>
                  <option value="cybersecurity">Cybersecurity</option>
                  <option value="data_science">Data Science</option>
                  <option value="devops_cloud">DevOps / Cloud</option>
                  <option value="product_management">Product Management</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wide">Company Style</label>
                <select value={companyStyle} onChange={e => setCompanyStyle(e.target.value)} className={selectCls}>
                  {companyStyleOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                {!supportsCompanyStyles(track) && (
                  <p className="mt-1 text-xs text-slate-400">General style only for this track.</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wide">Difficulty</label>
                <select value={difficulty} onChange={e => setDifficulty(e.target.value as Difficulty)} className={selectCls}>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wide">Behavioral Qs</label>
                <select value={behavioralTarget} onChange={e => setBehavioralTarget(Number(e.target.value))} className={selectCls}>
                  <option value={0}>0 — All technical</option>
                  <option value={1}>1</option>
                  <option value={2}>2 — Recommended</option>
                  <option value={3}>3</option>
                </select>
              </div>
            </div>

            {/* Adaptive toggle */}
            <div className="flex items-center justify-between gap-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-700/40 border border-slate-200 dark:border-slate-700">
              <div>
                <p className="text-sm font-medium text-slate-800 dark:text-white">Adaptive Difficulty</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Auto-adjusts based on your performance</p>
              </div>
              <button
                type="button"
                onClick={() => setAdaptiveDifficultyEnabled(p => !p)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none flex-shrink-0 ${
                  adaptiveDifficultyEnabled ? 'bg-blue-600' : 'bg-slate-200 dark:bg-slate-600'
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${
                  adaptiveDifficultyEnabled ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            {/* Interviewer Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-3 uppercase tracking-wide">Choose Interviewer</label>
              <div className="grid grid-cols-4 gap-2.5">
                {INTERVIEWERS.map(person => (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => setSelectedInterviewer(person.id)}
                    className={`relative p-2.5 rounded-xl border-2 transition-all duration-200 text-center group ${
                      selectedInterviewer === person.id
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-md shadow-blue-500/20'
                        : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 hover:border-blue-300 dark:hover:border-slate-500'
                    }`}
                  >
                    {selectedInterviewer === person.id && (
                      <div className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center shadow-sm">
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                    <div className={`relative w-12 h-12 mx-auto rounded-full overflow-hidden border-2 transition-all ${
                      selectedInterviewer === person.id ? 'border-blue-400' : 'border-slate-200 dark:border-slate-500'
                    }`}>
                      <img src={person.image_url || ''} alt={person.name} className="w-full h-full object-cover object-top" />
                    </div>
                    <p className={`mt-1.5 font-semibold text-xs ${selectedInterviewer === person.id ? 'text-blue-700 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'}`}>
                      {person.name}
                    </p>
                    <p className="text-[10px] text-slate-400">{person.gender}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={handleStartInterview}
              disabled={isStarting}
              className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-colors"
            >
              {isStarting ? (
                <>{Icons.spinner} Starting session...</>
              ) : (
                <>{Icons.play} Start Interview</>
              )}
            </button>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Session summary card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                {Icons.chart}
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">Overview</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">Session breakdown</p>
              </div>
            </div>
            <div className="p-4 space-y-3">
              {[
                { label: 'Total Sessions', value: sessions.length, color: 'text-slate-900 dark:text-white' },
                { label: 'Completed', value: completedSessions, color: 'text-emerald-600 dark:text-emerald-400' },
                { label: 'In Progress', value: inProgressSessions, color: 'text-amber-600 dark:text-amber-400' },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between py-2 border-b border-slate-50 dark:border-slate-700/50 last:border-0">
                  <span className="text-sm text-slate-600 dark:text-slate-400">{row.label}</span>
                  <span className={`text-base font-bold ${row.color}`}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* AI Chat CTA */}
          <div className="bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
            <div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center mb-3 text-slate-500 dark:text-slate-400">
              {Icons.chat}
            </div>
            <h3 className="font-semibold text-slate-900 dark:text-white">AI Chat Assistant</h3>
            <p className="text-slate-500 dark:text-slate-400 text-xs mt-1 mb-4">Get explanations, mock questions, or build a study plan</p>
            <button
              onClick={() => setCurrentPage('chat')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold text-sm transition-colors"
            >
              {Icons.chat}
              Open Chat
            </button>
          </div>
        </div>
      </div>

      {/* ── Recent Sessions ── */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-500 dark:text-slate-400">
              {Icons.history}
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">Recent Sessions</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Resume or view results</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={loadSessions} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors" title="Refresh">
              {Icons.refresh}
            </button>
            {sessions.length > 0 && (
              <button onClick={() => setCurrentPage('history')} className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 font-semibold px-2 py-1 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors">
                View all →
              </button>
            )}
          </div>
        </div>

        <div className="divide-y divide-slate-50 dark:divide-slate-700/60">
          {isLoading ? (
            <div className="p-10 text-center">
              <div className="text-slate-400 flex justify-center mb-2">{Icons.spinner}</div>
              <p className="text-slate-400 text-sm">Loading sessions...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-10 text-center">
              <div className="w-14 h-14 bg-blue-50 dark:bg-blue-500/10 rounded-2xl flex items-center justify-center mx-auto mb-3 text-blue-400">
                {Icons.history}
              </div>
              <p className="text-slate-700 dark:text-white font-semibold">No sessions yet</p>
              <p className="text-slate-400 text-sm mt-1">Start your first interview above to get going</p>
            </div>
          ) : (
            sessions.slice(0, 5).map(session => (
              <div
                key={session.id}
                onClick={() => {
                  setCurrentSession(session);
                  setCurrentPage(session.stage === 'done' ? 'results' : 'interview');
                }}
                className="px-5 py-3.5 hover:bg-slate-50 dark:hover:bg-slate-700/40 cursor-pointer transition-colors flex items-center justify-between group"
              >
                <div className="flex items-center gap-3.5">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    session.stage === 'done'
                      ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400'
                      : 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400'
                  }`}>
                    {session.stage === 'done' ? Icons.checkCircle : Icons.play}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-white text-sm capitalize">
                      {session.track?.replace(/_/g, ' ') || 'Interview Session'}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                      {session.difficulty} · {session.company_style || 'General'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                    session.stage === 'done'
                      ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400'
                      : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400'
                  }`}>
                    {session.stage === 'done' ? 'Done' : 'In Progress'}
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {session.created_at ? new Date(session.created_at as string).toLocaleDateString() : ''}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
