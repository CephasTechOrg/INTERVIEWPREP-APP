// Split from interview.js for maintainability (part: interview.part1.js)

// --- Error Logging Utility ---
// Logs errors to console with context. In production, could send to monitoring service.
function logError(context, error) {
  const msg = error?.message || String(error) || "Unknown error";
  console.warn(`[${context}]`, msg, error);
  // Optionally show user-facing notification for critical errors
  // showNotification(`${context}: ${msg}`, "error");
}

// --- Debounce Utility ---
// Prevents rapid repeated calls to a function
function debounce(fn, delay = 300) {
  let timeoutId = null;
  return function (...args) {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      timeoutId = null;
      fn.apply(this, args);
    }, delay);
  };
}

// --- Visibility-aware Interval ---
// Only runs callback when page is visible
function createVisibilityAwareInterval(callback, intervalMs) {
  let intervalId = null;
  
  const start = () => {
    if (intervalId) return;
    intervalId = setInterval(() => {
      if (!document.hidden) {
        callback();
      }
    }, intervalMs);
  };
  
  const stop = () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };
  
  // Start/stop based on visibility
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stop();
    } else {
      // Run immediately when becoming visible, then restart interval
      callback();
      start();
    }
  });
  
  // Initial start
  start();
  
  return { start, stop };
}

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
const ROLE_OPTIONS = new Set([
  "SWE Intern",
  "Software Engineer",
  "Senior Engineer",
  "Senior Software Engineer",
  "Cybersecurity",
  "Data Science",
  "DevOps / Cloud",
  "Product Management",
]);
const COMPANY_OPTIONS = new Set(["general", "amazon", "google", "apple", "microsoft", "meta"]);
const DIFFICULTY_OPTIONS = new Set(["easy", "medium", "hard"]);
const INTERVIEWER_IMAGE_URL = "https://i.imgur.com/ZCLzsF6.jpeg";
const INTERVIEWER_IMAGES = {
  alex: INTERVIEWER_IMAGE_URL,
  mason: INTERVIEWER_IMAGE_URL,
  erica: INTERVIEWER_IMAGE_URL,
  maya: INTERVIEWER_IMAGE_URL,
};
const INTERVIEWERS = [
  { id: "alex", name: "Alex", gender: "Male", image_url: INTERVIEWER_IMAGES.alex },
  { id: "mason", name: "Mason", gender: "Male", image_url: INTERVIEWER_IMAGES.mason },
  { id: "erica", name: "Erica", gender: "Female", image_url: INTERVIEWER_IMAGES.erica },
  { id: "maya", name: "Maya", gender: "Female", image_url: INTERVIEWER_IMAGES.maya },
];
const INTERVIEWER_IDS = new Set(INTERVIEWERS.map((i) => i.id));
const DEFAULT_INTERVIEWER_ID = INTERVIEWERS[0]?.id || "alex";
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

function normalizeInterviewerId(value) {
  const id = String(value || "").trim().toLowerCase();
  if (!id) return null;
  return INTERVIEWER_IDS.has(id) ? id : null;
}

function getInterviewerById(id) {
  const safe = normalizeInterviewerId(id);
  if (!safe) return null;
  return INTERVIEWERS.find((item) => item.id === safe) || null;
}

function normalizeSessionPrefs(raw) {
  if (!raw || typeof raw !== "object") return null;
  const role = ROLE_OPTIONS.has(raw.role) ? raw.role : null;
  const company_style = COMPANY_OPTIONS.has(raw.company_style) ? raw.company_style : null;
  const difficulty = DIFFICULTY_OPTIONS.has(raw.difficulty) ? raw.difficulty : null;
  const interviewer_id = normalizeInterviewerId(raw.interviewer_id || raw.interviewerId);

  let behavioral = null;
  if (raw.behavioral_questions_target !== undefined) {
    behavioral = Number(raw.behavioral_questions_target);
  } else if (raw.behavioralSelect !== undefined) {
    behavioral = Number(raw.behavioralSelect);
  }
  if (Number.isNaN(behavioral)) behavioral = null;
  if (behavioral !== null) behavioral = Math.max(0, Math.min(3, behavioral));

  if (!role && !company_style && !difficulty && behavioral === null && !interviewer_id) return null;
  return { role, company_style, difficulty, behavioral_questions_target: behavioral, interviewer_id };
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

function readInterviewerSelectionFromUI() {
  const grid = qs("#interviewerGrid");
  const selected = grid?.querySelector(".interviewer-card.selected")?.dataset?.interviewer;
  const select = qs("#interviewerSelect")?.value;
  const stored = loadSessionPrefs()?.interviewer_id;
  return normalizeInterviewerId(selected || select || stored || DEFAULT_INTERVIEWER_ID);
}

function applyInterviewerSelection(interviewerId) {
  const id = normalizeInterviewerId(interviewerId) || DEFAULT_INTERVIEWER_ID;
  const grid = qs("#interviewerGrid");
  if (grid) {
    grid.querySelectorAll(".interviewer-card").forEach((card) => {
      const isSelected = card.dataset?.interviewer === id;
      card.classList.toggle("selected", isSelected);
      card.setAttribute("aria-pressed", isSelected ? "true" : "false");
    });
  }
  const select = qs("#interviewerSelect");
  if (select && id) select.value = id;
  return id;
}

function renderInterviewerGrid() {
  const grid = qs("#interviewerGrid");
  if (!grid) return;
  if (grid.dataset.ready === "true") return;
  grid.innerHTML = INTERVIEWERS.map(
    (person) => `
      <button type="button" class="interviewer-card" data-interviewer="${person.id}" aria-pressed="false">
        <div class="interviewer-card__avatar">
          <img src="${person.image_url}" alt="${escapeHtml(person.name)}" />
        </div>
        <div class="interviewer-card__meta">
          <div class="interviewer-card__name">${escapeHtml(person.name)}</div>
          <div class="interviewer-card__role">${escapeHtml(person.gender || "Interviewer")}</div>
        </div>
      </button>
    `
  ).join("");
  grid.dataset.ready = "true";
  grid.addEventListener("click", (e) => {
    const card = e.target?.closest?.(".interviewer-card");
    if (!card) return;
    const id = card.dataset?.interviewer;
    if (!id) return;
    applyInterviewerSelection(id);
    saveSessionPrefs(readSessionPrefsFromUI());
  });

  const stored = loadSessionPrefs()?.interviewer_id || DEFAULT_INTERVIEWER_ID;
  applyInterviewerSelection(stored);
}

function currentInterviewerProfile() {
  const id = readInterviewerSelectionFromUI();
  return getInterviewerById(id) || INTERVIEWERS[0] || null;
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
  if (prefs.interviewer_id) {
    applyInterviewerSelection(prefs.interviewer_id);
  }
  if (prefs.behavioral_questions_target !== null && prefs.behavioral_questions_target !== undefined) {
    if (qs("#behavioralSelect")) qs("#behavioralSelect").value = String(prefs.behavioral_questions_target);
  }
}

function readSessionPrefsFromUI() {
  const role = qs("#roleSelect")?.value || qs("#interviewRole")?.value || "SWE Intern";
  const company_style = qs("#companySelect")?.value || qs("#interviewCompany")?.value || "general";
  const difficulty = qs("#difficultySelect")?.value || qs("#interviewDifficulty")?.value || "easy";
  const interviewer_id = readInterviewerSelectionFromUI();

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

  return { role, company_style, difficulty, behavioral_questions_target, interviewer_id };
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

  const headers = {
    "Content-Type": "application/json",
    Accept: "audio/mpeg, audio/*;q=0.9, application/json;q=0.8",
  };
  try {
    const token = typeof getToken === "function" ? getToken() : null;
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } catch {
    // ignore auth lookup errors; fallback will handle
  }

  let controller = null;
  let timeoutId = null;
  if (typeof AbortController !== "undefined") {
    controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), 10000);
  }

  try {
    const res = await fetch(`${API_BASE}/tts`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text: value }),
      signal: controller?.signal,
    });
    const ctype = res.headers.get("content-type") || "";

    if (res.ok && ctype.startsWith("audio/")) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      // Stop previous audio if playing to avoid overlap.
      if (currentTtsAudio) {
        try { currentTtsAudio.pause(); } catch {}
      }
      const audio = new Audio(url);
      currentTtsAudio = audio;
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
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }

  speakText(value);
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

function profileExtras(profile) {
  const extras = { ...(profile || {}) };
  delete extras.email;
  delete extras.full_name;
  delete extras.role_pref;
  delete extras.updated_at;
  return extras;
}

async function fetchProfileFromServer() {
  return apiFetch("/users/me", { method: "GET" });
}

async function saveProfileToServer(payload) {
  return apiFetch("/users/me", { method: "PATCH", body: payload });
}

function mergeServerProfile(email, localProfile, serverProfile) {
  const local = localProfile || {};
  const server = serverProfile || {};
  const merged = { ...local, ...(server.profile || {}) };
  merged.email = server.email || email || local.email || "";
  if (server.full_name !== undefined) merged.full_name = server.full_name || "";
  if (server.role_pref !== undefined) merged.role_pref = server.role_pref || merged.role_pref || "SWE Intern";
  return merged;
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

function applyAvatarElement(el, imageUrl, fallbackText, fallbackIconHtml) {
  if (!el) return;
  el.textContent = "";
  el.innerHTML = "";
  if (imageUrl) {
    const img = document.createElement("img");
    img.className = "avatar-img";
    img.alt = "Avatar";
    img.src = imageUrl;
    el.appendChild(img);
    return;
  }
  if (fallbackText) {
    el.textContent = fallbackText;
    return;
  }
  if (fallbackIconHtml) {
    el.innerHTML = fallbackIconHtml;
  }
}

function setAvatarPreview(previewEl, imageUrl) {
  if (!previewEl) return;
  applyAvatarElement(previewEl, imageUrl, "", '<i class="fas fa-user"></i>');
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Failed to read image."));
    reader.readAsDataURL(file);
  });
}

function resizeImageDataUrl(dataUrl, size = 256) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      const scale = Math.min(size / img.width, size / img.height, 1);
      const targetW = Math.round(img.width * scale);
      const targetH = Math.round(img.height * scale);
      canvas.width = targetW;
      canvas.height = targetH;
      ctx?.drawImage(img, 0, 0, targetW, targetH);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

async function processAvatarFile(file) {
  if (!file) return null;
  if (!String(file.type || "").startsWith("image/")) {
    showNotification("Please choose an image file.", "error");
    return null;
  }
  const maxBytes = 2 * 1024 * 1024;
  if (file.size > maxBytes) {
    showNotification("Profile photo is too large (max 2MB).", "error");
    return null;
  }
  const dataUrl = await fileToDataUrl(file);
  return resizeImageDataUrl(dataUrl, 256);
}

function currentUserProfile() {
  const email = getCurrentEmail();
  if (!email) return null;
  return loadLocalProfile(email) || { email, full_name: "" };
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
