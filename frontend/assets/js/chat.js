const CHAT_STORAGE_KEY = "ai_chat_sessions_v1";
const CHAT_ACTIVE_KEY = "ai_chat_active_id_v1";
const CHAT_MAX_HISTORY = 12;
const CHAT_HISTORY_COLLAPSED_KEY = "ai_chat_history_collapsed_v1";

const state = {
  sessions: [],
  activeId: null,
  sending: false,
  historyCollapsed: false,
};

function nowTimeLabel() {
  try {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function normalizeMessageText(text) {
  let out = String(text || "");
  out = out.replace(/\r\n/g, "\n");
  out = out.replace(/\u00a0/g, " ");
  out = out.replace(/[\u200B-\u200D\uFEFF]/g, "");
  out = out.replace(/[ \t]+$/gm, "");
  out = out.replace(/\n{4,}/g, "\n\n\n");
  out = out.replace(/^\*(?!\*)\S/gm, (m) => `* ${m.slice(1)}`);
  out = out.replace(/^-([^\s-])/gm, "- $1");
  out = out.replace(/^(\d+)\.(\S)/gm, "$1. $2");
  const fenceCount = (out.match(/```/g) || []).length;
  if (fenceCount % 2 === 1) {
    out = out.replace(/```/g, "");
  }
  return out.trim();
}

function escapeHtmlLocal(str) {
  return String(str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatInline(text) {
  let out = escapeHtmlLocal(text);
  out = out.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return out;
}

function attachCopyHandler(btn, text) {
  if (!btn) return;
  btn.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(String(text || ""));
      btn.classList.add("copied");
      setTimeout(() => btn.classList.remove("copied"), 800);
    } catch {
      showNotification("Copy failed. Check clipboard permissions.", "error");
    }
  });
}

function renderTextBlock(container, block) {
  const trimmed = (block || "").trim();
  if (!trimmed) return;
  const lines = trimmed.split("\n");
  const listLines = lines.filter((l) => l.trim().startsWith("- ") || l.trim().startsWith("* "));
  const isList = listLines.length >= 2 && listLines.length === lines.length;

  if (isList) {
    const ul = document.createElement("ul");
    ul.className = "message-list";
    lines.forEach((line) => {
      const li = document.createElement("li");
      const content = line.trim().replace(/^[-*]\s+/, "");
      li.innerHTML = formatInline(content);
      ul.appendChild(li);
    });
    container.appendChild(ul);
    return;
  }

  const p = document.createElement("p");
  p.className = "message-paragraph";
  p.innerHTML = formatInline(trimmed).replace(/\n/g, "<br>");
  container.appendChild(p);
}

function renderMessageContent(container, rawText) {
  const text = normalizeMessageText(rawText);
  const codeRegex = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match = null;
  let hasCode = false;

  while ((match = codeRegex.exec(text)) !== null) {
    const before = text.slice(lastIndex, match.index);
    if (before.trim()) {
      before.split(/\n{2,}/).forEach((block) => renderTextBlock(container, block));
    }

    const lang = (match[1] || "").trim();
    const codeText = (match[2] || "").replace(/\n$/, "");
    const codeWrap = document.createElement("div");
    codeWrap.className = "code-block";

    const header = document.createElement("div");
    header.className = "code-block__header";
    header.textContent = lang ? lang.toUpperCase() : "CODE";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "code-copy";
    copyBtn.title = "Copy code";
    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
    attachCopyHandler(copyBtn, codeText);
    header.appendChild(copyBtn);

    const pre = document.createElement("pre");
    const code = document.createElement("code");
    code.textContent = codeText;
    pre.appendChild(code);

    codeWrap.appendChild(header);
    codeWrap.appendChild(pre);
    container.appendChild(codeWrap);
    hasCode = true;
    lastIndex = codeRegex.lastIndex;
  }

  const rest = text.slice(lastIndex);
  if (rest.trim()) {
    rest.split(/\n{2,}/).forEach((block) => renderTextBlock(container, block));
  }

  return hasCode;
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveSessions(list) {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(list || []));
  } catch {}
}

function getActiveId() {
  return localStorage.getItem(CHAT_ACTIVE_KEY);
}

function setActiveId(id) {
  if (!id) return;
  localStorage.setItem(CHAT_ACTIVE_KEY, id);
}

function loadHistoryCollapsed() {
  try {
    return localStorage.getItem(CHAT_HISTORY_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function saveHistoryCollapsed(value) {
  try {
    localStorage.setItem(CHAT_HISTORY_COLLAPSED_KEY, value ? "1" : "0");
  } catch {}
}

function applyHistoryCollapsed(collapsed) {
  const shell = qs(".chat-shell");
  const btn = qs("#toggleHistoryBtn i");
  if (!shell) return;
  shell.classList.toggle("history-collapsed", !!collapsed);
  if (btn) {
    btn.className = collapsed ? "fas fa-chevron-right" : "fas fa-chevron-left";
  }
}

function createSession() {
  const id = `chat_${Date.now()}`;
  return {
    id,
    title: "New chat",
    created_at: Date.now(),
    updated_at: Date.now(),
    messages: [],
  };
}

function getActiveSession() {
  return state.sessions.find((s) => s.id === state.activeId) || null;
}

function persist() {
  saveSessions(state.sessions);
  if (state.activeId) setActiveId(state.activeId);
}

function ensureSession() {
  if (!state.sessions.length) {
    const session = createSession();
    state.sessions = [session];
    state.activeId = session.id;
    persist();
  }
  if (!state.activeId || !state.sessions.find((s) => s.id === state.activeId)) {
    state.activeId = state.sessions[0]?.id || null;
    persist();
  }
}

function sessionTitleFromText(text) {
  const t = (text || "").trim().replace(/\s+/g, " ");
  if (!t) return "New chat";
  return t.length > 42 ? `${t.slice(0, 42)}...` : t;
}

function renderHistory(filter = "") {
  const list = qs("#chatHistoryList");
  if (!list) return;
  list.innerHTML = "";
  const query = (filter || "").trim().toLowerCase();

  const sorted = [...state.sessions].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));
  const filtered = query
    ? sorted.filter((s) => String(s.title || "").toLowerCase().includes(query))
    : sorted;

  if (!filtered.length) {
    const empty = document.createElement("div");
    empty.className = "history-empty";
    empty.textContent = "No chats yet.";
    list.appendChild(empty);
    return;
  }

  filtered.forEach((session) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `history-item${session.id === state.activeId ? " active" : ""}`;

    const title = document.createElement("div");
    title.className = "history-title";
    title.textContent = session.title || "Chat";

    const meta = document.createElement("div");
    meta.className = "history-meta";
    const date = session.updated_at ? new Date(session.updated_at) : null;
    const label = date && !Number.isNaN(date.getTime())
      ? date.toLocaleDateString([], { month: "short", day: "numeric" })
      : "Just now";
    meta.textContent = `${session.messages?.length || 0} messages • ${label}`;

    btn.appendChild(title);
    btn.appendChild(meta);

    const del = document.createElement("button");
    del.type = "button";
    del.className = "history-delete";
    del.title = "Delete chat";
    del.innerHTML = '<i class="fas fa-trash"></i>';
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteSession(session.id);
    });
    btn.appendChild(del);

    btn.addEventListener("click", () => {
      state.activeId = session.id;
      persist();
      renderHistory(qs("#chatSearchInput")?.value || "");
      renderMessages();
    });

    list.appendChild(btn);
  });
}

function renderMessages() {
  const wrap = qs("#chatMessages");
  const empty = qs("#chatEmptyState");
  if (!wrap) return;
  const session = getActiveSession();
  wrap.innerHTML = "";

  if (!session || !session.messages?.length) {
    if (empty) wrap.appendChild(empty);
    return;
  }

  session.messages.forEach((msg) => {
    const normalizedContent = normalizeMessageText(msg.content || "");
    const bubble = document.createElement("div");
    const msgType = msg.role === "system" ? "ai system" : msg.role === "ai" ? "ai" : "user";
    bubble.className = `message ${msgType}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";

    if (msg.role === "ai") {
      avatar.innerHTML = '<i class="fas fa-robot"></i>';
      avatar.classList.add("ai");
    } else if (msg.role === "user") {
      const profile = currentUserProfile ? currentUserProfile() : null;
      const email = profile?.email || "";
      const initials = initialsFromNameOrEmail ? initialsFromNameOrEmail(profile?.full_name || "", email) : "ME";
      const avatarUrl = profile?.avatar_url || profile?.profile_picture || profile?.avatar || "";
      if (typeof applyAvatarElement === "function") {
        applyAvatarElement(avatar, avatarUrl, initials, '<i class="fas fa-user"></i>');
      } else {
        avatar.textContent = initials || "ME";
      }
    } else {
      avatar.innerHTML = '<i class="fas fa-circle-info"></i>';
    }

    const content = document.createElement("div");
    content.className = "message-content";

    const text = document.createElement("div");
    const hasCode = normalizedContent.includes("```");
    text.className = `message-bubble${hasCode ? " has-code" : ""}`;
    renderMessageContent(text, normalizedContent);

    const meta = document.createElement("div");
    meta.className = "message-time";
    meta.textContent = `${msg.role === "user" ? "You" : msg.role === "ai" ? "AI" : "System"} | ${msg.time || nowTimeLabel()}`;

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "message-copy";
    copyBtn.title = "Copy message";
    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
    attachCopyHandler(copyBtn, normalizedContent);
    meta.appendChild(copyBtn);

    content.appendChild(text);
    content.appendChild(meta);
    bubble.appendChild(avatar);
    bubble.appendChild(content);
    wrap.appendChild(bubble);
  });

  scrollMessagesToBottom();
}

function scrollMessagesToBottom() {
  const wrap = qs("#chatMessages");
  if (!wrap) return;
  requestAnimationFrame(() => {
    wrap.scrollTop = wrap.scrollHeight;
  });
}

function addMessage(role, content) {
  const session = getActiveSession();
  if (!session) return;
  const entry = {
    role,
    content: content || "",
    time: nowTimeLabel(),
  };
  session.messages = session.messages || [];
  session.messages.push(entry);
  session.updated_at = Date.now();
  if (role === "user" && (!session.title || session.title === "New chat")) {
    session.title = sessionTitleFromText(content);
  }
  persist();
  renderHistory(qs("#chatSearchInput")?.value || "");
  renderMessages();
}

function showTyping() {
  const wrap = qs("#chatMessages");
  if (!wrap) return;
  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.id = "chatTyping";
  indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  wrap.appendChild(indicator);
  scrollMessagesToBottom();
}

function hideTyping() {
  const indicator = qs("#chatTyping");
  if (indicator) indicator.remove();
}

function setComposerEnabled(enabled) {
  const input = qs("#chatInput");
  const send = qs("#sendChatBtn");
  if (input) input.disabled = !enabled;
  if (send) send.disabled = !enabled;
}

function buildHistoryForApi(session) {
  const items = (session?.messages || []).filter((m) => m.role === "user" || m.role === "ai");
  return items.slice(-CHAT_MAX_HISTORY).map((m) => ({
    role: m.role === "ai" ? "assistant" : "user",
    content: m.content || "",
  }));
}

async function handleSend() {
  const input = qs("#chatInput");
  if (!input || state.sending) return;
  const text = (input.value || "").trim();
  if (!text) return;

  input.value = "";
  input.style.height = "auto";
  addMessage("user", text);

  const session = getActiveSession();
  if (!session) return;

  setComposerEnabled(false);
  state.sending = true;
  showTyping();

  try {
    const res = await apiFetch("/ai/chat", {
      method: "POST",
      body: {
        message: text,
        history: buildHistoryForApi(session),
      },
    });
    hideTyping();
    addMessage("ai", res?.reply || "No response received.");
    if (res?.mode === "fallback") {
      showNotification("AI is offline. Configure DEEPSEEK_API_KEY to enable chat.", "info");
    }
  } catch (err) {
    hideTyping();
    const msg = err?.message || "Failed to reach AI.";
    addMessage("system", msg);
    showNotification(msg, "error");
  } finally {
    state.sending = false;
    setComposerEnabled(true);
    input?.focus();
  }
}

function setupComposer() {
  const input = qs("#chatInput");
  const send = qs("#sendChatBtn");
  if (!input) return;

  input.addEventListener("input", () => {
    input.style.height = "auto";
    const max = 240;
    const next = Math.min(input.scrollHeight, max);
    input.style.height = `${next}px`;
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  send?.addEventListener("click", handleSend);
}

function handleNewChat() {
  const session = createSession();
  state.sessions.unshift(session);
  state.activeId = session.id;
  persist();
  renderHistory(qs("#chatSearchInput")?.value || "");
  renderMessages();
  qs("#chatInput")?.focus();
}

function handleClearChat() {
  const session = getActiveSession();
  if (!session) return;
  if (!confirm("Clear this chat?")) return;
  session.messages = [];
  session.updated_at = Date.now();
  persist();
  renderHistory(qs("#chatSearchInput")?.value || "");
  renderMessages();
}

function deleteSession(id) {
  const session = state.sessions.find((s) => s.id === id);
  if (!session) return;
  if (!confirm("Delete this chat?")) return;
  state.sessions = state.sessions.filter((s) => s.id !== id);
  if (!state.sessions.length) {
    const fresh = createSession();
    state.sessions = [fresh];
    state.activeId = fresh.id;
  } else if (state.activeId === id) {
    state.activeId = state.sessions[0]?.id || null;
  }
  persist();
  renderHistory(qs("#chatSearchInput")?.value || "");
  renderMessages();
}

function clearAllChats() {
  if (!confirm("Delete all chats? This cannot be undone.")) return;
  const fresh = createSession();
  state.sessions = [fresh];
  state.activeId = fresh.id;
  persist();
  renderHistory(qs("#chatSearchInput")?.value || "");
  renderMessages();
}

function setupHeader() {
  const mobileBtn = qs("#mobileMenuBtn");
  const overlay = qs("#sidebarOverlay");
  const sidebar = qs("#sidebar");
  mobileBtn?.addEventListener("click", () => {
    sidebar?.classList.toggle("active");
    overlay?.classList.toggle("active");
  });
  overlay?.addEventListener("click", () => {
    sidebar?.classList.remove("active");
    overlay?.classList.remove("active");
  });

  qs("#btn_logout")?.addEventListener("click", () => {
    clearToken();
    window.location.href = "./login.html";
  });
}

function updateAvatar() {
  const avatar = qs("#userAvatar");
  if (!avatar || typeof getCurrentEmail !== "function") return;
  const email = getCurrentEmail();
  if (!email) return;
  const profile = loadLocalProfile(email) || { email, full_name: "" };
  const initials = initialsFromNameOrEmail(profile.full_name || "", email);
  const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
  if (typeof applyAvatarElement === "function") {
    applyAvatarElement(avatar, avatarUrl, initials, '<i class="fas fa-user"></i>');
  }
}

async function refreshAiStatus() {
  try {
    const status = await apiFetch("/ai/status");
    if (typeof setAiBadge === "function") setAiBadge(status);
  } catch {
    if (typeof setAiBadge === "function") setAiBadge({ status: "offline", configured: false, fallback_mode: true });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const savedTheme = typeof loadThemeToggle === "function" ? loadThemeToggle() : false;
  if (typeof applyTheme === "function") applyTheme(savedTheme);

  requireAuthOrRedirect();
  if (typeof setSessionBadge === "function") setSessionBadge("No Active Session", false);
  setupHeader();
  updateAvatar();
  refreshAiStatus();

  state.sessions = loadSessions();
  state.activeId = getActiveId();
  ensureSession();
  renderHistory();
  renderMessages();
  setupComposer();

  state.historyCollapsed = loadHistoryCollapsed();
  applyHistoryCollapsed(state.historyCollapsed);

  qs("#newChatBtn")?.addEventListener("click", handleNewChat);
  qs("#clearChatBtn")?.addEventListener("click", handleClearChat);
  qs("#clearAllChatsBtn")?.addEventListener("click", clearAllChats);
  qs("#toggleHistoryBtn")?.addEventListener("click", () => {
    state.historyCollapsed = !state.historyCollapsed;
    saveHistoryCollapsed(state.historyCollapsed);
    applyHistoryCollapsed(state.historyCollapsed);
  });
  qs("#chatSearchInput")?.addEventListener("input", (e) => {
    renderHistory(e.target?.value || "");
  });
});
