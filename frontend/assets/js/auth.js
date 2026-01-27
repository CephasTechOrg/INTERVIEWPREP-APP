async function handleSignup(e) {
  e.preventDefault();
  const email = qs("#su_email").value.trim();
  const password = qs("#su_password").value.trim();
  const full_name = qs("#su_name").value.trim();
  const role_pref = qs("#su_role")?.value || "SWE Intern";
  const company_pref = qs("#su_company")?.value || "general";
  const difficulty_pref = qs("#su_difficulty")?.value || "easy";
  const focus_pref = qs("#su_focus")?.value || "algorithms";
  const years_experience = qs("#su_experience")?.value || "";
  const location = qs("#su_location")?.value || "";

  setNotice("#signup_notice", "Creating account...", "");
  try {
    const data = await apiFetch("/auth/signup", {
      method: "POST",
      auth: false,
      body: { email, password, full_name: full_name || null },
    });
    try {
      localStorage.setItem("last_auth_email", email);
    } catch {}
    // Save profile locally (frontend-only)
    try {
      const key = `user_profile_${email.toLowerCase()}`;
      const existing = JSON.parse(localStorage.getItem(key) || "{}");
      localStorage.setItem(
        key,
        JSON.stringify({
          email,
          full_name: full_name || existing.full_name || "",
          role_pref: role_pref || existing.role_pref || "SWE Intern",
          company_pref: company_pref || existing.company_pref || "general",
          difficulty_pref: difficulty_pref || existing.difficulty_pref || "easy",
          focus_pref: focus_pref || existing.focus_pref || "algorithms",
          years_experience: years_experience || existing.years_experience || "",
          location: location || existing.location || "",
          updated_at: Date.now(),
        })
      );
    } catch {}
    setNotice("#signup_notice", data?.message || "Verification code sent. Check your email.", "ok");
    if (qs("#ver_email")) qs("#ver_email").value = email;
    showView("verify");
    focusVerificationInputs();
  } catch (err) {
    setNotice("#signup_notice", err.message, "error");
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = qs("#li_email").value.trim();
  const password = qs("#li_password").value.trim();

  setNotice("#login_notice", "Signing in...", "");
  try {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    setToken(data.access_token);
    try {
      localStorage.setItem("last_auth_email", email);
    } catch {}
    // Fetch user profile from server and merge with local profile
    try {
      await fetchAndMergeServerProfile(email);
    } catch {}

    setNotice("#login_notice", "Signed in. Redirecting...", "ok");
    showLoginOverlay(true);
    setTimeout(() => (window.location.href = "./interview.html"), 450);
  } catch (err) {
    const msg = err?.message || "Login failed.";
    setNotice("#login_notice", msg, "error");
    if (String(msg).toLowerCase().includes("verify")) {
      if (qs("#ver_email")) qs("#ver_email").value = email;
      showView("verify");
      if (email) {
        setNotice("#verify_notice", "Sending verification code...", "");
        handleResend().catch((e) => console.warn("[handleResend]", e?.message || e));
      }
    }
  }
}

async function fetchAndMergeServerProfile(email) {
  const token = getToken?.();
  if (!token || !email) return;
  
  // Fetch the user's profile from the server (contains the real name from signup)
  const serverProfile = await apiFetch("/users/me", { method: "GET" });
  
  const key = `user_profile_${email.toLowerCase()}`;
  const existingRaw = localStorage.getItem(key);
  const existing = existingRaw ? JSON.parse(existingRaw) : {};
  
  // Server profile takes precedence for full_name (it's the real name from signup)
  // Only use guessed name as fallback if server has no name stored
  let finalName = serverProfile.full_name;
  if (!finalName) {
    // Fallback: use existing local name or guess from email
    finalName = existing.full_name;
    if (!finalName) {
      const guessName = email.split("@")[0].replaceAll(".", " ").replaceAll("_", " ");
      finalName = guessName ? guessName.replace(/\b\w/g, (c) => c.toUpperCase()) : "";
    }
  }
  
  // Merge server profile extras into local profile
  const serverExtras = serverProfile.profile || {};
  
  localStorage.setItem(
    key,
    JSON.stringify({
      email,
      full_name: finalName,
      role_pref: serverProfile.role_pref || existing.role_pref || "SWE Intern",
      company_pref: serverExtras.company_pref || existing.company_pref || "general",
      difficulty_pref: serverExtras.difficulty_pref || existing.difficulty_pref || "easy",
      focus_pref: serverExtras.focus_pref || existing.focus_pref || "algorithms",
      years_experience: serverExtras.years_experience || existing.years_experience || "",
      location: serverExtras.location || existing.location || "",
      updated_at: Date.now(),
    })
  );
}

async function syncProfileToServer(email) {
  const token = getToken?.();
  if (!token || !email) return;
  const key = `user_profile_${email.toLowerCase()}`;
  const raw = localStorage.getItem(key);
  if (!raw) return;
  const local = JSON.parse(raw);
  const extras = { ...local };
  delete extras.email;
  delete extras.full_name;
  delete extras.role_pref;
  delete extras.updated_at;

  await apiFetch("/users/me", {
    method: "PATCH",
    body: {
      full_name: (local.full_name || "").trim() || null,
      role_pref: local.role_pref || "SWE Intern",
      profile: extras,
    },
  });
}

function handleLogout() {
  clearToken();
  localStorage.removeItem("current_session_id");
  window.location.href = "./login.html";
}

function setNotice(selector, msg, type) {
  const el = qs(selector);
  if (!el) return;
  el.textContent = msg;
  const normalized = type === "ok" ? "success" : (type || "");
  const base = el.classList.contains("login-notice") ? "login-notice" : "notice";
  el.className = `${base} ${normalized}`.trim();
}

function showView(viewName) {
  const targetId = `view_${viewName}`;
  document.querySelectorAll(".auth-view").forEach((v) => {
    v.classList.toggle("hidden", v.id !== targetId);
  });
  document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === viewName);
  });
  const indicator = qs(".tab-indicator");
  if (indicator) {
    const index = viewName === "signup" ? 1 : 0;
    indicator.style.transform = `translateX(${index * 100}%)`;
  }
  if (viewName === "verify") focusVerificationInputs();
}

function showLoginOverlay(show = true) {
  const overlay = qs("#login_overlay");
  if (!overlay) return;
  overlay.classList.toggle("hidden", !show);
}

function focusVerificationInputs() {
  const first = qs("#verifyCodeInputs .code-input");
  if (first) first.focus();
}

function readVerificationCode() {
  const inputs = qsa("#verifyCodeInputs .code-input");
  if (!inputs.length) return "";
  return inputs.map((i) => (i.value || "").trim()).join("").replace(/\D/g, "");
}

function setupVerificationInputs() {
  const inputs = qsa("#verifyCodeInputs .code-input");
  if (!inputs.length) return;

  const fillFrom = (start, digits) => {
    let idx = start;
    for (const ch of digits) {
      if (idx >= inputs.length) break;
      inputs[idx].value = ch;
      idx += 1;
    }
    const focusIdx = Math.min(idx, inputs.length) - 1;
    if (focusIdx >= 0) inputs[focusIdx].focus();
  };

  inputs.forEach((input, index) => {
    input.addEventListener("input", () => {
      const digits = input.value.replace(/\D/g, "");
      if (!digits) {
        input.value = "";
        return;
      }
      if (digits.length === 1) {
        input.value = digits;
        if (index < inputs.length - 1) inputs[index + 1].focus();
        return;
      }
      fillFrom(index, digits);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !input.value && index > 0) {
        inputs[index - 1].value = "";
        inputs[index - 1].focus();
      }
      if (e.key === "ArrowLeft" && index > 0) {
        inputs[index - 1].focus();
      }
      if (e.key === "ArrowRight" && index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
    });

    input.addEventListener("paste", (e) => {
      const text = (e.clipboardData || window.clipboardData).getData("text");
      const digits = String(text || "").replace(/\D/g, "");
      if (!digits) return;
      e.preventDefault();
      fillFrom(index, digits);
    });
  });
}

async function handleVerify(e) {
  e.preventDefault();
  const email = qs("#ver_email")?.value.trim();
  const code = readVerificationCode();
  if (!email) {
    setNotice("#verify_notice", "Enter your email first.", "error");
    return;
  }
  if (code.length !== 6) {
    setNotice("#verify_notice", "Enter the 6-digit code.", "error");
    return;
  }
  setNotice("#verify_notice", "Verifying...", "");
  try {
    const data = await apiFetch("/auth/verify", {
      method: "POST",
      auth: false,
      body: { email, code },
    });
    setToken(data.access_token);
    setNotice("#verify_notice", "Verified. Signing you in...", "ok");
    showLoginOverlay(true);
    setTimeout(() => (window.location.href = "./interview.html"), 450);
  } catch (err) {
    setNotice("#verify_notice", err.message, "error");
  }
}

async function handleResend() {
  const email = qs("#ver_email")?.value.trim();
  if (!email) {
    setNotice("#verify_notice", "Enter email to resend.", "error");
    return;
  }
  setNotice("#verify_notice", "Sending verification code...", "");
  try {
    await apiFetch("/auth/resend-verification", { method: "POST", auth: false, body: { email } });
    setNotice("#verify_notice", "Verification code sent (or printed in console).", "ok");
  } catch (err) {
    setNotice("#verify_notice", err.message, "error");
  }
}

async function handleResetRequest(e) {
  e.preventDefault();
  const email = qs("#rp_email")?.value.trim();
  if (!email) return;
  setNotice("#reset_request_notice", "Requesting reset...", "");
  try {
    const data = await apiFetch("/auth/request-password-reset", { method: "POST", auth: false, body: { email } });
    const tokenEl = qs("#rp_token");
    if (data?.token && tokenEl && !tokenEl.value) {
      tokenEl.value = data.token;
    }
    const msg = data?.token
      ? "Reset token ready. Enter a new password below."
      : "If the email exists, a reset token was sent (or printed in console).";
    setNotice("#reset_request_notice", msg, "ok");
  } catch (err) {
    setNotice("#reset_request_notice", err.message, "error");
  }
}

async function handleReset(e) {
  e.preventDefault();
  const token = qs("#rp_token")?.value.trim();
  const new_password = qs("#rp_new_password")?.value.trim();
  if (!token || !new_password) return;
  setNotice("#reset_notice", "Resetting...", "");
  try {
    await apiFetch("/auth/reset-password", { method: "POST", auth: false, body: { token, new_password } });
    setNotice("#reset_notice", "Password reset. You can now sign in.", "ok");
  } catch (err) {
    setNotice("#reset_notice", err.message, "error");
  }
}

// Theme utilities for login page
const THEME_TOGGLE_KEY = "dark_theme";

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

document.addEventListener("DOMContentLoaded", () => {
  // Apply theme first
  const savedTheme = loadThemeToggle();
  applyTheme(savedTheme);

  const suForm = qs("#signup_form");
  const liForm = qs("#login_form");
  const logoutBtn = qs("#btn_logout");
  const verifyForm = qs("#verify_form");
  const resendBtn = qs("#btn_resend");
  const resetReqForm = qs("#reset_request_form");
  const resetForm = qs("#reset_form");

  setupVerificationInputs();

  if (suForm) suForm.addEventListener("submit", handleSignup);
  if (liForm) liForm.addEventListener("submit", handleLogin);
  if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);
  if (verifyForm) verifyForm.addEventListener("submit", handleVerify);
  if (resendBtn) resendBtn.addEventListener("click", handleResend);
  if (resetReqForm) resetReqForm.addEventListener("submit", handleResetRequest);
  if (resetForm) resetForm.addEventListener("submit", handleReset);
  qs("#link_forgot")?.addEventListener("click", () => {
    const email = qs("#li_email")?.value || "";
    if (email) qs("#rp_email").value = email;
    showView("reset");
  });
  qs("#link_verify")?.addEventListener("click", () => {
    const email = qs("#li_email")?.value || "";
    if (email) qs("#ver_email").value = email;
    showView("verify");
  });

  document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.view;
      showView(view);
    });
  });

  document.querySelectorAll("[data-view-jump]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.getAttribute("data-view-jump");
      showView(view);
    });
  });

  showView("signin");

  const token = getToken();
  const quick = qs("#quick_go");
  if (quick) quick.style.display = token ? "inline-flex" : "none";

  const params = new URLSearchParams(window.location.search);
  const viewParam = params.get("view");
  const tokenParam = params.get("token");
  const emailParam = params.get("email");
  const hash = window.location.hash.replace("#", "");
  const requestedView = viewParam || hash;
  const lastEmail = (() => {
    try {
      return localStorage.getItem("last_auth_email") || "";
    } catch {
      return "";
    }
  })();
  if (requestedView === "verify") {
    if (qs("#ver_email") && lastEmail) qs("#ver_email").value = lastEmail;
    showView("verify");
    focusVerificationInputs();
    return;
  }
  if (requestedView === "reset" || tokenParam) {
    if (qs("#rp_email")) qs("#rp_email").value = emailParam || lastEmail;
    if (qs("#rp_token") && tokenParam) qs("#rp_token").value = tokenParam;
    showView("reset");
    return;
  }
});
