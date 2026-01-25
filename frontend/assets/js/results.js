
// Results page script (scoped to avoid global name collisions).
(() => {
  // Theme utilities for results page
  const THEME_KEY = "dark_theme";
  const loadThemeToggleSafe =
    typeof loadThemeToggle === "function"
      ? loadThemeToggle
      : () => {
          try {
            return localStorage.getItem(THEME_KEY) === "1";
          } catch {
            return false;
          }
        };

  const applyThemeSafe =
    typeof applyTheme === "function"
      ? applyTheme
      : (isDark) => {
          const html = document.documentElement;
          html.setAttribute("data-theme", isDark ? "dark" : "light");
        };

  // Initialize results page
  document.addEventListener("DOMContentLoaded", async () => {
    // Apply theme first
    const savedTheme = loadThemeToggleSafe();
    applyThemeSafe(savedTheme);

      requireAuthOrRedirect();

      // Get session ID from URL or localStorage
      function getSessionIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('session_id');
      }

      function formatCompanyStyle(value) {
        const raw = String(value || '').trim();
        if (!raw) return '--';
        if (raw.toLowerCase() === 'general') return 'General';
        return raw.slice(0, 1).toUpperCase() + raw.slice(1);
      }

      function pickLatestCompletedSession(sessions) {
        const completed = (sessions || []).filter((s) => typeof s.overall_score === 'number');
        if (!completed.length) return null;
        const toTime = (value) => {
          if (!value) return 0;
          const t = new Date(value).getTime();
          return Number.isNaN(t) ? 0 : t;
        };
        return completed.sort((a, b) => {
          const byDate = toTime(b.created_at) - toTime(a.created_at);
          if (byDate) return byDate;
          return Number(b.id || 0) - Number(a.id || 0);
        })[0];
      }

      async function loadSessions(limit = 200) {
        return apiFetch(`/sessions?limit=${limit}`, { method: 'GET' });
      }

      async function resolveSessionId() {
        const fromUrl = getSessionIdFromUrl();
        const stored = localStorage.getItem('current_session_id');
        let sessions = null;
        try {
          sessions = await loadSessions();
        } catch {
          sessions = null;
        }

        if (fromUrl) {
          return { sessionId: fromUrl, sessions };
        }

        if (stored && sessions) {
          const match = sessions.find((s) => Number(s.id) === Number(stored));
          if (match && typeof match.overall_score === 'number') {
            return { sessionId: stored, sessions };
          }
        }

        const latest = pickLatestCompletedSession(sessions || []);
        return { sessionId: latest?.id || null, sessions };
      }

      // Load session metadata
      function sessionReadyForResults(sessionMeta) {
        if (!sessionMeta) return false;
        const stage = String(sessionMeta.stage || "").toLowerCase();
        if (stage === "wrapup" || stage === "done") return true;
        const asked = Number(sessionMeta.questions_asked_count || 0);
        const maxQ = Number(sessionMeta.max_questions || 0);
        return maxQ > 0 && asked >= maxQ;
      }

      async function loadSessionMeta(sessionId, sessionsOverride = null) {
        try {
          const sessions = sessionsOverride || (await loadSessions());
          const match = (sessions || []).find((s) => Number(s.id) === Number(sessionId));
          if (!match) return;

          document.getElementById('metaRole').textContent = match.role || '--';
          document.getElementById('metaCompany').textContent = formatCompanyStyle(match.company_style);
          document.getElementById('metaDifficulty').textContent = match.difficulty || '--';
          document.getElementById('metaStage').textContent = (match.stage || '').replaceAll('_', ' ') || '--';
          document.getElementById('metaQuestions').textContent =
            `${Number(match.questions_asked_count ?? 0)}/${Number(match.max_questions ?? 7)}`;

          document.getElementById('session_badge').innerHTML =
            `<i class="fas fa-hashtag"></i><span>Session #${sessionId}</span>`;
          return match;
        } catch (err) {
          console.warn('Failed to load session metadata:', err);
        }
      }

      // Update gauge animation
      function updateGauge(score) {
        const progress = document.querySelector('.gauge-progress');
        const scoreElement = document.getElementById('overall_score');
        const progressValue = 565 - (score / 100) * 565;

        if (progress) progress.style.strokeDashoffset = progressValue;
        if (scoreElement) scoreElement.textContent = Math.round(score);
      }

      // Render feedback items
      function renderFeedbackItems(selector, items, type) {
        const container = document.getElementById(selector);
        if (!container) return;

        container.innerHTML = '';

        if (!items || !items.length) {
          container.innerHTML = `
            <div class="empty-state">
              <i class="fas fa-info-circle"></i>
              <p>No ${type} data available</p>
            </div>
          `;
          return;
        }

        items.forEach((item, index) => {
          const itemElement = document.createElement('div');
          itemElement.className = `feedback-item ${type}`;
          itemElement.innerHTML = `
            <div class="feedback-icon">
              <i class="fas fa-${type === 'strength' ? 'check-circle' : type === 'weakness' ? 'exclamation-circle' : 'arrow-right'}"></i>
            </div>
            <div class="feedback-content">
              <div class="feedback-text">${escapeHtml(item)}</div>
            </div>
          `;
          container.appendChild(itemElement);
        });
      }

      // Update rating callout
      function updateRatingCallout(score) {
        const callout = document.getElementById('ratingCallout');
        const label = document.getElementById('ratingLabel');
        const text = document.getElementById('ratingText');

        let rating, tone;
        if (score >= 90) {
          rating = { label: 'Outstanding Performance', text: 'Elite range - keep the momentum!', tone: 'great' };
        } else if (score >= 80) {
          rating = { label: 'Great Performance', text: 'Strong interview showing. Fine-tune weak spots.', tone: 'good' };
        } else if (score >= 70) {
          rating = { label: 'Good Performance', text: 'Solid baseline. Focus on depth and edge cases.', tone: 'good' };
        } else if (score >= 55) {
          rating = { label: 'Needs Polish', text: 'You\'re close. Target rubric gaps.', tone: 'warn' };
        } else {
          rating = { label: 'Needs Focus', text: 'Refine fundamentals and practice pacing.', tone: 'danger' };
        }

        label.textContent = rating.label;
        text.textContent = rating.text;

        // Update callout styling
        callout.className = 'rating-callout ' + rating.tone;
      }

      // Copy summary to clipboard
      async function copySummary(data) {
        try {
          const summary = [
            `Interview Score: ${data?.overall_score || 0}/100`,
            `---`,
            `Rubric Breakdown:`,
            ...Object.entries(data?.rubric || {}).map(([k, v]) => `  ${k}: ${v}/10`),
            `---`,
            `Strengths:`,
            ...(data?.summary?.strengths || []).map(s => `  - ${s}`),
            `---`,
            `Weaknesses:`,
            ...(data?.summary?.weaknesses || []).map(w => `  - ${w}`),
            `---`,
            `Next Steps:`,
            ...(data?.summary?.next_steps || []).map(n => `  - ${n}`),
          ].join('\n');

          await navigator.clipboard.writeText(summary);
          alert('Summary copied to clipboard!');
        } catch (err) {
          console.error('Failed to copy summary:', err);
          alert('Failed to copy summary to clipboard');
        }
      }

      async function loadResultsData(primaryId, sessionsOverride) {
        if (!primaryId) throw new Error('Missing session id');
        try {
          const data = await apiFetch(`/analytics/sessions/${primaryId}/results`, { method: 'GET' });
          return { data, sessionId: primaryId, fallback: false };
        } catch (err) {
          const msg = String(err?.message || '').toLowerCase();
          const isNoEval = msg.includes('no evaluation') || msg.includes('not found');
          if (isNoEval) {
            let sessions = sessionsOverride;
            if (!sessions) {
              try {
                sessions = await loadSessions();
              } catch {
                sessions = null;
              }
            }
            const meta = (sessions || []).find((s) => Number(s.id) === Number(primaryId));
            if (sessionReadyForResults(meta)) {
              const subtitle = document.getElementById('resultsSubtitle');
              if (subtitle) {
                subtitle.textContent = 'Generating your results...';
              }
              try {
                await apiFetch(`/sessions/${primaryId}/finalize`, { method: 'POST' });
                const data = await apiFetch(`/analytics/sessions/${primaryId}/results`, { method: 'GET' });
                return { data, sessionId: primaryId, fallback: false };
              } catch (finalizeErr) {
                console.warn('Auto-finalize failed:', finalizeErr);
              }
            }
            if (!sessions) {
              try {
                sessions = await loadSessions();
              } catch {
                sessions = null;
              }
            }
            const latest = pickLatestCompletedSession(sessions || []);
            if (latest && Number(latest.id) !== Number(primaryId)) {
              const data = await apiFetch(`/analytics/sessions/${latest.id}/results`, { method: 'GET' });
              return { data, sessionId: latest.id, fallback: true };
            }
          }
          throw err;
        }
      }

      // Main initialization
      const { sessionId, sessions } = await resolveSessionId();
      if (!sessionId) {
        document.getElementById('resultsSubtitle').textContent = 'No completed sessions yet. Finish an interview to see results.';
        return;
      }

      // Load metadata
      const sessionMeta = await loadSessionMeta(sessionId, sessions);

      try {
        // Load results data
        const result = await loadResultsData(sessionId, sessions || (sessionMeta ? [sessionMeta] : null));
        const data = result.data;
        if (result.fallback) {
          loadSessionMeta(result.sessionId, sessions);
          document.getElementById('resultsSubtitle').textContent = `Showing latest completed session (#${result.sessionId}).`;
        }

        // Update UI with data
        updateGauge(data.overall_score || 0);
        updateRatingCallout(data.overall_score || 0);

        // Render charts and feedback
        renderRadar('#radarChart', data.rubric || {});
        renderRubricBars(data.rubric || {});
        renderFeedbackItems('strengths', data.summary?.strengths || [], 'strength');
        renderFeedbackItems('weaknesses', data.summary?.weaknesses || [], 'weakness');
        renderFeedbackItems('next_steps', data.summary?.next_steps || [], 'step');

        // Set up button handlers
        document.getElementById('btnCopySummary').addEventListener('click', () => copySummary(data));
        document.getElementById('btnOpenPerformance').addEventListener('click', () => {
          window.location.href = './dashboard.html#performance';
        });
        document.getElementById('btnNewSession').addEventListener('click', () => {
          window.location.href = './interview.html';
        });
        document.getElementById('btnExportPDF').addEventListener('click', () => {
          alert('PDF export feature coming soon!');
        });

      } catch (err) {
        console.error('Failed to load results:', err);
        const msg = String(err?.message || '');
        if (msg.toLowerCase().includes('no evaluation')) {
          document.getElementById('resultsSubtitle').textContent =
            'This session is not finalized yet. Click Submit & Evaluate to generate results.';
        } else {
          document.getElementById('resultsSubtitle').textContent = 'Failed to load results. Please try again.';
        }
      }

      // Logout handler
    document.getElementById("btn_logout").addEventListener("click", () => {
      localStorage.removeItem("token");
      localStorage.removeItem("current_session_id");
      window.location.href = "./login.html";
    });
  });
})();
