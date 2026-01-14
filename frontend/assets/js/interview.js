function getSessionId() {
  return localStorage.getItem("current_session_id");
}

function setSessionId(id) {
  localStorage.setItem("current_session_id", String(id));
}

function clearSessionId() {
  localStorage.removeItem("current_session_id");
}

function showNotification(message, type = "info") {
  const area = document.getElementById("notificationArea");
  if (!area) return;

  const n = document.createElement("div");
  n.className = `notification ${type}`;

  const icon =
    type === "success"
      ? '<i class="fas fa-check-circle"></i>'
      : type === "error"
        ? '<i class="fas fa-triangle-exclamation"></i>'
        : '<i class="fas fa-circle-info"></i>';
  const title = type === "success" ? "Success" : type === "error" ? "Error" : "Info";

  n.innerHTML = `
    <div style="font-weight: 700; margin-bottom: 4px;">
      ${icon} ${title}
    </div>
    <div>${escapeHtml(message)}</div>
  `;

  area.appendChild(n);

  setTimeout(() => {
    n.style.animation = "slideIn 0.3s ease-out reverse";
    setTimeout(() => n.remove(), 300);
  }, 2800);
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

// UI state keys
const VOICE_TOGGLE_KEY = "tts_enabled";
const THEME_TOGGLE_KEY = "dark_theme";
const QUESTION_PIN_COLLAPSED_KEY = "question_pin_collapsed";
const SESSION_PREFS_KEY = "last_session_prefs";
const ROLE_OPTIONS = new Set(["SWE Intern", "Software Engineer", "Senior Engineer"]);
const COMPANY_OPTIONS = new Set(["general", "amazon", "google", "apple", "microsoft", "meta"]);
const DIFFICULTY_OPTIONS = new Set(["easy", "medium", "hard"]);
let lastAiMessage = "";
let currentTtsAudio = null;
let pendingTtsText = null;
let pendingTtsNoticeShown = false;
let ttsUnlockBound = false;
let manualUserActivation = false;

function hasUserActivation() {
  if (typeof document === "undefined") return true;
  if ("userActivation" in document) {
    return !!document.userActivation?.hasBeenActive;
  }
  return manualUserActivation;
}

function markUserActivation() {
  manualUserActivation = true;
}

if (typeof document !== "undefined") {
  document.addEventListener("pointerdown", markUserActivation, { once: true });
  document.addEventListener("keydown", markUserActivation, { once: true });
}

function bindTtsUnlock() {
  if (ttsUnlockBound) return;
  ttsUnlockBound = true;

  const handler = () => {
    if (!pendingTtsText) return;
    const text = pendingTtsText;
    pendingTtsText = null;
    ttsUnlockBound = false;
    document.removeEventListener("pointerdown", handler);
    document.removeEventListener("keydown", handler);
    if (typeof speakText === "function") {
      speakText(text);
    } else {
      speakWithBackendTts(text);
    }
  };

  document.addEventListener("pointerdown", handler, { once: true });
  document.addEventListener("keydown", handler, { once: true });
}

function deferTts(text) {
  const value = String(text || "").trim();
  if (!value) return;
  pendingTtsText = value;
  bindTtsUnlock();
  if (!pendingTtsNoticeShown) {
    pendingTtsNoticeShown = true;
    showNotification("Tap anywhere to enable audio output.", "info");
  }
}

function normalizeSessionPrefs(raw) {
  if (!raw || typeof raw !== "object") return null;
  const role = ROLE_OPTIONS.has(raw.role) ? raw.role : null;
  const company_style = COMPANY_OPTIONS.has(raw.company_style) ? raw.company_style : null;
  const difficulty = DIFFICULTY_OPTIONS.has(raw.difficulty) ? raw.difficulty : null;

  let behavioral = null;
  if (raw.behavioral_questions_target !== undefined) {
    behavioral = Number(raw.behavioral_questions_target);
  } else if (raw.behavioralSelect !== undefined) {
    behavioral = Number(raw.behavioralSelect);
  }
  if (Number.isNaN(behavioral)) behavioral = null;
  if (behavioral !== null) behavioral = Math.max(0, Math.min(3, behavioral));

  if (!role && !company_style && !difficulty && behavioral === null) return null;
  return { role, company_style, difficulty, behavioral_questions_target: behavioral };
}

function saveSessionPrefs(prefs) {
  try {
    const normalized = normalizeSessionPrefs(prefs);
    if (!normalized) return;
    localStorage.setItem(SESSION_PREFS_KEY, JSON.stringify(normalized));
  } catch {}
}

function loadSessionPrefs() {
  try {
    const raw = localStorage.getItem(SESSION_PREFS_KEY);
    return raw ? normalizeSessionPrefs(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function applySessionPrefs(prefs) {
  if (!prefs) return;
  if (prefs.role) {
    if (qs("#roleSelect")) qs("#roleSelect").value = prefs.role;
    if (qs("#interviewRole")) qs("#interviewRole").value = prefs.role;
  }
  if (prefs.company_style) {
    if (qs("#companySelect")) qs("#companySelect").value = prefs.company_style;
    if (qs("#interviewCompany")) qs("#interviewCompany").value = prefs.company_style;
  }
  if (prefs.difficulty) {
    if (qs("#difficultySelect")) qs("#difficultySelect").value = prefs.difficulty;
    if (qs("#interviewDifficulty")) qs("#interviewDifficulty").value = prefs.difficulty;
  }
  if (prefs.behavioral_questions_target !== null && prefs.behavioral_questions_target !== undefined) {
    if (qs("#behavioralSelect")) qs("#behavioralSelect").value = String(prefs.behavioral_questions_target);
  }
}

function readSessionPrefsFromUI() {
  const role = qs("#roleSelect")?.value || qs("#interviewRole")?.value || "SWE Intern";
  const company_style = qs("#companySelect")?.value || qs("#interviewCompany")?.value || "general";
  const difficulty = qs("#difficultySelect")?.value || qs("#interviewDifficulty")?.value || "easy";

  let behavioral_questions_target = null;
  if (qs("#behavioralSelect")) {
    behavioral_questions_target = Number(qs("#behavioralSelect")?.value ?? 2);
  } else {
    const stored = loadSessionPrefs();
    if (stored && stored.behavioral_questions_target !== null && stored.behavioral_questions_target !== undefined) {
      behavioral_questions_target = stored.behavioral_questions_target;
    }
  }
  if (behavioral_questions_target === null || Number.isNaN(behavioral_questions_target)) {
    behavioral_questions_target = 2;
  }
  behavioral_questions_target = Math.max(0, Math.min(3, behavioral_questions_target));

  return { role, company_style, difficulty, behavioral_questions_target };
}

// Best-effort voice playback:
// 1) Try backend TTS (ElevenLabs) and play the MP3.
// 2) Fall back to browser speech if audio is slow or blocked.
// 3) Avoid overlapping audio by stopping prior playback.
// 4) Respect the user voice toggle and never throw (silent fallback to text).
async function speakWithBackendTts(text) {
  const value = String(text || "").trim();
  if (!value) return;
  const toggle = qs("#voiceToggle");
  if (toggle && !toggle.checked) return;

  let played = false;
  // Wait a bit longer before falling back to browser speech so ElevenLabs has time to stream.
  const quickFallbackMs = 2000;

  const fallbackTimer = setTimeout(() => {
    if (!played) {
      played = true;
      speakText(value);
    }
  }, quickFallbackMs);

  const headers = { "Content-Type": "application/json" };
  try {
    const token = typeof getToken === "function" ? getToken() : null;
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } catch {
    // ignore auth lookup errors; fallback will handle
  }

  try {
    const res = await fetch(`${API_BASE}/tts`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text: value }),
    });
    const ctype = res.headers.get("content-type") || "";

    if (res.ok && ctype.startsWith("audio/")) {
      const blob = await res.blob();
      if (played) return; // already fell back; skip double audio
      clearTimeout(fallbackTimer);
      const url = URL.createObjectURL(blob);
      // Stop previous audio if playing to avoid overlap.
      if (currentTtsAudio) {
        try { currentTtsAudio.pause(); } catch {}
      }
      const audio = new Audio(url);
      currentTtsAudio = audio;
      played = true;
      audio.play()
        .then(() => {
          audio.onended = () => {
            currentTtsAudio = null;
            URL.revokeObjectURL(url);
          };
        })
        .catch(() => {
          currentTtsAudio = null;
          speakText(value); // autoplay blocked; fallback to speech synthesis
          URL.revokeObjectURL(url);
        });
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      return;
    }
  } catch {
    // ignore and fallback
  }

  if (!played) {
    clearTimeout(fallbackTimer);
    speakText(value);
  }
}

function stopVoicePlayback() {
  try { window.speechSynthesis.cancel(); } catch {}
  if (currentTtsAudio) {
    try { currentTtsAudio.pause(); } catch {}
    currentTtsAudio = null;
  }
}

async function copyTextToClipboard(text) {
  const value = String(text ?? "");
  if (!value) return false;
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = value;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      return true;
    } catch {
      return false;
    }
  }
}

let activeComposerTab = "text"; // "text" | "code" | "voice"

function getComposerTab() {
  return activeComposerTab || "text";
}

function setComposerTab(tab) {
  const next =
    tab === "code"
      ? "code"
      : tab === "voice"
        ? "voice"
        : tab === "text" || tab === "message"
          ? "text"
          : "text";
  activeComposerTab = next;

  const tabs = qsa(".input-tab");
  const chat = qs("#chatInput");
  const code = qs("#codeInput");
  const voicePanel = qs(".voice-input");
  const copyBtn = qs("#copyCodeBtn");
  const voiceBtn = qs("#voiceBtn");

  tabs.forEach((btn) => {
    const key = btn.dataset.tab || "text";
    btn.classList.toggle("active", key === next);
  });

  chat?.classList.toggle("hidden", next === "code");
  code?.classList.toggle("hidden", next !== "code");
  if (voicePanel) voicePanel.classList.toggle("hidden", next !== "voice");

  if (copyBtn) copyBtn.classList.toggle("hidden", next !== "code");
  if (voiceBtn) voiceBtn.disabled = next === "code";

  if (next === "code") code?.focus();
  else chat?.focus();
}

function wrapCodeBlock(code) {
  const raw = String(code || "").trim();
  if (!raw) return "";
  if (raw.startsWith("```")) return raw;
  return "```\n" + raw + "\n```";
}

function saveVoiceToggle(enabled) {
  try {
    localStorage.setItem(VOICE_TOGGLE_KEY, enabled ? "1" : "0");
  } catch {}
}

function loadVoiceToggle() {
  try {
    return localStorage.getItem(VOICE_TOGGLE_KEY) !== "0";
  } catch {
    return true;
  }
}

function saveThemeToggle(isDark) {
  try {
    localStorage.setItem(THEME_TOGGLE_KEY, isDark ? "1" : "0");
  } catch {}
}

function loadThemeToggle() {
  try {
    return localStorage.getItem(THEME_TOGGLE_KEY) === "1";
  } catch {
    return false;
  }
}

function applyTheme(isDark) {
  const html = document.documentElement;
  if (isDark) {
    html.setAttribute("data-theme", "dark");
  } else {
    html.setAttribute("data-theme", "light");
  }
}

function decodeJwtPayload(token) {
  try {
    const parts = String(token || "").split(".");
    if (parts.length < 2) return null;
    const b64 = parts[1].replaceAll("-", "+").replaceAll("_", "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const json = atob(padded);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function getCurrentEmail() {
  const token = getToken?.();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  const email = payload?.sub;
  return typeof email === "string" ? email : null;
}

function profileKey(email) {
  return `user_profile_${String(email || "").toLowerCase()}`;
}

function loadLocalProfile(email) {
  try {
    const raw = localStorage.getItem(profileKey(email));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveLocalProfile(email, profile) {
  try {
    localStorage.setItem(profileKey(email), JSON.stringify({ ...profile, email, updated_at: Date.now() }));
  } catch {}
}

function initialsFromNameOrEmail(fullName, email) {
  const base = (fullName || "").trim() || (email || "").split("@")[0] || "";
  const parts = base
    .replaceAll(".", " ")
    .replaceAll("_", " ")
    .split(/\s+/)
    .filter(Boolean);
  const a = parts[0]?.[0] || "U";
  const b = parts[1]?.[0] || "";
  return (a + b).toUpperCase();
}

function setSessionBadge(text, active) {
  const badgeText = qs("#sessionBadgeText");
  const badge = qs("#sessionBadge");
  const dot = badge?.querySelector(".status-dot");
  if (badgeText) badgeText.textContent = text;
  if (badge) {
    badge.classList.add("status-badge");
    badge.classList.remove("success", "warning", "danger", "primary");
    if (active) badge.classList.add("success");
  }
  if (dot) dot.classList.toggle("inactive", !active);
}

function setInterviewStatus(text, active) {
  const statusText = qs("#sessionStatusText") || qs("#sessionStatus");
  const dot = qs("#sessionDot") || qs("#sessionStatus .status-indicator");
  if (statusText) statusText.textContent = text;
  if (dot) dot.classList.toggle("inactive", !active);
}

function setAiBadge(status) {
  const badge = qs("#aiBadge");
  const text = qs("#aiBadgeText");
  if (!badge || !text) return;

  const s = status || {};
  const state = String(s.status || "unknown").toLowerCase();
  const configured = !!s.configured;
  const fallback = !!s.fallback_mode;

  let cls = "primary";
  let label = "AI: Checking...";

  if (state === "online") {
    cls = "success";
    label = "AI: Online";
  } else if (state === "offline") {
    cls = "danger";
    label = configured ? "AI: Offline (Fallback)" : "AI: Offline (No key)";
  } else {
    cls = fallback ? "warning" : "primary";
    label = configured ? "AI: Checking..." : "AI: Offline (No key)";
  }

  badge.classList.add("status-badge");
  badge.classList.remove("success", "warning", "danger", "primary", "ai-status");
  badge.classList.add(cls);
  if (cls === "primary") badge.classList.add("ai-status");
  text.textContent = label;
  badge.title = s.last_error ? `Last AI error: ${s.last_error}` : "AI status";
}

async function refreshAiStatus() {
  try {
    const data = await apiFetch("/ai/status", { method: "GET" });
    setAiBadge(data);
    return data;
  } catch {
    setAiBadge({ status: "unknown", configured: true, fallback_mode: true, last_error: "Status check failed" });
    return null;
  }
}

let currentQuestionId = null;
let currentQuestionIsBehavioral = false;

const FLOW_STEPS = [
  { key: "plan", label: "Plan" },
  { key: "solve", label: "Solve" },
  { key: "optimize", label: "Optimize" },
  { key: "validate", label: "Validate" },
];

const FOCUS_TARGETS = [
  { key: "plan", label: "Approach" },
  { key: "constraints", label: "Constraints" },
  { key: "complexity", label: "Complexity" },
  { key: "edge", label: "Edge cases" },
  { key: "correctness", label: "Correctness" },
];

const FLOW_SIGNALS = {
  plan: ["approach", "plan", "strategy", "idea", "high level", "overall"],
  solve: ["implement", "implementation", "code", "pseudocode", "steps", "loop", "iterate", "recursion", "dfs", "bfs"],
  optimize: ["optimize", "improve", "reduce", "complexity", "big o", "big-o", "time complexity", "space complexity"],
  validate: ["edge", "corner", "test", "verify", "validate", "correct", "proof", "invariant"],
};

const FOCUS_SIGNALS = {
  plan: ["approach", "plan", "strategy", "idea", "high level", "overall"],
  constraints: ["constraint", "constraints", "assume", "assumption", "bounds", "input size", "n up to", "limit"],
  complexity: ["complexity", "big o", "big-o", "time complexity", "space complexity"],
  edge: ["edge", "corner", "empty", "null", "single", "duplicate", "overflow", "negative", "zero"],
  correctness: ["correct", "correctness", "proof", "prove", "invariant", "guarantee", "why this works"],
};

let flowState = initFlowState();
let focusState = initFocusState();

function initFlowState() {
  return { plan: false, solve: false, optimize: false, validate: false };
}

function initFocusState() {
  return { plan: false, constraints: false, complexity: false, edge: false, correctness: false };
}

function resetGuidanceState() {
  flowState = initFlowState();
  focusState = initFocusState();
  renderFlowRail();
  renderFocusTargets();
}

function updateGuidanceVisibility(hasQuestion) {
  const guide = qs("#questionGuide") || qs("#flowCard") || qs(".guidance-card");
  const hide = !hasQuestion || currentQuestionIsBehavioral;
  if (guide) guide.classList.toggle("hidden", hide);
}

function setQuestionContext(question) {
  const tags = Array.isArray(question?.tags) ? question.tags.map((t) => String(t).toLowerCase()) : [];
  currentQuestionIsBehavioral = tags.includes("behavioral");
  resetGuidanceState();
  updateGuidanceVisibility(!!question);
}

function textHasAny(text, terms) {
  return terms.some((term) => text.includes(term));
}

function renderFlowRail() {
  const rail = qs("#flowRail") || qs(".flow-steps");
  if (!rail) return;
  let activeSet = false;
  FLOW_STEPS.forEach((step) => {
    const el = rail.querySelector(`[data-step="${step.key}"]`);
    if (!el) return;
    const done = !!flowState[step.key];
    el.classList.toggle("done", done);
    const active = !done && !activeSet;
    el.classList.toggle("active", active);
    if (active) activeSet = true;
  });

  const subtitle = qs("#flowSubtitle");
  if (subtitle) {
    const next = FLOW_STEPS.find((step) => !flowState[step.key]);
    if (!next) subtitle.textContent = "Flow complete. Keep it crisp and confident.";
    else if (next.key === "plan") subtitle.textContent = "Start with your plan and approach.";
    else subtitle.textContent = `Next up: ${next.label.toLowerCase()}.`;
  }
}

function renderFocusTargets() {
  const chips = qs("#focusChips");
  if (!chips) return;
  chips.innerHTML = "";
  const missing = FOCUS_TARGETS.filter((target) => !focusState[target.key]);

  missing.forEach((target) => {
    const chip = document.createElement("span");
    chip.className = "focus-chip";
    if (target.key === "complexity" || target.key === "edge") chip.classList.add("critical");
    chip.textContent = target.label;
    chips.appendChild(chip);
  });

  const empty = qs("#focusEmpty");
  if (empty) empty.classList.toggle("hidden", missing.length !== 0);

  const subtitle = qs("#focusSubtitle");
  if (subtitle) {
    subtitle.textContent = missing.length
      ? `Missing ${missing.length} key area${missing.length === 1 ? "" : "s"}.`
      : "You are covering the key follow-ups.";
  }
}

function updateGuidanceFromUserMessage(text) {
  const value = String(text || "").trim();
  if (!value || currentQuestionIsBehavioral) return;

  const lower = value.toLowerCase();
  const hasBigO = /\bo\([^)]*\)/i.test(value);

  if (value.includes("```")) flowState.solve = true;

  if (!flowState.plan && textHasAny(lower, FLOW_SIGNALS.plan)) flowState.plan = true;
  if (!flowState.solve && textHasAny(lower, FLOW_SIGNALS.solve)) flowState.solve = true;
  if (!flowState.optimize && (textHasAny(lower, FLOW_SIGNALS.optimize) || hasBigO)) flowState.optimize = true;
  if (!flowState.validate && textHasAny(lower, FLOW_SIGNALS.validate)) flowState.validate = true;

  if (textHasAny(lower, FOCUS_SIGNALS.plan)) focusState.plan = true;
  if (textHasAny(lower, FOCUS_SIGNALS.constraints)) focusState.constraints = true;
  if (textHasAny(lower, FOCUS_SIGNALS.complexity) || hasBigO) focusState.complexity = true;
  if (textHasAny(lower, FOCUS_SIGNALS.edge)) focusState.edge = true;
  if (textHasAny(lower, FOCUS_SIGNALS.correctness)) focusState.correctness = true;

  renderFlowRail();
  renderFocusTargets();
}

async function fetchQuestionById(questionId) {
  const id = Number(questionId || 0);
  if (!id) return null;
  return apiFetch(`/questions/${id}`, { method: "GET" });
}

function renderCurrentQuestion(question) {
  const title = qs("#currentQuestionTitle");
  const meta = qs("#currentQuestionMeta");
  const prompt = qs("#currentQuestionPrompt");

  if (!title || !meta || !prompt) return;

  if (!question) {
    title.textContent = "No active question";
    meta.textContent = "Start a session to load a question.";
    prompt.textContent = "";
    setQuestionContext(null);
    return;
  }

  title.textContent = question.title || `Question #${question.id}`;
  const tags = Array.isArray(question.tags) && question.tags.length ? question.tags.join(", ") : "";
  const bits = [];
  if (question.difficulty) bits.push(`Difficulty: ${question.difficulty}`);
  if (tags) bits.push(`Tags: ${tags}`);
  meta.textContent = bits.join(" | ") || " ";
  prompt.textContent = question.prompt || "";
  setQuestionContext(question);
}

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
    if (icon) icon.className = expanded ? "fas fa-up-down-left-right" : "fas fa-up-down";
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

  const who = sender === "ai" ? "Interviewer" : sender === "system" ? "System" : "You";
  const hasCode = String(text || "").includes("```");
  const bubbleCls = `message-bubble${hasCode ? " code" : ""}`;
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  if (sender === "ai") avatar.innerHTML = '<i class="fas fa-robot"></i>';
  else if (sender === "user") avatar.innerHTML = '<i class="fas fa-user"></i>';
  else avatar.innerHTML = '<i class="fas fa-circle-info"></i>';

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
    refreshSessionHistory().catch(() => {});
  }
  if (page === "performance") {
    if (sessionHistoryCache.length) renderPerformanceDashboard(sessionHistoryCache);
    else refreshSessionHistory().catch(() => {});
  }
}

async function createSession({ role, company_style, difficulty, behavioral_questions_target }) {
  const track = role === "SWE Intern" ? "swe_intern" : "swe_engineer";
  const behavioral = Number(
    behavioral_questions_target ?? qs("#behavioralSelect")?.value ?? 2
  );
  return apiFetch("/sessions", {
    method: "POST",
    body: { role, track, company_style, difficulty, behavioral_questions_target: behavioral },
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

const COVERAGE_TRACKS = new Set(["swe_intern", "swe_engineer", "behavioral"]);
const COVERAGE_COMPANIES = new Set(["general", "amazon", "apple", "google", "microsoft", "meta"]);
const COVERAGE_DIFFICULTIES = new Set(["easy", "medium", "hard"]);

async function updateCoverageHint() {
  const hint = qs("#coverageHint");
  if (!hint) return;
  const role = qs("#roleSelect")?.value || "SWE Intern";
  const company_style = qs("#companySelect")?.value || "general";
  const difficulty = qs("#difficultySelect")?.value || "easy";
  const track = role === "SWE Intern" ? "swe_intern" : "swe_engineer";

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
    if (fallback > 0) {
      hint.style.color = "var(--warning)";
      hint.textContent = `No ${labelCompanyStyle(company_style)} ${difficulty} questions. We'll use General instead.`;
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
    list.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No sessions yet. Start one above.</div>`;
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

async function refreshSessionHistory() {
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
  }
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

function setComposerEnabled(enabled) {
  const on = !!enabled;
  const tab = getComposerTab();
  const input = qs("#chatInput");
  const code = qs("#codeInput");
  const tabs = qsa(".input-tab");
  const copyCode = qs("#copyCodeBtn");
  const send = qs("#sendBtn");
  const voice = qs("#voiceBtn");
  if (input) input.disabled = !on;
  if (code) code.disabled = !on;
  tabs.forEach((btn) => {
    btn.disabled = !on;
  });
  if (copyCode) copyCode.disabled = !on;
  if (send) send.disabled = !on;
  if (voice) voice.disabled = !on || tab === "code";
}

function openSettingsDrawer() {
  qs("#settingsDrawer")?.classList.add("open");
}

function closeSettingsDrawer() {
  qs("#settingsDrawer")?.classList.remove("open");
}

function toggleMobileMenu() {
  const sidebar = qs("#sidebar");
  const overlay = qs("#sidebarOverlay");
  if (!sidebar || !overlay) return;
  const isActive = sidebar.classList.contains("active");
  if (isActive) {
    closeMobileMenu();
  } else {
    sidebar.classList.add("active");
    overlay.classList.add("active");
  }
}

function closeMobileMenu() {
  qs("#sidebar")?.classList.remove("active");
  qs("#sidebarOverlay")?.classList.remove("active");
}

async function resumeSessionById(sessionId) {
  const id = Number(sessionId);
  if (!id) return;

  let startedNewSession = false;

  if (!pageHasSection("interview")) {
    setSessionId(id);
    goToInterviewPage(id);
    return;
  }

  let info = (sessionHistoryCache || []).find((x) => Number(x.id) === id);
  if (!info) {
    try {
      const sessions = await fetchSessions(200);
      sessionHistoryCache = sessions || [];
      info = sessionHistoryCache.find((x) => Number(x.id) === id);
    } catch {}
  }
  const stage = String(info?.stage || "").toLowerCase();
  const isDone = stage === "done";
  const isWrapup = stage === "wrapup";
  if (info) {
    if (qs("#roleSelect")) qs("#roleSelect").value = info.role || "SWE Intern";
    if (qs("#companySelect")) qs("#companySelect").value = info.company_style || "general";
    if (qs("#difficultySelect")) qs("#difficultySelect").value = info.difficulty || "easy";
    if (qs("#behavioralSelect")) qs("#behavioralSelect").value = String(info.behavioral_questions_target ?? 2);
    syncInterviewSelectorsFromDashboard();
  } else {
    applySessionPrefs(loadSessionPrefs());
  }

  setSessionId(id);
  setSessionBadge(`Session #${id}`, true);
  navigateTo("interview");
  setInterviewStatus("Resuming session...", true);
  setInlineStatus("Loading messages...");
  setComposerEnabled(!(isDone || isWrapup));

  qs("#chatMessages").innerHTML = "";

  try {
    const msgs = await fetchSessionMessages(id, 2000);
    if (!msgs.length) {
      if (info && String(info.stage || "").toLowerCase() === "done") {
        addMessage("This session is completed. View Results or start a New Session.", "system");
      } else {
        // If the session never started, start it now so the user sees the first question.
        const first = await startInterview(id);
        addMessage(first.content, roleToSender(first?.role));
        if (first?.current_question_id) {
          maybeUpdateCurrentQuestion(first.current_question_id).catch(() => {});
        }
        startedNewSession = true;
      }
    } else {
      msgs.forEach((m) => {
        const sender = roleToSender(m.role);
        addMessage(m.content, sender, timeLabelFromDate(m.created_at));
      });
    }

    if (info && String(info.stage || "").toLowerCase() === "done") {
      addMessage("This session is completed. Start a New Session to practice again.", "system");
      setInterviewStatus("Completed (view results)", true);
      setInlineStatus("Session completed. View Results or start a New Session.");
    } else if (info && String(info.stage || "").toLowerCase() === "wrapup") {
      addMessage("This session is ready to finalize. Click Submit & Evaluate to generate results.", "system");
      setInterviewStatus("Ready to finalize", true);
      setInlineStatus("Ready to finalize. Submit & Evaluate to score this session.");
    } else {
      setInterviewStatus("Waiting for your response", true);
      setInlineStatus(
        startedNewSession
          ? "Interview started. Reply with your approach and code."
          : "Session resumed. Continue the conversation."
      );
    }
    if (!startedNewSession && info?.current_question_id) {
      maybeUpdateCurrentQuestion(info.current_question_id).catch(() => {});
    }
    refreshAiStatus().catch(() => {});
    qs("#chatInput")?.focus();
    refreshSessionHistory().catch(() => {});
  } catch (err) {
    const msg = err?.message || "Failed to load session messages.";
    addMessage(msg, "system");
    showNotification(msg, "error");
    setInterviewStatus("Error (check message)", true);
    setInlineStatus(msg);
  }
}

async function handleDeleteSession(sessionId) {
  const id = Number(sessionId);
  if (!id) return;

  const confirmed = window.confirm(
    `Delete Session #${id}?\n\nThis permanently removes the transcript and score from your database.`
  );
  if (!confirmed) return;

  try {
    await deleteSession(id);
    showNotification(`Session #${id} deleted.`, "success");

    if (String(getSessionId() || "") === String(id)) {
      clearSessionId();
      clearCurrentQuestion();
      setSessionBadge("No Active Session", false);
      setInterviewStatus("Ready to Start", false);
      setInlineStatus("Session deleted.");
      setComposerEnabled(false);
      if (qs("#chatMessages")) qs("#chatMessages").innerHTML = "";
    }

    refreshSessionHistory().catch(() => {});
  } catch (err) {
    const msg = err?.message || "Failed to delete session.";
    showNotification(msg, "error");
  }
}

async function handleStartFromDashboard() {
  const prefs = readSessionPrefsFromUI();
  const role = prefs.role;
  const company_style = prefs.company_style;
  const difficulty = prefs.difficulty;
  const behavioral_questions_target = prefs.behavioral_questions_target;
  saveSessionPrefs(prefs);

  showNotification("Starting interview session...", "info");
  setInlineStatus("Creating session...");

  const s = await createSession({ role, company_style, difficulty, behavioral_questions_target });
  setSessionId(s.id);

  if (!pageHasSection("interview")) {
    goToInterviewPage(s.id);
    return;
  }

  setSessionBadge(`Session #${s.id}`, true);
  setInlineStatus("Starting interview...");

  navigateTo("interview");
  setInterviewStatus("Interview in progress", true);
  setComposerEnabled(true);
  qs("#chatMessages").innerHTML = "";

  const msg = await startInterview(s.id);
  addMessage(msg.content, roleToSender(msg?.role));
  maybeUpdateCurrentQuestion(msg.current_question_id).catch(() => {});
  refreshAiStatus().catch(() => {});
  setInlineStatus("Interview started. Reply with your approach and code.");
  showNotification("Interview session started!", "success");

  syncInterviewSelectorsFromDashboard();
  refreshSessionHistory().catch(() => {});
  qs("#chatInput")?.focus();
}

function syncInterviewSelectorsFromDashboard() {
  const role = qs("#roleSelect")?.value;
  const company_style = qs("#companySelect")?.value;
  const difficulty = qs("#difficultySelect")?.value;

  if (role && qs("#interviewRole")) qs("#interviewRole").value = role;
  if (company_style && qs("#interviewCompany")) qs("#interviewCompany").value = company_style;
  if (difficulty && qs("#interviewDifficulty")) qs("#interviewDifficulty").value = difficulty;
  saveSessionPrefs({
    role,
    company_style,
    difficulty,
    behavioral_questions_target: Number(qs("#behavioralSelect")?.value ?? 2),
  });
  updateCoverageHint().catch(() => {});
}

function syncDashboardSelectorsFromInterview() {
  const role = qs("#interviewRole")?.value;
  const company_style = qs("#interviewCompany")?.value;
  const difficulty = qs("#interviewDifficulty")?.value;

  if (role && qs("#roleSelect")) qs("#roleSelect").value = role;
  if (company_style && qs("#companySelect")) qs("#companySelect").value = company_style;
  if (difficulty && qs("#difficultySelect")) qs("#difficultySelect").value = difficulty;
  saveSessionPrefs({
    role,
    company_style,
    difficulty,
    behavioral_questions_target: Number(qs("#behavioralSelect")?.value ?? 2),
  });
  updateCoverageHint().catch(() => {});
}

async function handleSendMessage() {
  const sessionId = getSessionId();
  if (!sessionId) {
    showNotification("No active session. Start one from Dashboard.", "error");
    setInlineStatus("No active session. Start one from Dashboard.");
    return;
  }

  const tab = getComposerTab();
  const input = qs("#chatInput");
  const codeInput = qs("#codeInput");

  let text = "";
  if (tab === "code") {
    text = wrapCodeBlock((codeInput?.value || "").trim());
    if (!text) return;
  } else {
    text = (input?.value || "").trim();
    if (!text) return;
  }

  addMessage(text, "user");
  if (tab === "code") {
    if (codeInput) codeInput.value = "";
  } else {
    if (input) input.value = "";
  }

  showTypingIndicator();
  setInterviewStatus("AI is responding...", true);

  try {
    const reply = await sendToInterview(sessionId, text);
    hideTypingIndicator();
    addMessage(reply.content, "ai");
    maybeUpdateCurrentQuestion(reply.current_question_id).catch(() => {});
    refreshAiStatus().catch(() => {});
    setInterviewStatus("Waiting for your response", true);
  } catch (err) {
    hideTypingIndicator();
    const msg = err?.message || "AI service error.";
    addMessage(msg, "system");
    showNotification(msg, "error");
    refreshAiStatus().catch(() => {});
    setInterviewStatus("Error (check message)", true);
  }
}

async function handleFinalize() {
  const sessionId = getSessionId();
  if (!sessionId) {
    showNotification("No session to submit.", "error");
    return;
  }

  showNotification("Submitting interview for evaluation...", "info");
  setInlineStatus("Finalizing & scoring (this may take a moment)...");

  try {
    await finalizeInterview(sessionId);
    refreshAiStatus().catch(() => {});
    showNotification("Interview submitted! Loading results...", "success");
    setInterviewStatus("Completed (view results)", true);
    refreshSessionHistory().catch(() => {});
    await handleLoadResultsAndNavigate(sessionId);
  } catch (err) {
    const msg = err?.message || "AI service error.";
    addMessage(msg, "system");
    showNotification(msg, "error");
    refreshAiStatus().catch(() => {});
  }
}

async function handleLoadResultsAndNavigate(sessionId) {
  if (!pageHasSection("results")) {
    goToResultsPage(sessionId);
    return;
  }
  if (!sessionId) {
    navigateTo("results");
    const subtitle = qs("#resultsSubtitle");
    if (subtitle) subtitle.textContent = "No completed sessions yet.";
    return;
  }
  navigateTo("results");

  const subtitle = qs("#resultsSubtitle");
  if (subtitle) subtitle.textContent = `Session #${sessionId}`;

  qs("#overall_score").textContent = "0";
  const overallText = qs("#overallScoreText");
  if (overallText) overallText.textContent = "0";
  qs("#rubric_wrap").innerHTML = "";
  qs("#strengths").innerHTML = "";
  qs("#weaknesses").innerHTML = "";
  qs("#next_steps").innerHTML = "";

  try {
    const data = await loadResults(sessionId);
    const scoreVal = data.overall_score ?? 0;
    qs("#overall_score").textContent = scoreVal;
    if (overallText) overallText.textContent = scoreVal;
    renderRubricBars(data.rubric || {});
    renderList("#strengths", data.summary?.strengths || []);
    renderList("#weaknesses", data.summary?.weaknesses || []);
    renderList("#next_steps", data.summary?.next_steps || []);
  } catch (err) {
    const msg = err?.message || "Failed to load results.";
    const fail = `<div style="color: var(--danger); font-weight:600;">${escapeHtml(msg)}</div>`;
    qs("#rubric_wrap").innerHTML = fail;
    qs("#strengths").innerHTML = fail;
    qs("#weaknesses").innerHTML = fail;
    qs("#next_steps").innerHTML = fail;
    showNotification(msg, "error");
  }
}

function handleEndSession() {
  clearSessionId();
  clearCurrentQuestion();
  setSessionBadge("No Active Session", false);
  setInterviewStatus("Ready to Start", false);
  setInlineStatus("Session ended.");
  showNotification("Session ended", "info");
  stopVoicePlayback();
  navigateTo("dashboard");
}

function handleReplayLast() {
  if (!lastAiMessage || !lastAiMessage.trim()) {
    showNotification("No interviewer response to replay yet.", "error");
    return;
  }
  stopVoicePlayback();
  speakWithBackendTts(lastAiMessage);
}

function initNav() {
  qsa(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const page = item.getAttribute("data-page");
      if (page === "settings") {
        goToPage("settings");
        return;
      }
      if (page === "results") {
        openResultsView().catch(() => navigateTo("results"));
        return;
      }
      navigateTo(page);
    });
  });
}

function initShortcuts() {
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "n") {
      e.preventDefault();
      handleStartFromDashboard().catch((err) => showNotification(err?.message || "Failed to start session", "error"));
    }
  });
}

  // Apply saved theme on load
  const savedTheme = loadThemeToggle();
  applyTheme(savedTheme);

document.addEventListener("DOMContentLoaded", async () => {
  requireAuthOrRedirect();

  function updateAvatarFromProfile() {
    const email = getCurrentEmail();
    const avatar = qs("#userAvatar");
    if (!avatar) return;

    if (!email) {
      avatar.textContent = "";
      avatar.innerHTML = `<i class="fas fa-user"></i>`;
      return;
    }

    const profile = loadLocalProfile(email) || { email, full_name: "" };
    const initials = initialsFromNameOrEmail(profile.full_name, email);
    avatar.textContent = initials;
    avatar.title = profile.full_name ? `${profile.full_name} (${email})` : email;
  }

  function ensureProfileDefaults(email) {
    if (!email) return null;
    let profile = loadLocalProfile(email);
    if (!profile) {
      const guessName = email.split("@")[0].replaceAll(".", " ").replaceAll("_", " ");
      profile = {
        email,
        full_name: guessName ? guessName.replace(/\b\w/g, (c) => c.toUpperCase()) : "",
        role_pref: "SWE Intern",
      };
      saveLocalProfile(email, profile);
    }
    if (!profile.role_pref) {
      profile.role_pref = "SWE Intern";
      saveLocalProfile(email, profile);
    }
    return profile;
  }

  function renderDashboardProfile(profile) {
    if (!profile) return;
    const name = (profile.full_name || "").trim();
    const nameEl = qs("#dashProfileName");
    const emailEl = qs("#dashProfileEmail");
    const roleEl = qs("#dashRolePref");
    if (nameEl) nameEl.textContent = name || initialsFromNameOrEmail("", profile.email);
    if (emailEl) emailEl.textContent = profile.email || "-";
    if (roleEl) roleEl.textContent = profile.role_pref || "SWE Intern";
    if (sessionHistoryCache.length) renderPerformanceDashboard(sessionHistoryCache);
    else refreshSessionHistory().catch(() => {});
  }

  function applyRolePrefToSelectors(profile) {
    if (!profile) return;
    if (qs("#roleSelect")) qs("#roleSelect").value = profile.role_pref || "SWE Intern";
    if (qs("#interviewRole")) qs("#interviewRole").value = profile.role_pref || "SWE Intern";
  }

  initNav();
  initShortcuts();
  initQuestionPin();
  refreshAiStatus().catch(() => {});
  window.setInterval(() => refreshAiStatus().catch(() => {}), 15000);

  const voiceToggle = qs("#voiceToggle");
  if (voiceToggle) {
    const saved = loadVoiceToggle();
    voiceToggle.checked = saved;
    voiceToggle.addEventListener("change", () => {
      saveVoiceToggle(voiceToggle.checked);
    });
  }

  const themeToggle = qs("#themeToggle");
  if (themeToggle) {
    themeToggle.checked = savedTheme;
    themeToggle.addEventListener("change", () => {
      const isDark = themeToggle.checked;
      saveThemeToggle(isDark);
      applyTheme(isDark);
    });
  }

  qs("#settingsToggleBtn")?.addEventListener("click", openSettingsDrawer);
  qs("#settingsCloseBtn")?.addEventListener("click", closeSettingsDrawer);

  // Mobile menu toggle
  qs("#mobileMenuBtn")?.addEventListener("click", toggleMobileMenu);
  qs("#sidebarOverlay")?.addEventListener("click", closeMobileMenu);

  // Logout
  qs("#btn_logout")?.addEventListener("click", () => {
    clearToken();
    clearSessionId();
    window.location.href = "./login.html";
  });

  function openProfileModal() {
    const email = getCurrentEmail();
    if (!email) {
      showNotification("Not logged in.", "error");
      return;
    }

    const profile = ensureProfileDefaults(email) || { email, full_name: "", role_pref: "SWE Intern" };

    const modal = qs("#profileModal");
    if (!modal) return;

    qs("#profileEmail").value = email;
    qs("#profileName").value = profile.full_name || "";
    qs("#profileRolePref").value = profile.role_pref || "SWE Intern";

    modal.classList.remove("hidden");
    modal.classList.add("active");
  }

  function closeProfileModal() {
    const modal = qs("#profileModal");
    modal?.classList.add("hidden");
    modal?.classList.remove("active");
  }

  // Avatar click shows profile
  qs("#userAvatar")?.addEventListener("click", openProfileModal);
  qs("#profileCloseBtn")?.addEventListener("click", closeProfileModal);
  qs("#profileModal")?.addEventListener("click", (e) => {
    if (e.target?.id === "profileModal") closeProfileModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeProfileModal();
  });

  qs("#profileSaveBtn")?.addEventListener("click", () => {
    const email = getCurrentEmail();
    if (!email) return;
    const name = (qs("#profileName")?.value || "").trim();
    const rolePref = qs("#profileRolePref")?.value || "SWE Intern";
    saveLocalProfile(email, { full_name: name, role_pref: rolePref });
    updateAvatarFromProfile();
    renderDashboardProfile({ email, full_name: name, role_pref: rolePref });
    applyRolePrefToSelectors({ email, full_name: name, role_pref: rolePref });
    showNotification("Profile saved.", "success");
    closeProfileModal();
  });

  qs("#profileLogoutBtn")?.addEventListener("click", () => {
    clearToken();
    clearSessionId();
    window.location.href = "./login.html";
  });

  // Dashboard start
  qs("#startInterviewBtn")?.addEventListener("click", () => {
    handleStartFromDashboard().catch((err) => showNotification(err?.message || "Failed to start session", "error"));
  });

  qs("#viewDetailedBtn")?.addEventListener("click", () => {
    openResultsView().catch(() => navigateTo("results"));
  });
  qs("#performanceViewDetailsBtn")?.addEventListener("click", () => {
    openResultsView().catch(() => navigateTo("results"));
  });

  // Session history
  qs("#refreshSessionsBtn")?.addEventListener("click", () => refreshSessionHistory());
  qs("#refreshPerformanceBtn")?.addEventListener("click", () => refreshSessionHistory());
  qs("#sessionHistoryList")?.addEventListener("click", (e) => {
    const btn = e.target?.closest?.("button[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    const id = btn.dataset.session;
    if (!id) return;

    if (action === "resume") {
      resumeSessionById(id);
      return;
    }
    if (action === "results") {
      handleLoadResultsAndNavigate(id);
      return;
    }
    if (action === "delete") {
      handleDeleteSession(id);
    }
  });

  // Keep settings synced
  qsa("#interviewRole,#interviewCompany,#interviewDifficulty").forEach((el) => {
    el.addEventListener("change", () => syncDashboardSelectorsFromInterview());
  });
  qsa("#roleSelect,#companySelect,#difficultySelect").forEach((el) => {
    el.addEventListener("change", () => syncInterviewSelectorsFromDashboard());
  });

  // Chat send
  qs("#sendBtn")?.addEventListener("click", handleSendMessage);
  qs("#chatInput")?.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleSendMessage();
  });
  qs("#codeInput")?.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleSendMessage();
  });

  // Composer tabs
  qsa(".input-tab").forEach((btn) => {
    btn.addEventListener("click", () => setComposerTab(btn.dataset.tab || "text"));
  });
  qs("#copyCodeBtn")?.addEventListener("click", async () => {
    const code = qs("#codeInput")?.value || "";
    const ok = await copyTextToClipboard(code);
    showNotification(ok ? "Code copied." : "Copy failed.", ok ? "success" : "error");
  });
  setComposerTab("text");

  // Finalize + end
  qs("#submitInterviewBtn")?.addEventListener("click", handleFinalize);
  qs("#endSessionBtn")?.addEventListener("click", handleEndSession);
  qs("#replayLastBtn")?.addEventListener("click", handleReplayLast);
  qs("#newSessionBtn")?.addEventListener("click", () => {
    handleStartFromDashboard().catch((err) => showNotification(err?.message || "Failed to start session", "error"));
  });
  qs("#backToDashboardBtn")?.addEventListener("click", () => navigateTo("dashboard"));

  qs("#editProfileBtn")?.addEventListener("click", openProfileModal);

  // Resume badge if session exists
  const existing = getSessionId();
  if (existing) {
    setSessionBadge(`Session #${existing}`, true);
    setInterviewStatus("Ready (resume)", true);
    setInlineStatus("Session exists. Open Interview tab to continue.");
  } else {
    setSessionBadge("No Active Session", false);
    setInterviewStatus("Ready to Start", false);
  }

  // Connect voice utilities (voice.js) by mapping IDs it expects.
  // We keep it backward compatible by providing the IDs voice.js looks for.
  // (No-op if voice.js uses new IDs directly.)
  setupVoiceForInterview?.({
    onTextReady: () => {},
  });

  // Apply avatar initials on load
  updateAvatarFromProfile();

  // Dashboard profile card + defaults
  const email = getCurrentEmail();
  const profile = ensureProfileDefaults(email);
  renderDashboardProfile(profile);
  applyRolePrefToSelectors(profile);
  applySessionPrefs(loadSessionPrefs());
  updateCoverageHint().catch(() => {});

  // Load and set profile inline
  if (profile) {
    qs("#profileEmailInline").value = profile.email;
    qs("#profileNameInline").value = profile.full_name || "";
    qs("#profileRolePrefInline").value = profile.role_pref || "SWE Intern";
  }

  // Handlers
  qs("#saveProfileInlineBtn")?.addEventListener("click", () => {
    const name = qs("#profileNameInline").value.trim();
    const rolePref = qs("#profileRolePrefInline").value;
    saveLocalProfile(email, { full_name: name, role_pref: rolePref });
    updateAvatarFromProfile();
    renderDashboardProfile({ email, full_name: name, role_pref: rolePref });
    applyRolePrefToSelectors({ role_pref: rolePref });
    showNotification("Profile saved.", "success");
  });

  refreshSessionHistory();

  // hash navigation support (e.g., results page "Open Performance" link)
  if (window.location.hash === "#performance") {
    navigateTo("performance");
  } else if (window.location.hash === "#history") {
    navigateTo("history");
  } else if (window.location.hash === "#dashboard") {
    navigateTo("dashboard");
  }

  const params = new URLSearchParams(window.location.search);
  const sessionFromUrl = params.get("session_id");
  const storedSession = getSessionId();
  if (pageHasSection("interview")) {
    const targetSession = sessionFromUrl || storedSession;
    if (targetSession) {
      resumeSessionById(targetSession);
    }
  }
});