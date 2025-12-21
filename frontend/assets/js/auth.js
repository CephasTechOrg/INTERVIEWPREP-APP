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
    setToken(data.access_token);
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
    setNotice("#signup_notice", "Account created. Redirecting...", "ok");
    setTimeout(() => (window.location.href = "./interview.html"), 450);
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
    // Ensure a local profile exists for this email (frontend-only)
    try {
      const key = `user_profile_${email.toLowerCase()}`;
      if (!localStorage.getItem(key)) {
        const guessName = email.split("@")[0].replaceAll(".", " ").replaceAll("_", " ");
        localStorage.setItem(
          key,
          JSON.stringify({
            email,
            full_name: guessName ? guessName.replace(/\b\w/g, (c) => c.toUpperCase()) : "",
            role_pref: "SWE Intern",
            company_pref: "general",
            difficulty_pref: "easy",
            focus_pref: "algorithms",
            years_experience: "",
            location: "",
            updated_at: Date.now(),
          })
        );
      }
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
        setNotice("#verify_notice", "Sending verification email...", "");
        handleResend().catch(() => {});
      }
    }
  }
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
}

function showLoginOverlay(show = true) {
  const overlay = qs("#login_overlay");
  if (!overlay) return;
  overlay.classList.toggle("hidden", !show);
}

async function handleVerify(e) {
  e.preventDefault();
  const token = qs("#ver_token")?.value.trim();
  if (!token) return;
  setNotice("#verify_notice", "Verifying...", "");
  try {
    await apiFetch("/auth/verify", { method: "POST", auth: false, body: { token } });
    setNotice("#verify_notice", "Email verified!", "ok");
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
  setNotice("#verify_notice", "Sending verification...", "");
  try {
    await apiFetch("/auth/resend-verification", { method: "POST", auth: false, body: { email } });
    setNotice("#verify_notice", "Verification email sent (or printed in console).", "ok");
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
    await apiFetch("/auth/request-password-reset", { method: "POST", auth: false, body: { email } });
    setNotice("#reset_request_notice", "If the email exists, a reset token was sent (or printed in console).", "ok");
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

document.addEventListener("DOMContentLoaded", () => {
  const suForm = qs("#signup_form");
  const liForm = qs("#login_form");
  const logoutBtn = qs("#btn_logout");
  const verifyForm = qs("#verify_form");
  const resendBtn = qs("#btn_resend");
  const resetReqForm = qs("#reset_request_form");
  const resetForm = qs("#reset_form");

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
});
