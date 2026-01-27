// Feedback widget functionality for results page
(() => {
  // State
  let feedbackState = {
    sessionId: null,
    rating: 0,
    thumbs: null,
    rating_questions: null,
    rating_feedback: null,
    rating_difficulty: null,
    comment: "",
    submitted: false,
  };

  // DOM Elements
  const modal = document.getElementById("feedbackModal");
  const requestCard = document.getElementById("feedbackRequestCard");
  const openBtn = document.getElementById("btnOpenFeedback");
  const closeBtn = document.getElementById("closeFeedbackModal");
  const cancelBtn = document.getElementById("cancelFeedback");
  const submitBtn = document.getElementById("submitFeedback");
  const starRating = document.getElementById("starRating");
  const ratingLabel = document.getElementById("ratingValueLabel");
  const commentInput = document.getElementById("feedbackComment");
  const thumbUp = document.getElementById("thumbUp");
  const thumbDown = document.getElementById("thumbDown");

  const ratingLabels = {
    1: "Poor - Needs major improvement",
    2: "Fair - Some issues",
    3: "Good - Average experience",
    4: "Great - Very helpful",
    5: "Excellent - Outstanding!",
  };

  // Initialize feedback widget
  function initFeedbackWidget(sessionId) {
    feedbackState.sessionId = sessionId;

    // Check if feedback already submitted
    checkExistingFeedback(sessionId);

    // Setup event listeners
    setupStarRating();
    setupThumbButtons();
    setupMiniStars();
    setupModalControls();
    setupCommentInput();
  }

  async function checkExistingFeedback(sessionId) {
    try {
      const feedback = await apiFetch(`/feedback/session/${sessionId}`, { method: "GET" });
      if (feedback) {
        showFeedbackSubmitted();
        feedbackState.submitted = true;
      }
    } catch (err) {
      // No feedback yet, that's fine
    }
  }

  function showFeedbackSubmitted() {
    if (!requestCard) return;
    const requestContent = requestCard.querySelector(".feedback-request-content");
    const submittedContent = requestCard.querySelector(".feedback-submitted-content");
    if (requestContent) requestContent.style.display = "none";
    if (submittedContent) submittedContent.style.display = "flex";
    requestCard.style.background = "linear-gradient(135deg, #22c55e, #16a34a)";
  }

  function setupModalControls() {
    if (openBtn) {
      openBtn.addEventListener("click", () => openModal());
    }
    if (closeBtn) {
      closeBtn.addEventListener("click", () => closeModal());
    }
    if (cancelBtn) {
      cancelBtn.addEventListener("click", () => closeModal());
    }
    if (submitBtn) {
      submitBtn.addEventListener("click", () => submitFeedback());
    }

    // Close on overlay click
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
      });
    }

    // Close on escape
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal?.classList.contains("active")) {
        closeModal();
      }
    });
  }

  function openModal() {
    if (modal) modal.classList.add("active");
  }

  function closeModal() {
    if (modal) modal.classList.remove("active");
  }

  function setupStarRating() {
    if (!starRating) return;

    const stars = starRating.querySelectorAll(".star");

    stars.forEach((star) => {
      // Hover effect
      star.addEventListener("mouseenter", () => {
        const value = parseInt(star.dataset.value);
        highlightStars(stars, value, true);
      });

      star.addEventListener("mouseleave", () => {
        highlightStars(stars, feedbackState.rating, false);
      });

      // Click to select
      star.addEventListener("click", () => {
        const value = parseInt(star.dataset.value);
        feedbackState.rating = value;
        highlightStars(stars, value, false);
        if (ratingLabel) ratingLabel.textContent = ratingLabels[value];
        updateSubmitButton();
      });
    });
  }

  function highlightStars(stars, upTo, isHover) {
    stars.forEach((star) => {
      const val = parseInt(star.dataset.value);
      star.classList.remove("active", "hovered");
      if (val <= upTo) {
        star.classList.add(isHover ? "hovered" : "active");
      }
    });
  }

  function setupThumbButtons() {
    if (thumbUp) {
      thumbUp.addEventListener("click", () => {
        feedbackState.thumbs = feedbackState.thumbs === "up" ? null : "up";
        updateThumbButtons();
      });
    }
    if (thumbDown) {
      thumbDown.addEventListener("click", () => {
        feedbackState.thumbs = feedbackState.thumbs === "down" ? null : "down";
        updateThumbButtons();
      });
    }
  }

  function updateThumbButtons() {
    if (thumbUp) thumbUp.classList.toggle("active", feedbackState.thumbs === "up");
    if (thumbDown) thumbDown.classList.toggle("active", feedbackState.thumbs === "down");
  }

  function setupMiniStars() {
    const miniStarGroups = document.querySelectorAll(".mini-stars");

    miniStarGroups.forEach((group) => {
      const target = group.dataset.target;
      const buttons = group.querySelectorAll("button");

      buttons.forEach((btn) => {
        btn.addEventListener("mouseenter", () => {
          const value = parseInt(btn.dataset.value);
          highlightMiniStars(buttons, value, true);
        });

        btn.addEventListener("mouseleave", () => {
          highlightMiniStars(buttons, feedbackState[target] || 0, false);
        });

        btn.addEventListener("click", () => {
          const value = parseInt(btn.dataset.value);
          feedbackState[target] = value;
          highlightMiniStars(buttons, value, false);
        });
      });
    });
  }

  function highlightMiniStars(buttons, upTo, isHover) {
    buttons.forEach((btn) => {
      const val = parseInt(btn.dataset.value);
      btn.classList.remove("active", "hovered");
      if (val <= upTo) {
        btn.classList.add(isHover ? "hovered" : "active");
      }
    });
  }

  function setupCommentInput() {
    if (commentInput) {
      commentInput.addEventListener("input", () => {
        feedbackState.comment = commentInput.value;
      });
    }
  }

  function updateSubmitButton() {
    if (submitBtn) {
      submitBtn.disabled = feedbackState.rating === 0;
    }
  }

  async function submitFeedback() {
    if (!feedbackState.sessionId || feedbackState.rating === 0) {
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

    try {
      const payload = {
        session_id: feedbackState.sessionId,
        rating: feedbackState.rating,
        thumbs: feedbackState.thumbs,
        comment: feedbackState.comment || null,
        rating_questions: feedbackState.rating_questions,
        rating_feedback: feedbackState.rating_feedback,
        rating_difficulty: feedbackState.rating_difficulty,
      };

      await apiFetch("/feedback", {
        method: "POST",
        body: payload,
      });

      feedbackState.submitted = true;
      closeModal();
      showFeedbackSubmitted();

      // Show success message
      showToast("Thanks for your feedback!", "success");
    } catch (err) {
      console.error("Failed to submit feedback:", err);
      showToast("Failed to submit feedback. Please try again.", "error");
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Feedback';
    }
  }

  function showToast(message, type = "info") {
    // Simple toast implementation
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <i class="fas fa-${type === "success" ? "check-circle" : "exclamation-circle"}"></i>
      <span>${message}</span>
    `;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: ${type === "success" ? "#22c55e" : "#ef4444"};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 2000;
      animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = "slideOut 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Add animation styles
  const style = document.createElement("style");
  style.textContent = `
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
      from { transform: translateX(0); opacity: 1; }
      to { transform: translateX(100%); opacity: 0; }
    }
  `;
  document.head.appendChild(style);

  // Export for use in results.js
  window.initFeedbackWidget = initFeedbackWidget;
})();
