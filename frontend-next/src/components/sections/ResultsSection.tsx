'use client';

import { useEffect } from 'react';
import { useSessionStore } from '@/lib/stores/sessionStore';
import { analyticsService } from '@/lib/services/analyticsService';

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

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Interview Results</h2>
        <p className="text-gray-600">Review your performance and actionable feedback.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Score Card */}
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Score</h3>
          <div className="text-5xl font-bold text-blue-600">
            {evaluation?.overall_score ?? '--'}
          </div>
          <p className="text-sm text-gray-500 mt-2">out of 100</p>
        </div>

        {/* Summary */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
          {evaluation?.summary ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">Strengths</h4>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  {(evaluation.summary.strengths || []).map((item, idx) => (
                    <li key={`strength-${idx}`}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">Weaknesses</h4>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  {(evaluation.summary.weaknesses || []).map((item, idx) => (
                    <li key={`weakness-${idx}`}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">Next Steps</h4>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  {(evaluation.summary.next_steps || []).map((item, idx) => (
                    <li key={`next-${idx}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">Complete an interview session to see your summary here.</p>
          )}
        </div>
      </div>

      {/* Rubric Placeholder */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Rubric Breakdown</h3>
        {evaluation?.rubric ? (
          <pre className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 overflow-x-auto">
            {JSON.stringify(evaluation.rubric, null, 2)}
          </pre>
        ) : (
          <p className="text-gray-500">Rubric details will appear after evaluation.</p>
        )}
      </div>
    </div>
  );
};
