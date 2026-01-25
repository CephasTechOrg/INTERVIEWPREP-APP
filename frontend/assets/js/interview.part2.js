// Split from interview.js for maintainability (part: interview.part2.js)

async function maybeUpdateCurrentQuestion(nextId) {
  const id = Number(nextId || 0);
  if (!id) return;
  if (currentQuestionId && Number(currentQuestionId) === id) return;

  currentQuestionId = id;
  try {
    const q = await fetchQuestionById(id);
    renderCurrentQuestion(q);
  } catch (err) {
    renderCurrentQuestion({ id, title: `Question #${id}`, prompt: "" });
    showNotification(err?.message || "Failed to load current question.", "error");
  }
}

function clearCurrentQuestion() {
  currentQuestionId = null;
  renderCurrentQuestion(null);
}

function initQuestionPin() {
  const pin = qs("#questionPin");
  const btnCopy = qs("#copyQuestionBtn");
  const btnToggle = qs("#toggleQuestionBtn");
  const btnExpand = qs("#expandQuestionBtn");
  const body = qs("#questionPinBody");
  const prompt = qs("#currentQuestionPrompt");

  if (!pin || !btnToggle || !body) return;

  const setCollapsed = (collapsed) => {
    pin.classList.toggle("collapsed", !!collapsed);
    const icon = btnToggle.querySelector("i");
    if (icon) icon.className = collapsed ? "fas fa-chevron-down" : "fas fa-chevron-up";
    try {
      localStorage.setItem(QUESTION_PIN_COLLAPSED_KEY, collapsed ? "1" : "0");
    } catch {}
  };

  // Restore last state
  try {
    const saved = localStorage.getItem(QUESTION_PIN_COLLAPSED_KEY);
    if (saved === null || saved === undefined) {
      setCollapsed(true);
    } else {
      setCollapsed(saved === "1");
    }
  } catch {
    setCollapsed(true);
  }

  btnToggle.addEventListener("click", () => {
    setCollapsed(!pin.classList.contains("collapsed"));
  });

  btnCopy?.addEventListener("click", async () => {
    const t = qs("#currentQuestionTitle")?.textContent || "";
    const p = qs("#currentQuestionPrompt")?.textContent || "";
    const ok = await copyTextToClipboard(`${t}\n\n${p}`.trim());
    showNotification(ok ? "Question copied." : "Copy failed.", ok ? "success" : "error");
  });

  btnExpand?.addEventListener("click", () => {
    if (!prompt) return;
    const expanded = prompt.classList.toggle("expanded");
    btnExpand.title = expanded ? "Collapse" : "Expand";
    const icon = btnExpand.querySelector("i");
    if (icon) icon.className = expanded ? "fas fa-compress" : "fas fa-expand";
  });
}

function setInlineStatus(text) {
  const el = qs("#status");
  if (el) el.textContent = text;
}

function nowTimeLabel() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function timeLabelFromDate(value) {
  if (!value) return nowTimeLabel();
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return nowTimeLabel();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return nowTimeLabel();
  }
}

function roleToSender(role) {
  if (role === "interviewer") return "ai";
  if (role === "student") return "user";
  return "system";
}

function addMessage(text, sender, timeLabel = null) {
  const wrap = qs("#chatMessages");
  if (!wrap) return;

  const msg = document.createElement("div");
  const msgType = sender === "system" ? "ai system" : sender;
  msg.className = `message ${msgType}`;

  const interviewer = currentInterviewerProfile();
  const who = sender === "ai" ? (interviewer?.name || "Interviewer") : sender === "system" ? "System" : "You";
  const hasCode = String(text || "").includes("```");
  const bubbleCls = `message-bubble${hasCode ? " code" : ""}`;
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  if (sender === "ai") {
    applyAvatarElement(avatar, interviewer?.image_url || "", "", '<i class="fas fa-robot"></i>');
  } else if (sender === "user") {
    const profile = currentUserProfile() || {};
    const email = profile.email || getCurrentEmail() || "";
    const initials = initialsFromNameOrEmail(profile.full_name || "", email);
    const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
    applyAvatarElement(avatar, avatarUrl, initials, '<i class="fas fa-user"></i>');
  } else {
    avatar.innerHTML = '<i class="fas fa-circle-info"></i>';
  }

  const content = document.createElement("div");
  content.className = "message-content";

  const bubble = document.createElement("div");
  bubble.className = bubbleCls;
  bubble.textContent = text || "";

  const meta = document.createElement("div");
  meta.className = "message-time";
  meta.textContent = `${who} | ${timeLabel || nowTimeLabel()}`;

  content.appendChild(bubble);
  content.appendChild(meta);
  msg.appendChild(avatar);
  msg.appendChild(content);
  wrap.appendChild(msg);
  wrap.scrollTop = wrap.scrollHeight;

  if (sender === "user") {
    updateGuidanceFromUserMessage(text);
  }

  if (sender === "ai" && qs("#voiceToggle")?.checked) {
    // Browser auto-play policies block audio on fresh page loads. Defer until user interacts.
    if (hasUserActivation()) {
      speakWithBackendTts(text);
    } else {
      deferTts(text);
    }
  }

  if (sender === "ai") {
    lastAiMessage = text || "";
  }
}

function showTypingIndicator() {
  const wrap = qs("#chatMessages");
  if (!wrap) return;

  const t = document.createElement("div");
  t.className = "typing-indicator";
  t.id = "typingIndicator";
  t.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
  wrap.appendChild(t);
  wrap.scrollTop = wrap.scrollHeight;
}

function hideTypingIndicator() {
  const t = document.getElementById("typingIndicator");
  if (t) t.remove();
}

// Timer
let timerInterval = null;
let timerSeconds = 0;

function updateTimer() {
  const minutes = Math.floor(timerSeconds / 60);
  const seconds = timerSeconds % 60;
  const el = qs("#timer");
  if (el) el.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function startTimer() {
  stopTimer();
  timerSeconds = 0;
  updateTimer();
  timerInterval = setInterval(() => {
    timerSeconds += 1;
    updateTimer();
  }, 1000);
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
}

const PAGE_LINKS = {
  dashboard: "./dashboard.html",
  history: "./dashboard.html#history",
  performance: "./dashboard.html#performance",
  interview: "./interview.html",
  results: "./results.html",
  settings: "./settings.html",
};

function pageHasSection(page) {
  return !!qs(`#${page}Page`);
}

function goToPage(page) {
  const href = PAGE_LINKS[page];
  if (href) window.location.href = href;
}

function goToInterviewPage(sessionId) {
  const href = PAGE_LINKS.interview || "./interview.html";
  if (!sessionId) {
    window.location.href = href;
    return;
  }
  const url = new URL(href, window.location.href);
  url.searchParams.set("session_id", String(sessionId));
  window.location.href = url.toString();
}

function goToResultsPage(sessionId) {
  const href = PAGE_LINKS.results || "./results.html";
  if (!sessionId) {
    window.location.href = href;
    return;
  }
  const url = new URL(href, window.location.href);
  url.searchParams.set("session_id", String(sessionId));
  window.location.href = url.toString();
}

function navigateTo(page) {
  const pages = {
    dashboard: qs("#dashboardPage"),
    history: qs("#historyPage"),
    performance: qs("#performancePage"),
    interview: qs("#interviewPage"),
    results: qs("#resultsPage"),
  };

  if (page === "settings") {
    goToPage("settings");
    return;
  }
  if (!pages[page]) {
    goToPage(page);
    return;
  }

  Object.values(pages).forEach((p) => p?.classList.remove("active"));
  pages[page]?.classList.add("active");

  qsa(".nav-item").forEach((it) => it.classList.remove("active"));
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add("active");

  const titles = { dashboard: "Dashboard", history: "History", performance: "Performance", interview: "Live Interview", results: "Results & Analytics" };
  const titleEl = qs("#pageTitle span") || qs("#pageTitle");
  if (titleEl) titleEl.textContent = titles[page] || "Dashboard";

  if (page === "interview") startTimer();
  else stopTimer();

  document.body.classList.toggle("in-interview", page === "interview");

  if (page === "history") {
    refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
  }
  if (page === "performance") {
    if (sessionHistoryCache.length) renderPerformanceDashboard(sessionHistoryCache);
    else refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
  }
}

function roleToTrack(role) {
  const raw = String(role || "").trim().toLowerCase();
  if (raw === "swe intern") return "swe_intern";
  if (raw === "software engineer" || raw === "senior engineer" || raw === "senior software engineer") return "swe_engineer";
  if (raw === "cybersecurity") return "cybersecurity";
  if (raw === "data science") return "data_science";
  if (raw === "devops / cloud" || raw === "devops" || raw === "devops cloud") return "devops_cloud";
  if (raw === "product management") return "product_management";
  return "swe_engineer";
}

async function createSession({ role, company_style, difficulty, behavioral_questions_target, interviewer }) {
  const track = roleToTrack(role);
  const behavioral = Number(
    behavioral_questions_target ?? qs("#behavioralSelect")?.value ?? 2
  );
  return apiFetch("/sessions", {
    method: "POST",
    body: {
      role,
      track,
      company_style,
      difficulty,
      behavioral_questions_target: behavioral,
      interviewer: interviewer || undefined,
    },
  });
}

async function startInterview(sessionId) {
  const msg = await apiFetch(`/sessions/${sessionId}/start`, { method: "POST" });
  return msg;
}

async function sendToInterview(sessionId, text) {
  return apiFetch(`/sessions/${sessionId}/message`, {
    method: "POST",
    body: { content: text },
  });
}

async function finalizeInterview(sessionId) {
  return apiFetch(`/sessions/${sessionId}/finalize`, { method: "POST" });
}

async function loadResults(sessionId) {
  return apiFetch(`/analytics/sessions/${sessionId}/results`, { method: "GET" });
}

let sessionHistoryCache = [];

async function deleteSession(sessionId) {
  return apiFetch(`/sessions/${sessionId}`, { method: "DELETE" });
}

async function fetchSessions(limit = 50) {
  return apiFetch(`/sessions?limit=${encodeURIComponent(String(limit))}`, { method: "GET" });
}

async function fetchSessionMessages(sessionId, limit = 2000) {
  return apiFetch(`/sessions/${sessionId}/messages?limit=${encodeURIComponent(String(limit))}`, { method: "GET" });
}

async function fetchCoverage({ track, company_style, difficulty }) {
  const params = new URLSearchParams({
    track: String(track || ""),
    company_style: String(company_style || ""),
    difficulty: String(difficulty || ""),
    include_behavioral: "false",
  });
  return apiFetch(`/questions/coverage?${params.toString()}`, { method: "GET" });
}

function labelCompanyStyle(companyStyle) {
  const s = String(companyStyle || "general");
  if (s === "general") return "General";
  return s.slice(0, 1).toUpperCase() + s.slice(1);
}

function stageBadge(stage) {
  const s = String(stage || "").toLowerCase();
  if (s === "done") return { cls: "completed", text: "Completed" };
  if (s === "wrapup") return { cls: "pending", text: "Ready to finalize" };
  if (!s || s === "intro") return { cls: "pending", text: "Not started" };
  return { cls: "active", text: "In progress" };
}

function safeLocaleString(value) {
  if (!value) return "";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString();
  } catch {
    return "";
  }
}

const COVERAGE_TRACKS = new Set([
  "swe_intern",
  "swe_engineer",
  "behavioral",
  "cybersecurity",
  "data_science",
  "devops_cloud",
  "product_management",
]);
const COVERAGE_COMPANIES = new Set(["general", "amazon", "apple", "google", "microsoft", "meta"]);
const COVERAGE_DIFFICULTIES = new Set(["easy", "medium", "hard"]);

async function updateCoverageHint() {
  const hint = qs("#coverageHint");
  if (!hint) return;
  const role = qs("#roleSelect")?.value || "SWE Intern";
  const company_style = qs("#companySelect")?.value || "general";
  const difficulty = qs("#difficultySelect")?.value || "easy";
  const track = roleToTrack(role);

  hint.style.color = "var(--text-muted)";
  hint.textContent = "Checking question coverage...";
  if (
    !COVERAGE_TRACKS.has(track) ||
    !COVERAGE_COMPANIES.has(company_style) ||
    !COVERAGE_DIFFICULTIES.has(difficulty)
  ) {
    hint.textContent = "Coverage check unavailable.";
    return;
  }
  try {
    const data = await fetchCoverage({ track, company_style, difficulty });
    const count = Number(data?.count || 0);
    const fallback = Number(data?.fallback_general || 0);
    if (count > 0) {
      hint.textContent = `${count} ${labelCompanyStyle(company_style)} ${difficulty} questions available.`;
      return;
    }
    hint.style.color = "var(--danger)";
    hint.textContent = `No questions available for ${labelCompanyStyle(company_style)} ${difficulty}.`;
  } catch (err) {
    hint.style.color = "var(--text-muted)";
    hint.textContent = "Coverage check unavailable.";
  }
}

function renderSessionHistory(sessions) {
  const list = qs("#sessionHistoryList");
  if (!list) return;
  list.innerHTML = "";

  if (!sessions || !sessions.length) {
    list.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-box-open"></i>
        <h3>No Sessions Yet!</h3>
        <p>You haven't completed any interviews. Start one to see your history and track your progress.</p>
        <button class="btn btn-primary" onclick="navigateTo('dashboard')">Start First Interview</button>
      </div>
    `;
    return;
  }

  const activeId = Number(getSessionId() || 0);

  sessions.forEach((s) => {
    const row = document.createElement("div");
    row.className = "session-item";
    if (activeId && Number(s.id) === activeId) row.style.borderColor = "var(--primary-light)";

    const icon = document.createElement("div");
    icon.className = "session-icon";
    icon.innerHTML = '<i class="fas fa-comments"></i>';

    const main = document.createElement("div");
    main.className = "session-content";

    const title = document.createElement("div");
    title.className = "session-title";
    title.textContent = `Session #${s.id} - ${s.role || ""}`;

    const meta = document.createElement("div");
    meta.className = "session-meta";

    const metaBits = [];
    const company = labelCompanyStyle(s.company_style);
    const diff = String(s.difficulty || "");
    if (company || diff) metaBits.push(diff ? `${company} / ${diff}` : company);
    metaBits.push(`Q: ${Number(s.questions_asked_count || 0)}/${Number(s.max_questions || 7)}`);
    metaBits.push(`Behavioral: ${Number(s.behavioral_questions_target ?? 2)}`);
    if (typeof s.overall_score === "number") metaBits.push(`Score: ${s.overall_score}/100`);
    const when = safeLocaleString(s.created_at);
    if (when) metaBits.push(when);
    metaBits.forEach((item) => {
      const span = document.createElement("span");
      span.className = "session-meta-item";
      span.textContent = item;
      meta.appendChild(span);
    });

    main.appendChild(title);
    main.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "session-actions";

    const badge = stageBadge(s.stage);
    const badgeEl = document.createElement("span");
    badgeEl.className = `session-status ${badge.cls}`;
    badgeEl.textContent = badge.text;

    const resumeBtn = document.createElement("button");
    resumeBtn.type = "button";
    resumeBtn.className = "btn btn-outline";
    resumeBtn.dataset.action = "resume";
    resumeBtn.dataset.session = String(s.id);
    resumeBtn.innerHTML = '<i class="fas fa-play"></i> Resume';

    const resultsBtn = document.createElement("button");
    resultsBtn.type = "button";
    resultsBtn.className = "btn btn-outline";
    resultsBtn.dataset.action = "results";
    resultsBtn.dataset.session = String(s.id);
    resultsBtn.innerHTML = '<i class="fas fa-chart-line"></i> Results';

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-danger";
    deleteBtn.dataset.action = "delete";
    deleteBtn.dataset.session = String(s.id);
    deleteBtn.innerHTML = '<i class="fas fa-trash"></i> Delete';

    actions.appendChild(badgeEl);
    actions.appendChild(resumeBtn);
    actions.appendChild(resultsBtn);
    actions.appendChild(deleteBtn);

    row.appendChild(icon);
    row.appendChild(main);
    row.appendChild(actions);
    list.appendChild(row);
  });
}

// Debounced to prevent rapid API calls when multiple events trigger refresh
let _refreshSessionHistoryPending = false;
let _refreshSessionHistoryTimer = null;
async function refreshSessionHistory() {
  // If a call is pending, skip redundant calls
  if (_refreshSessionHistoryPending) return;
  
  // Debounce: coalesce rapid calls within 300ms
  if (_refreshSessionHistoryTimer) {
    clearTimeout(_refreshSessionHistoryTimer);
  }
  
  return new Promise((resolve) => {
    _refreshSessionHistoryTimer = setTimeout(async () => {
      _refreshSessionHistoryPending = true;
      const list = qs("#sessionHistoryList");
      if (list) list.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">Loading sessions...</div>`;
      try {
        const sessions = await fetchSessions(50);
        sessionHistoryCache = Array.isArray(sessions) ? sessions : [];
        renderSessionHistory(sessionHistoryCache);
        renderPerformanceDashboard(sessionHistoryCache);
      } catch (err) {
        const msg = err?.message || "Failed to load sessions.";
        if (list) list.innerHTML = `<div style="color: var(--danger); font-weight:600;">${escapeHtml(msg)}</div>`;
        showNotification(msg, "error");
      } finally {
        _refreshSessionHistoryPending = false;
      }
      resolve();
    }, 300);
  });
}

function pickLatestCompletedSession(sessions) {
  const list = Array.isArray(sessions) ? sessions : [];
  const completed = list.filter((s) => typeof s.overall_score === "number");
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

async function resolveResultsSessionId() {
  const current = getSessionId();
  if (current) return current;
  const cached = pickLatestCompletedSession(sessionHistoryCache);
  if (cached) return cached.id;
  try {
    const sessions = await fetchSessions(50);
    sessionHistoryCache = Array.isArray(sessions) ? sessions : [];
    const latest = pickLatestCompletedSession(sessionHistoryCache);
    return latest?.id || null;
  } catch {
    return null;
  }
}

async function openResultsView() {
  const sessionId = await resolveResultsSessionId();
  if (!pageHasSection("results")) {
    goToResultsPage(sessionId);
    return;
  }
  if (sessionId) {
    await handleLoadResultsAndNavigate(sessionId);
    return;
  }
  navigateTo("results");
  const subtitle = qs("#resultsSubtitle");
  if (subtitle) subtitle.textContent = "No completed sessions yet.";
}

function performanceStats(sessions) {
  const total = Array.isArray(sessions) ? sessions.length : 0;
  const completed = (sessions || []).filter((s) => typeof s.overall_score === "number");
  const scores = completed.map((s) => Number(s.overall_score || 0));
  const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
  const best = scores.length ? Math.max(...scores) : null;
  const completionRate = total ? Math.round((completed.length / total) * 100) : 0;
  const median =
    !scores.length
      ? null
      : (() => {
          const sorted = [...scores].sort((a, b) => a - b);
          const mid = Math.floor(sorted.length / 2);
          return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
        })();

  const sortByDate = (arr) =>
    [...arr].sort((a, b) => {
      const ad = new Date(a.created_at || 0).getTime();
      const bd = new Date(b.created_at || 0).getTime();
      return ad - bd;
    });

  const trend = sortByDate(completed).slice(-10).map((s) => ({
    score: Number(s.overall_score || 0),
    label: `#${s.id}`,
    when: s.created_at,
  }));

  const recent = sortByDate(completed).slice(-5).reverse();

  const last = sortByDate(completed).slice(-1)[0] || null;

  const byDifficulty = {};
  (sessions || []).forEach((s) => {
    const d = (s.difficulty || "unknown").toLowerCase();
    byDifficulty[d] = (byDifficulty[d] || 0) + 1;
  });

  const byStage = {};
  (sessions || []).forEach((s) => {
    const st = (s.stage || "unknown").toLowerCase();
    byStage[st] = (byStage[st] || 0) + 1;
  });

  const byBand = { "90-100": 0, "75-89": 0, "60-74": 0, "<60": 0 };
  scores.forEach((score) => {
    if (score >= 90) byBand["90-100"] += 1;
    else if (score >= 75) byBand["75-89"] += 1;
    else if (score >= 60) byBand["60-74"] += 1;
    else byBand["<60"] += 1;
  });

  // streak: consecutive days with at least one completed session, starting from latest day
  const daySet = new Set(
    completed.map((c) => {
      try {
        return new Date(c.created_at).toISOString().slice(0, 10);
      } catch {
        return null;
      }
    }).filter(Boolean)
  );
  let streak = 0;
  if (daySet.size) {
    const today = new Date();
    for (let i = 0; i < 365; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      if (daySet.has(key)) streak += 1;
      else break;
    }
  }

  return {
    total,
    completed: completed.length,
    avg,
    best,
    median,
    last,
    completionRate,
    trend,
    recent,
    byDifficulty,
    byStage,
    byBand,
    streak,
  };
}

function renderDifficultyChips(selector, mapObj) {
  const el = qs(selector);
  if (!el) return;
  el.innerHTML = "";
  const entries = Object.entries(mapObj || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No data yet.</div>`;
    return;
  }
  entries.forEach(([label, count]) => {
    const key = String(label || "unknown").toLowerCase();
    const display = key === "unknown" ? "unknown" : key.slice(0, 1).toUpperCase() + key.slice(1);
    const chip = document.createElement("div");
    chip.className = "difficulty-chip";
    if (key === "easy" || key === "medium" || key === "hard") {
      chip.classList.add(key);
    }
    chip.innerHTML = `
      <span class="chip-dot"></span>
      <span>${escapeHtml(display)}</span>
      <strong>${count}</strong>
    `;
    el.appendChild(chip);
  });
}

function renderScoreBands(selector, bandMap, total) {
  const el = qs(selector);
  if (!el) return;
  el.innerHTML = "";
  const entries = Object.entries(bandMap || {});
  if (!entries.length) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No data yet.</div>`;
    return;
  }
  const order = ["90-100", "75-89", "60-74", "<60"];
  const colorMap = {
    "90-100": "excellent",
    "75-89": "good",
    "60-74": "fair",
    "<60": "need-improvement",
  };
  order.forEach((label) => {
    const count = Number(bandMap?.[label] || 0);
    const pct = total ? Math.round((count / total) * 100) : 0;
    const row = document.createElement("div");
    row.className = "score-band";
    row.innerHTML = `
      <div class="band-label">
        <span class="band-color ${colorMap[label]}"></span>
        <span>${escapeHtml(label)}</span>
      </div>
      <div style="text-align:right;">
        <div class="band-count">${count}</div>
        <div class="band-percentage">${pct}%</div>
      </div>
    `;
    el.appendChild(row);
  });
}

function renderSparklineTrend(selector, points) {
  const el = qs(selector);
  if (!el) return;
  if (!points || !points.length) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No completed interviews yet.</div>`;
    return;
  }
  const width = 120;
  const height = 60;
  const maxScore = 100;
  const step = points.length > 1 ? width / (points.length - 1) : width;
  const coords = points.map((p, i) => {
    const score = Math.max(0, Math.min(maxScore, Number(p.score) || 0));
    const x = i * step;
    const y = height - (score / maxScore) * (height - 6);
    return { x, y, score };
  });
  const poly = coords.map((c) => `${c.x},${c.y}`).join(" ");
  const area = `${coords
    .map((c) => `${c.x},${c.y}`)
    .join(" ")} ${coords[coords.length - 1].x},${height} 0,${height}`;

  const svg = `
    <svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <polygon points="${area}" fill="rgba(37,99,235,0.12)"></polygon>
      <polyline points="${poly}" fill="none" stroke="var(--primary)" stroke-width="2"></polyline>
      ${coords
        .map((c, idx) => (idx === coords.length - 1 ? `<circle cx="${c.x}" cy="${c.y}" r="3.5"></circle>` : ""))
        .join("")}
    </svg>
  `;
  el.innerHTML = svg;
}

function renderRecentPerformance(list) {
  const wrap = qs("#perfRecentList");
  if (!wrap) return;
  wrap.innerHTML = "";
  if (!list || !list.length) {
    wrap.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No completed interviews yet.</div>`;
    return;
  }
  list.forEach((s) => {
    const row = document.createElement("div");
    row.className = "recent-item";

    const icon = document.createElement("div");
    icon.className = "recent-item-icon";
    icon.innerHTML = '<i class="fas fa-chart-line"></i>';

    const content = document.createElement("div");
    content.className = "recent-item-content";

    const title = document.createElement("div");
    title.className = "recent-item-title";
    title.textContent = `Session #${s.id} | ${s.role || ""}`;

    const meta = document.createElement("div");
    meta.className = "recent-item-meta";
    const stage = (s.stage || "").replaceAll("_", " ") || "unknown";
    const when = safeLocaleString(s.created_at) || "recent";
    const company = labelCompanyStyle(s.company_style);
    [stage, company, when].filter(Boolean).forEach((item) => {
      const span = document.createElement("span");
      span.textContent = item;
      meta.appendChild(span);
    });

    content.appendChild(title);
    content.appendChild(meta);

    const score = document.createElement("div");
    score.className = "recent-item-score";
    score.textContent = typeof s.overall_score === "number" ? `${s.overall_score}` : "--";

    const view = document.createElement("a");
    view.className = "btn btn-outline";
    view.href = `./results.html?session_id=${encodeURIComponent(s.id)}`;
    view.innerHTML = '<i class="fas fa-chart-line"></i> View';

    const actions = document.createElement("div");
    actions.className = "recent-item-actions";
    actions.appendChild(score);
    actions.appendChild(view);

    row.appendChild(icon);
    row.appendChild(content);
    row.appendChild(actions);
    wrap.appendChild(row);
  });
}

function renderPerformanceDashboard(sessions) {
  const stats = performanceStats(sessions);
  const setText = (id, val) => {
    const el = qs(id);
    if (el && val !== undefined && val !== null) el.textContent = val;
  };
  setText("#perfTotal", stats.total);
  setText("#perfCompleted", `${stats.completed} completed`);
  setText("#perfAverage", stats.avg !== null ? Math.round(stats.avg) : "--");
  setText("#perfBest", stats.best !== null ? Math.round(stats.best) : "--");
  setText("#perfBestLabel", stats.best !== null ? "Personal best" : "Complete an interview to see stats");
  setText("#perfCompletion", `${stats.completionRate}%`);
  const bar = qs("#perfCompletionBar");
  if (bar) bar.style.width = `${Math.min(100, Math.max(0, stats.completionRate))}%`;
  setText("#perfMedian", stats.median !== null ? Math.round(stats.median) : "--");
  if (stats.last) {
    setText("#perfLastScore", Math.round(Number(stats.last.overall_score || 0)));
    setText("#perfLastDate", safeLocaleString(stats.last.created_at) || "Most recent completed");
  } else {
    setText("#perfLastScore", "--");
    setText("#perfLastDate", "Complete an interview to see stats");
  }
  setText("#perfStreak", stats.streak ?? 0);

  renderSparklineTrend("#perfSparkline", stats.trend);
  renderDifficultyChips("#perfDifficulty", stats.byDifficulty);
  renderScoreBands("#perfBands", stats.byBand, stats.completed);
  renderRecentPerformance(stats.recent);
  renderDashboardQuickStats(stats);
}

function renderDashboardQuickStats(stats) {
  if (!stats) return;
  const setText = (selector, value) => {
    const el = qs(selector);
    if (el) el.textContent = value;
  };
  const setLastSession = (label, scoreText) => {
    const el = qs("#dashLastSession");
    if (!el) return;
    const safeLabel = escapeHtml(label || "");
    const safeScore = scoreText ? escapeHtml(scoreText) : "";
    if (!safeLabel) {
      el.textContent = "--";
      return;
    }
    el.innerHTML = safeScore
      ? `<span class="stat-value-primary">${safeLabel}</span><span class="stat-value-secondary">${safeScore}</span>`
      : `<span class="stat-value-primary">${safeLabel}</span>`;
  };
  const avgScore = stats.avg !== null ? Math.round(stats.avg) : "--";
  const bestScore = stats.best !== null ? Math.round(stats.best) : "--";
  const lastScore =
    stats.last && typeof stats.last.overall_score === "number"
      ? Math.round(Number(stats.last.overall_score || 0))
      : null;
  setText("#dashAvgScore", avgScore);
  setText("#dashDayStreak", stats.streak ?? 0);
  setText("#dashBestScore", bestScore);
  if (stats.last) {
    const dateLabel = safeLocaleString(stats.last.created_at) || "Recent";
    const scoreLabel = `Score: ${lastScore ?? "--"}/100`;
    setLastSession(dateLabel, scoreLabel);
  } else {
    setLastSession("No sessions yet", "");
  }
}
