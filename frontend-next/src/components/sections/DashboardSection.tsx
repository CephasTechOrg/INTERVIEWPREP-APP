'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { useUIStore } from '@/lib/stores/uiStore';
import { sessionService } from '@/lib/services/sessionService';
import { SessionSummary, Track, Difficulty, InterviewerProfile } from '@/types/api';
import { useAuthStore } from '@/lib/stores/authStore';
import { Icons } from '@/components/ui/Icons';

// Interviewers matching backend - with actual images
const INTERVIEWERS: Array<InterviewerProfile & { gender: string }> = [
  { id: 'alex', name: 'Alex', gender: 'Male', image_url: '/alex.avif' },
  { id: 'mason', name: 'Mason', gender: 'Male', image_url: '/mason.jpg' },
  { id: 'erica', name: 'Erica', gender: 'Female', image_url: '/erica.jpeg' },
  { id: 'maya', name: 'Maya', gender: 'Female', image_url: '/maya.jpg' },
];

// Role to Track mapping (supports canonical values and legacy display strings)
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

export const DashboardSection = () => {
  const { setCurrentSession, setLoading, setError } = useSessionStore();
  const { user } = useAuthStore();
  const { setCurrentPage, setVoiceEnabled } = useUIStore();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Form state
  const [role, setRole] = useState(normalizeRoleValue(user?.role_pref));
  const [companyStyle, setCompanyStyle] = useState('general');
  const [difficulty, setDifficulty] = useState<Difficulty>('medium');
  const [behavioralTarget, setBehavioralTarget] = useState(2);
  const [selectedInterviewer, setSelectedInterviewer] = useState<string>('alex');
  const [isStarting, setIsStarting] = useState(false);

  // Derive track from role
  const track: Track = ROLE_TO_TRACK[(role || '').trim().toLowerCase()] || 'swe_intern';

  // Stats
  const [stats, setStats] = useState({
    avgScore: 0,
    bestScore: 0,
    dayStreak: 0,
    lastSession: '',
  });

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (sessions.length > 0) {
      calculateStats();
    }
  }, [sessions]);

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

    // Use actual scores from API (filter out null/undefined)
    const scores = completed
      .map(s => s.overall_score)
      .filter((s): s is number => typeof s === 'number' && s > 0);
    
    const avgScore = scores.length > 0
      ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) 
      : 0;
    const bestScore = scores.length > 0 ? Math.max(...scores) : 0;
    
    // Calculate day streak
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
    
    // Last session
    const lastDate = completed[0]?.created_at ? new Date(completed[0].created_at) : null;
    let lastSession = 'Never';
    if (lastDate) {
      const daysDiff = Math.floor((Date.now() - lastDate.getTime()) / 86400000);
      lastSession = daysDiff === 0 ? 'Today' : daysDiff === 1 ? 'Yesterday' : `${daysDiff}d ago`;
    }

    setStats({
      avgScore,
      bestScore,
      dayStreak: streak,
      lastSession,
    });
  };

  const handleStartInterview = async () => {
    const interviewer = INTERVIEWERS.find(i => i.id === selectedInterviewer);
    try {
      setIsStarting(true);
      setLoading(true);
      setVoiceEnabled(true);
      const session = await sessionService.createSession({
        role,
        track,
        company_style: companyStyle,
        difficulty,
        interviewer: interviewer ? { id: interviewer.id, name: interviewer.name, gender: interviewer.gender, image_url: interviewer.image_url } : undefined,
        behavioral_questions_target: behavioralTarget,
      });
      setCurrentSession(session);
      setCurrentPage('interview');
    } catch (err) {
      setError('Failed to create interview session');
    } finally {
      setIsStarting(false);
      setLoading(false);
    }
  };

  const completedSessions = sessions.filter((s) => s.stage === 'done').length;
  const inProgressSessions = sessions.filter((s) => s.stage !== 'done').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Start a new interview session or continue where you left off</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Main Card - Start Interview */}
        <div className="xl:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Start New Interview</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Configure your interview settings</p>
          </div>
          
          <div className="p-5">
            {/* Form Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Role */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                >
                  <option value="swe_intern">SWE Intern</option>
                  <option value="swe_engineer">Software Engineer</option>
                  <option value="senior_engineer">Senior Engineer</option>
                  <option value="cybersecurity">Cybersecurity</option>
                  <option value="data_science">Data Science</option>
                  <option value="devops_cloud">DevOps / Cloud</option>
                  <option value="product_management">Product Management</option>
                </select>
              </div>

              {/* Company Style */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Company Style</label>
                <select
                  value={companyStyle}
                  onChange={(e) => setCompanyStyle(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                >
                  <option value="general">General Tech</option>
                  <option value="amazon">Amazon</option>
                  <option value="apple">Apple</option>
                  <option value="google">Google</option>
                  <option value="microsoft">Microsoft</option>
                  <option value="meta">Meta</option>
                </select>
              </div>

              {/* Difficulty */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Difficulty</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value as Difficulty)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              {/* Behavioral Questions */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Behavioral Questions</label>
                <select
                  value={behavioralTarget}
                  onChange={(e) => setBehavioralTarget(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                >
                  <option value={0}>0 (All technical)</option>
                  <option value={1}>1</option>
                  <option value={2}>2 (Recommended)</option>
                  <option value={3}>3</option>
                </select>
              </div>
            </div>

            {/* Interviewer Selection */}
            <div className="mt-5">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Choose Your Interviewer</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {INTERVIEWERS.map((person) => (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => setSelectedInterviewer(person.id)}
                    className={`relative p-3 rounded-xl border-2 transition-all duration-200 text-center group ${
                      selectedInterviewer === person.id
                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 ring-2 ring-indigo-500/20'
                        : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-500 hover:bg-slate-50 dark:hover:bg-slate-600'
                    }`}
                  >
                    {/* Selection Check */}
                    {selectedInterviewer === person.id && (
                      <div className="absolute -top-2 -right-2 w-5 h-5 bg-indigo-500 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                    
                    {/* Avatar */}
                    <div className={`relative w-16 h-16 mx-auto rounded-full overflow-hidden border-2 transition-all ${
                      selectedInterviewer === person.id 
                        ? 'border-indigo-400' 
                        : 'border-slate-200 dark:border-slate-500 group-hover:border-slate-300 dark:group-hover:border-slate-400'
                    }`}>
                      <Image
                        src={person.image_url || ''}
                        alt={person.name}
                        fill
                        className="object-cover"
                        sizes="64px"
                      />
                    </div>
                    
                    {/* Name & Gender */}
                    <div className="mt-2">
                      <div className={`font-medium text-sm ${
                        selectedInterviewer === person.id ? 'text-indigo-700 dark:text-indigo-400' : 'text-slate-900 dark:text-white'
                      }`}>
                        {person.name}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">{person.gender}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={handleStartInterview}
              disabled={isStarting}
              className="mt-6 w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg font-medium transition-colors"
            >
              {isStarting ? (
                <>
                  {Icons.spinner}
                  Starting...
                </>
              ) : (
                <>
                  {Icons.play}
                  Start Interview
                </>
              )}
            </button>
          </div>
        </div>

        {/* Stats Card */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Quick Stats</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Your interview performance</p>
          </div>
          
          <div className="p-4">
            <div className="grid grid-cols-2 gap-3">
              {/* Avg Score */}
              <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 bg-indigo-100 dark:bg-indigo-900/50 rounded-md flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                    {Icons.chart}
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.avgScore || '-'}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">Avg Score</div>
              </div>

              {/* Day Streak */}
              <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 bg-orange-100 dark:bg-orange-900/50 rounded-md flex items-center justify-center text-orange-600 dark:text-orange-400">
                    {Icons.fire}
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.dayStreak}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">Day Streak</div>
              </div>

              {/* Last Session */}
              <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 bg-purple-100 dark:bg-purple-900/50 rounded-md flex items-center justify-center text-purple-600 dark:text-purple-400">
                    {Icons.clock}
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.lastSession || '-'}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">Last Session</div>
              </div>

              {/* Best Score */}
              <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 bg-green-100 dark:bg-green-900/50 rounded-md flex items-center justify-center text-green-600 dark:text-green-400">
                    {Icons.trophy}
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900 dark:text-white">{stats.bestScore || '-'}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">Best Score</div>
              </div>
            </div>

            {/* Session Summary */}
            <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Total Sessions</span>
                <span className="font-semibold text-slate-900 dark:text-white">{sessions.length}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Completed</span>
                <span className="font-semibold text-green-600 dark:text-green-400">{completedSessions}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">In Progress</span>
                <span className="font-semibold text-amber-600 dark:text-amber-400">{inProgressSessions}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI Chat CTA */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-5 text-white">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">AI Chat Assistant</h3>
            <p className="text-blue-100 text-sm mt-0.5">
              Get quick explanations, mock questions, or study plans
            </p>
          </div>
          <button
            onClick={() => setCurrentPage('chat')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 rounded-lg font-medium hover:bg-indigo-50 dark:hover:bg-slate-600 transition-colors"
          >
            {Icons.chat}
            Open Chat
          </button>
        </div>
      </div>

      {/* Recent Sessions */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Sessions</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Resume or view results</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadSessions}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="Refresh"
            >
              {Icons.refresh}
            </button>
            {sessions.length > 0 && (
              <button
                onClick={() => setCurrentPage('history')}
                className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium"
              >
                View all →
              </button>
            )}
          </div>
        </div>
        
        <div className="divide-y divide-slate-100 dark:divide-slate-700">
          {isLoading ? (
            <div className="p-8 text-center">
              <div className="text-slate-400 mb-2">{Icons.spinner}</div>
              <p className="text-slate-500 dark:text-slate-400 text-sm">Loading sessions...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-12 h-12 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mx-auto mb-3 text-slate-400">
                {Icons.history}
              </div>
              <p className="text-slate-900 dark:text-white font-medium">No sessions yet</p>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Start your first interview above</p>
            </div>
          ) : (
            sessions.slice(0, 5).map((session) => (
              <div
                key={session.id}
                onClick={() => {
                  setCurrentSession(session);
                  setCurrentPage(session.stage === 'done' ? 'results' : 'interview');
                }}
                className="px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                    session.stage === 'done' 
                      ? 'bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400' 
                      : 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400'
                  }`}>
                    {session.stage === 'done' ? Icons.checkCircle : Icons.play}
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white text-sm capitalize">
                      {session.track?.replace(/_/g, ' ') || 'Interview Session'}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                      {session.difficulty} • {session.company_style || 'General'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    session.stage === 'done'
                      ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400'
                      : 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-400'
                  }`}>
                    {session.stage === 'done' ? 'Completed' : 'In Progress'}
                  </span>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {session.created_at 
                      ? new Date(session.created_at as string).toLocaleDateString()
                      : ''}
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
