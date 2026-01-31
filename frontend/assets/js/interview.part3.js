// Split from interview.js for maintainability (part: interview.part3.js)

// Define globally accessible function for fullscreen toggle
window.toggleChatFullscreen = function() {
  const chatPanel = document.querySelector(".chat-panel");
  const layout = document.querySelector(".interview-layout");
  const container = document.querySelector(".interview-container");
  
  if (!chatPanel && !layout) {
    console.error("Chat panel not found!");
    return;
  }

  let isFullscreen = false;
  if (layout) {
    isFullscreen = layout.classList.toggle("chat-expanded");
    if (container) {
      container.classList.toggle("chat-expanded", isFullscreen);
    }
  } else if (chatPanel) {
    isFullscreen = chatPanel.classList.toggle("fullscreen");
  }
  if (chatPanel) {
    chatPanel.classList.toggle("fullscreen", isFullscreen && !layout);
  }
  
  const icon = document.querySelector("#btnExpand i");
  if (icon) {
    icon.className = isFullscreen ? "fas fa-compress" : "fas fa-expand";
  }
  
  const btn = document.querySelector("#btnExpand");
  if (btn) {
    btn.title = isFullscreen ? "Exit full screen" : "Toggle full screen";
  }
};

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
    if (info?.interviewer?.id) {
      applyInterviewerSelection(info.interviewer.id);
      saveSessionPrefs({ ...readSessionPrefsFromUI(), interviewer_id: info.interviewer.id });
    }
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
          maybeUpdateCurrentQuestion(first.current_question_id).catch((e) => logError("maybeUpdateCurrentQuestion", e));
        }
        startedNewSession = true;
      }
    } else {
      const hasInterviewer = msgs.some((m) => m.role === "interviewer");
      msgs.forEach((m) => {
        const sender = roleToSender(m.role);
        addMessage(m.content, sender, timeLabelFromDate(m.created_at));
      });
      if (!hasInterviewer && !(isDone || isWrapup)) {
        const first = await startInterview(id);
        addMessage(first.content, roleToSender(first?.role));
        if (first?.current_question_id) {
          maybeUpdateCurrentQuestion(first.current_question_id).catch((e) => logError("maybeUpdateCurrentQuestion", e));
        }
        startedNewSession = true;
      }
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
      maybeUpdateCurrentQuestion(info.current_question_id).catch((e) => logError("maybeUpdateCurrentQuestion", e));
    }
    refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
    qs("#chatInput")?.focus();
    refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
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

    refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
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
  const interviewer = currentInterviewerProfile();
  saveSessionPrefs(prefs);

  showNotification("Starting interview session...", "info");
  setInlineStatus("Creating session...");

  const s = await createSession({ role, company_style, difficulty, behavioral_questions_target, interviewer });
  setSessionId(s.id);
  if (s?.interviewer?.id) {
    applyInterviewerSelection(s.interviewer.id);
    saveSessionPrefs({ ...readSessionPrefsFromUI(), interviewer_id: s.interviewer.id });
  }

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
  maybeUpdateCurrentQuestion(msg.current_question_id).catch((e) => logError("maybeUpdateCurrentQuestion", e));
  refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
  setInlineStatus("Interview started. Reply with your approach and code.");
  showNotification("Interview session started!", "success");

  syncInterviewSelectorsFromDashboard();
  refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
  qs("#chatInput")?.focus();
}

function syncInterviewSelectorsFromDashboard() {
  const role = qs("#roleSelect")?.value;
  const company_style = qs("#companySelect")?.value;
  const difficulty = qs("#difficultySelect")?.value;
  const interviewer_id = readInterviewerSelectionFromUI();

  if (role && qs("#interviewRole")) qs("#interviewRole").value = role;
  if (company_style && qs("#interviewCompany")) qs("#interviewCompany").value = company_style;
  if (difficulty && qs("#interviewDifficulty")) qs("#interviewDifficulty").value = difficulty;
  saveSessionPrefs({
    role,
    company_style,
    difficulty,
    behavioral_questions_target: Number(qs("#behavioralSelect")?.value ?? 2),
    interviewer_id,
  });
  updateCoverageHint().catch((e) => logError("updateCoverageHint", e));
}

function syncDashboardSelectorsFromInterview() {
  const role = qs("#interviewRole")?.value;
  const company_style = qs("#interviewCompany")?.value;
  const difficulty = qs("#interviewDifficulty")?.value;
  const interviewer_id = readInterviewerSelectionFromUI();

  if (role && qs("#roleSelect")) qs("#roleSelect").value = role;
  if (company_style && qs("#companySelect")) qs("#companySelect").value = company_style;
  if (difficulty && qs("#difficultySelect")) qs("#difficultySelect").value = difficulty;
  saveSessionPrefs({
    role,
    company_style,
    difficulty,
    behavioral_questions_target: Number(qs("#behavioralSelect")?.value ?? 2),
    interviewer_id,
  });
  updateCoverageHint().catch((e) => logError("updateCoverageHint", e));
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
    maybeUpdateCurrentQuestion(reply.current_question_id).catch((e) => logError("maybeUpdateCurrentQuestion", e));
    refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
    setInterviewStatus("Waiting for your response", true);
  } catch (err) {
    hideTypingIndicator();
    const msg = err?.message || "AI service error.";
    addMessage(msg, "system");
    showNotification(msg, "error");
    refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
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
    refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
    showNotification("Interview submitted! Loading results...", "success");
    setInterviewStatus("Completed (view results)", true);
    refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
    await handleLoadResultsAndNavigate(sessionId);
  } catch (err) {
    const msg = err?.message || "AI service error.";
    addMessage(msg, "system");
    showNotification(msg, "error");
    refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
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
        openResultsView().catch((err) => {
          logError("openResultsView", err);
          navigateTo("results");
        });
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

document.addEventListener("DOMContentLoaded", async () => {
  // Apply saved theme on load (before other initialization)
  const savedTheme = loadThemeToggle();
  applyTheme(savedTheme);

  // Full screen chat toggle
  const expandBtn = qs("#btnExpand");
  if (expandBtn) {
    expandBtn.addEventListener("click", function(e) {
      e.preventDefault();
      e.stopPropagation();
      window.toggleChatFullscreen?.();
    });
  } else {
    console.warn("btnExpand button not found!");
  }

  // Close fullscreen chat on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const chatPanel = qs(".chat-panel");
      const layout = qs(".interview-layout");
      const container = qs(".interview-container");
      if (layout && layout.classList.contains("chat-expanded")) {
        layout.classList.remove("chat-expanded");
        container?.classList.remove("chat-expanded");
      }
      if (chatPanel && chatPanel.classList.contains("fullscreen")) {
        chatPanel.classList.remove("fullscreen");
        const icon = qs("#btnExpand i");
        if (icon) {
          icon.className = "fas fa-expand";
        }
      }
    }
  });

  requireAuthOrRedirect();
  let pendingAvatarUrl = "";
  let pendingAvatarInlineUrl = "";

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
    const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
    applyAvatarElement(avatar, avatarUrl, initials, '<i class="fas fa-user"></i>');
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
    const avatarEl = qs("#dashProfileAvatar");
    if (nameEl) nameEl.textContent = name || initialsFromNameOrEmail("", profile.email);
    if (emailEl) emailEl.textContent = profile.email || "-";
    if (roleEl) roleEl.textContent = profile.role_pref || "SWE Intern";
    if (avatarEl) {
      const initials = initialsFromNameOrEmail(name, profile.email);
      const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
      applyAvatarElement(avatarEl, avatarUrl, initials, '<i class="fas fa-user"></i>');
    }
    if (sessionHistoryCache.length) renderPerformanceDashboard(sessionHistoryCache);
    else refreshSessionHistory().catch((e) => logError("refreshSessionHistory", e));
  }

  function applyRolePrefToSelectors(profile) {
    if (!profile) return;
    if (qs("#roleSelect")) qs("#roleSelect").value = profile.role_pref || "SWE Intern";
    if (qs("#interviewRole")) qs("#interviewRole").value = profile.role_pref || "SWE Intern";
  }

  initNav();
  initShortcuts();
  initQuestionPin();
  refreshAiStatus().catch((e) => logError("refreshAiStatus", e));
  createVisibilityAwareInterval(() => refreshAiStatus().catch((e) => logError("refreshAiStatus", e)), 15000);

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
    const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
    pendingAvatarUrl = avatarUrl;
    setAvatarPreview(qs("#profileAvatarPreview"), avatarUrl);
    const avatarInput = qs("#profileAvatarInput");
    if (avatarInput) avatarInput.value = "";

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

  qs("#profileAvatarInput")?.addEventListener("change", async (e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await processAvatarFile(file);
      if (!dataUrl) return;
      pendingAvatarUrl = dataUrl;
      setAvatarPreview(qs("#profileAvatarPreview"), dataUrl);
    } catch (err) {
      showNotification(err?.message || "Failed to load image.", "error");
    }
  });

  qs("#profileAvatarClearBtn")?.addEventListener("click", () => {
    pendingAvatarUrl = "";
    const input = qs("#profileAvatarInput");
    if (input) input.value = "";
    setAvatarPreview(qs("#profileAvatarPreview"), "");
  });

  qs("#profileSaveBtn")?.addEventListener("click", async () => {
    const email = getCurrentEmail();
    if (!email) return;
    const name = (qs("#profileName")?.value || "").trim();
    const rolePref = qs("#profileRolePref")?.value || "SWE Intern";
    const local = loadLocalProfile(email) || {};
    const updated = { ...local, full_name: name, role_pref: rolePref };
    updated.avatar_url = pendingAvatarUrl || "";
    const extras = profileExtras(updated);
    try {
      const server = await saveProfileToServer({ full_name: name || null, role_pref: rolePref, profile: extras });
      const merged = mergeServerProfile(email, updated, server);
      saveLocalProfile(email, merged);
      updateAvatarFromProfile();
      renderDashboardProfile(merged);
      applyRolePrefToSelectors(merged);
      const mergedAvatar = merged.avatar_url || merged.profile_picture || merged.avatar || "";
      pendingAvatarInlineUrl = mergedAvatar;
      setAvatarPreview(qs("#profileAvatarInlinePreview"), mergedAvatar);
      showNotification("Profile saved.", "success");
      closeProfileModal();
    } catch (err) {
      showNotification(err?.message || "Failed to save profile.", "error");
    }
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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
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
  let profile = ensureProfileDefaults(email);
  renderDashboardProfile(profile);
  applyRolePrefToSelectors(profile);
  renderInterviewerGrid();
  applySessionPrefs(loadSessionPrefs());
  updateCoverageHint().catch((e) => logError("updateCoverageHint", e));

  // Load and set profile inline
  if (profile) {
    const emailInline = qs("#profileEmailInline");
    const nameInline = qs("#profileNameInline");
    const roleInline = qs("#profileRolePrefInline");
    if (emailInline) emailInline.value = profile.email || "";
    if (nameInline) nameInline.value = profile.full_name || "";
    if (roleInline) roleInline.value = profile.role_pref || "SWE Intern";
    const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
    pendingAvatarInlineUrl = avatarUrl;
    setAvatarPreview(qs("#profileAvatarInlinePreview"), avatarUrl);
    const inlineInput = qs("#profileAvatarInlineInput");
    if (inlineInput) inlineInput.value = "";
  }

  if (email) {
    fetchProfileFromServer()
      .then((serverProfile) => {
        profile = mergeServerProfile(email, profile, serverProfile);
        saveLocalProfile(email, profile);
        updateAvatarFromProfile();
        renderDashboardProfile(profile);
        applyRolePrefToSelectors(profile);
        if (qs("#profileEmailInline")) qs("#profileEmailInline").value = profile.email || "";
        if (qs("#profileNameInline")) qs("#profileNameInline").value = profile.full_name || "";
        if (qs("#profileRolePrefInline")) qs("#profileRolePrefInline").value = profile.role_pref || "SWE Intern";
        const avatarUrl = profile.avatar_url || profile.profile_picture || profile.avatar || "";
        pendingAvatarInlineUrl = avatarUrl;
        setAvatarPreview(qs("#profileAvatarInlinePreview"), avatarUrl);
      })
      .catch((e) => logError("fetchProfileFromServer", e));
  }

  // Handlers
  qs("#profileAvatarInlineInput")?.addEventListener("change", async (e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await processAvatarFile(file);
      if (!dataUrl) return;
      pendingAvatarInlineUrl = dataUrl;
      setAvatarPreview(qs("#profileAvatarInlinePreview"), dataUrl);
    } catch (err) {
      showNotification(err?.message || "Failed to load image.", "error");
    }
  });

  qs("#profileAvatarInlineClearBtn")?.addEventListener("click", () => {
    pendingAvatarInlineUrl = "";
    const input = qs("#profileAvatarInlineInput");
    if (input) input.value = "";
    setAvatarPreview(qs("#profileAvatarInlinePreview"), "");
  });

  qs("#saveProfileInlineBtn")?.addEventListener("click", async () => {
    const name = qs("#profileNameInline").value.trim();
    const rolePref = qs("#profileRolePrefInline").value;
    const local = loadLocalProfile(email) || {};
    const updated = { ...local, full_name: name, role_pref: rolePref };
    updated.avatar_url = pendingAvatarInlineUrl || "";
    const extras = profileExtras(updated);
    try {
      const server = await saveProfileToServer({ full_name: name || null, role_pref: rolePref, profile: extras });
      const merged = mergeServerProfile(email, updated, server);
      saveLocalProfile(email, merged);
      updateAvatarFromProfile();
      renderDashboardProfile(merged);
      applyRolePrefToSelectors(merged);
      const mergedAvatar = merged.avatar_url || merged.profile_picture || merged.avatar || "";
      pendingAvatarInlineUrl = mergedAvatar;
      setAvatarPreview(qs("#profileAvatarInlinePreview"), mergedAvatar);
      showNotification("Profile saved.", "success");
    } catch (err) {
      showNotification(err?.message || "Failed to save profile.", "error");
    }
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
