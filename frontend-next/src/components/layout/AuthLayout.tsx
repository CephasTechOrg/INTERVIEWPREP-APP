'use client';

import { ReactNode } from 'react';

const CheckIcon = () => (
  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
  </svg>
);

const BotIcon = () => (
  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
  </svg>
);

const features = [
  {
    title: 'AI-Powered Interviewer',
    desc: 'Adaptive difficulty that adjusts to your skill level in real time',
  },
  {
    title: 'Instant Detailed Feedback',
    desc: 'Rubric-based scoring with strengths, weaknesses, and next steps',
  },
  {
    title: 'Track Your Progress',
    desc: 'Session history and analytics to watch your improvement over time',
  },
];

interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  subtitle: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex bg-white dark:bg-slate-900">
      {/* ── Left brand panel (desktop only) ── */}
      <div className="hidden lg:flex lg:w-[48%] xl:w-[45%] relative bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 flex-col justify-between p-12 overflow-hidden select-none">
        {/* Decorative blobs */}
        <div className="absolute -top-32 -right-32 w-96 h-96 bg-white/[0.06] rounded-full" />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 bg-white/[0.06] rounded-full" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-white/[0.03] rounded-full" />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm border border-white/20">
            <BotIcon />
          </div>
          <div>
            <span className="text-xl font-bold text-white tracking-tight">InterviewPrep</span>
            <span className="block text-[10px] text-indigo-200 font-semibold tracking-widest uppercase">AI Powered</span>
          </div>
        </div>

        {/* Middle */}
        <div className="relative space-y-10">
          <div>
            <h2 className="text-4xl font-bold text-white leading-snug mb-3">
              Land your<br />
              <span className="text-indigo-200">dream job</span>
            </h2>
            <p className="text-indigo-200 text-base leading-relaxed max-w-xs">
              Practice with a realistic AI interviewer and get the feedback you need to succeed.
            </p>
          </div>

          {/* Features */}
          <ul className="space-y-5">
            {features.map((f) => (
              <li key={f.title} className="flex items-start gap-3.5">
                <div className="mt-0.5 w-5 h-5 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                  <CheckIcon />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{f.title}</p>
                  <p className="text-indigo-200 text-sm leading-relaxed">{f.desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Stats strip */}
        <div className="relative flex items-center gap-8">
          {[['500+', 'Questions'], ['10k+', 'Interviews'], ['95%', 'Satisfaction']].map(([val, label], i, arr) => (
            <div key={label} className="flex items-center gap-8">
              <div>
                <p className="text-2xl font-bold text-white">{val}</p>
                <p className="text-indigo-200 text-xs uppercase tracking-wider">{label}</p>
              </div>
              {i < arr.length - 1 && <div className="w-px h-8 bg-white/20" />}
            </div>
          ))}
        </div>
      </div>

      {/* ── Right form panel ── */}
      <div className="flex-1 flex flex-col justify-center overflow-y-auto px-6 py-12 sm:px-10 lg:px-14 xl:px-20">
        {/* Mobile logo */}
        <div className="lg:hidden mb-10 flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <BotIcon />
          </div>
          <span className="text-lg font-bold text-slate-900 dark:text-white">InterviewPrep AI</span>
        </div>

        {/* Form slot */}
        <div className="w-full max-w-sm mx-auto lg:mx-0">
          <div className="mb-7">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">{title}</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm">{subtitle}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
