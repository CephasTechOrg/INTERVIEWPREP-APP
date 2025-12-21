// Voice = Speech-to-Text (browser) + Text-to-Speech (optional)
// Works best on Chrome/Edge.

let recognition = null;
let isListening = false;

function _voiceEls() {
  // Backward compatible mapping for old + new UI.
  const btn =
    document.querySelector("#voiceBtn") ||
    document.querySelector("#btn_voice");
  const note =
    document.querySelector("#voiceNote") ||
    document.querySelector("#voice_note");
  const input =
    document.querySelector("#chatInput") ||
    document.querySelector("#msg_box");
  const toggle =
    document.querySelector("#voiceToggle") ||
    document.querySelector("#tts_toggle");
  return { btn, note, input, toggle };
}

function supportsSpeechRecognition() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function initSpeechRecognition({ onPartial, onFinal, onError } = {}) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;

  const r = new SR();
  r.lang = "en-US";
  r.interimResults = true;
  r.continuous = true;

  r.onresult = (event) => {
    let interim = "";
    let finalText = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += transcript;
      else interim += transcript;
    }

    if (interim && onPartial) onPartial(interim);
    if (finalText && onFinal) onFinal(finalText);
  };

  r.onerror = (e) => onError && onError(e?.error || "voice_error");
  r.onend = () => {
    isListening = false;
    updateVoiceUI(false);
  };

  return r;
}

function startListening() {
  if (!recognition) return;
  if (isListening) return;
  isListening = true;
  updateVoiceUI(true);
  try {
    recognition.start();
  } catch {}
}

function stopListening() {
  if (!recognition) return;
  if (!isListening) return;
  isListening = false;
  updateVoiceUI(false);
  try {
    recognition.stop();
  } catch {}
}

function updateVoiceUI(listening) {
  const { btn } = _voiceEls();
  const badge =
    document.querySelector("#voice_badge") ||
    document.querySelector("#voiceBadge");
  if (btn) {
    const icon = btn.querySelector("i");
    if (icon) icon.className = listening ? "fas fa-stop" : "fas fa-microphone";
    if (!icon) btn.textContent = listening ? "Listening..." : "Mic";
    btn.classList.toggle("recording", listening);
  }
  if (badge) badge.textContent = listening ? "Voice: ON" : "Voice: ready";
}

function speakText(text) {
  if (!("speechSynthesis" in window)) return;
  const { toggle } = _voiceEls();
  const enabled = toggle?.checked;
  if (!enabled) return;

  window.speechSynthesis.cancel();

  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  u.pitch = 1.0;
  u.lang = "en-US";
  window.speechSynthesis.speak(u);
}

// Call this on interview page only
function setupVoiceForInterview({ onTextReady } = {}) {
  const supported = supportsSpeechRecognition();
  const { btn, note, input } = _voiceEls();

  if (!btn || !input) return;

  if (!supported) {
    if (note) note.textContent = "Voice input not supported in this browser. Use Chrome/Edge.";
    btn.disabled = true;
    return;
  }

  if (note) note.textContent = "Click Mic to start/stop recording. We'll convert it to text (edit before sending).";

  let live = "";
  let committed = "";

  recognition = initSpeechRecognition({
    onPartial: (t) => {
      live = t;
      if (input && isListening) input.value = (committed + " " + live).trim();
    },
    onFinal: (t) => {
      committed = (committed + " " + t).trim();
      if (input) input.value = committed;
    },
    onError: (err) => {
      if (note) note.textContent = `Voice error: ${err}. Try again.`;
    },
  });

  // Click-to-toggle UX (no hold required)
  if (!btn.dataset.voiceBound) {
    btn.dataset.voiceBound = "1";

    btn.addEventListener("click", () => {
      if (!recognition) return;
      if (!isListening) {
        committed = input?.value || "";
        startListening();
        return;
      }
      stopListening();
      if (onTextReady) onTextReady(input?.value || "");
    });

    // Escape to stop recording
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isListening) {
        stopListening();
        if (onTextReady) onTextReady(input?.value || "");
      }
    });
  }
}
