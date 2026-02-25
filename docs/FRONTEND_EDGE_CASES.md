# Frontend Chat UI Edge Cases & Issues

## Executive Summary

This document identifies **27 critical edge cases and bugs** discovered in the frontend chat UI components (`InterviewSection.tsx` and `ChatSection.tsx`). Issues are categorized by severity and include specific line references and recommended fixes.

---

## 🔴 CRITICAL ISSUES (Must Fix)

### 1. **Memory Leak: Blob URLs Not Released**

**Location:** [frontend-next/src/lib/services/aiService.ts](frontend-next/src/lib/services/aiService.ts#L38)

- **Issue**: `URL.createObjectURL(blob)` creates blob URLs for TTS audio but they're never revoked with `URL.revokeObjectURL()`
- **Impact**: Memory leak grows with each AI response played, especially problematic in long interviews
- **Reproduction**: Have a 20+ message conversation with voice enabled
- **Fix**:

```typescript
// Store blob URLs and revoke them after audio plays
const audioBlobUrls = useRef<string[]>([]);

// After audio ends:
audioRef.current.onended = () => {
  if (audioBlobUrls.current.length > 0) {
    URL.revokeObjectURL(audioBlobUrls.current.shift()!);
  }
};
```

### 2. **Race Condition: Double Session Start**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L283-L303)

- **Issue**: `loadMessages()` can be called multiple times rapidly (component re-renders), causing multiple `startSession()` API calls before `startRequestedRef` is set
- **Impact**: Creates duplicate AI first messages, confuses conversation state
- **Reproduction**:
  1. Start new interview
  2. Quickly switch tabs or trigger re-render
  3. Check backend logs - multiple POST `/sessions/{id}/start` calls
- **Fix**: Use async lock pattern or abort controller

```typescript
const loadMessagesAbortRef = useRef<AbortController | null>(null);

const loadMessages = async () => {
  // Cancel previous request
  loadMessagesAbortRef.current?.abort();
  loadMessagesAbortRef.current = new AbortController();

  // Use signal in API calls
  const result = await sessionService.getMessages(currentSession.id, {
    signal: loadMessagesAbortRef.current.signal,
  });
};
```

### 3. **Speech Recognition Never Stops on Unmount**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L191-L193)

- **Issue**: If user leaves page while `isListening === true`, speech recognition continues running in background
- **Impact**:
  - Privacy concern (mic stays on)
  - Browser performance degradation
  - Battery drain on mobile
- **Reproduction**:
  1. Click Record button in voice mode
  2. Navigate away or close tab while recording
  3. Check browser mic indicator - still active
- **Fix**:

```typescript
useEffect(() => {
  return () => {
    // Cleanup on unmount
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }
    setIsListening(false);
  };
}, []);
```

### 4. **Audio Context Leak**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L431-L441)

- **Issue**: `audioRef.current` audio element not cleaned up on unmount, can cause issues with multiple mounts
- **Impact**: Multiple audio contexts in memory, potential audio glitches
- **Fix**:

```typescript
useEffect(() => {
  return () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current.load();
    }
  };
}, []);
```

### 5. **Concurrent Message Send Race**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L361-L390)

- **Issue**: User can trigger `handleSendMessage()` multiple times before `loading.sending` is set (async delay)
- **Impact**: Sends duplicate messages to API, corrupts conversation state
- **Reproduction**:
  1. Type message
  2. Press Enter key repeatedly (within 50ms)
  3. Check network tab - multiple POST requests sent
- **Fix**: Set loading state IMMEDIATELY, before any async operations

```typescript
const handleSendMessage = async (e?: React.FormEvent) => {
  e?.preventDefault();
  if (!currentSession || loading.sending) return;

  // Set loading FIRST
  setLoading((prev) => ({ ...prev, sending: true }));

  const content = buildMessagePayload();
  if (!content) {
    setLoading((prev) => ({ ...prev, sending: false }));
    return;
  }

  // Continue with message send...
};
```

---

## 🟠 HIGH PRIORITY ISSUES

### 6. **Missing Error Recovery for Failed Message Send**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L382-L388)

- **Issue**: When message send fails, the optimistically-added student message remains in UI forever
- **Impact**: User sees their message but AI never responds, no way to retry
- **Fix**: Remove the optimistic message on error or add retry button

```typescript
catch (err) {
  // Remove the failed message
  setMessages((prev) => prev.filter((m) => m.id !== tempId));
  setLocalError('Send failed. Try again.');
}
```

### 7. **TTS Playback Can Stack and Overlap**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L431-L441)

- **Issue**: `playTts()` doesn't check if audio is already playing before starting new playback
- **Impact**: Multiple AI responses can play simultaneously, creating audio chaos
- **Reproduction**:
  1. Enable voice
  2. Send 2 messages rapidly
  3. Both AI responses try to play at once
- **Fix**:

```typescript
const playTts = async (text: string) => {
  if (!audioRef.current) return;

  // Stop any current playback
  if (!audioRef.current.paused) {
    audioRef.current.pause();
    audioRef.current.currentTime = 0;
  }

  // Continue with TTS generation...
};
```

### 8. **Voice Mode Text Not Cleared on Mode Switch**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L753-L771)

- **Issue**: Switching from voice mode to text mode leaves `voiceText` and `voiceInterim` populated
- **Impact**: User might accidentally resend voice transcript when switching modes
- **Fix**: Clear voice state when mode changes

```typescript
const setInputMode = (mode: InputMode) => {
  if (mode !== "voice") {
    setVoiceText("");
    setVoiceInterim("");
    if (isListening) {
      recognitionRef.current?.stop();
    }
  }
  _setInputMode(mode);
};
```

### 9. **ChatSection: Fallback Thread Creation Can Fail Silently**

**Location:** [frontend-next/src/components/sections/ChatSection.tsx](frontend-next/src/components/sections/ChatSection.tsx#L56-L59)

- **Issue**: In catch block, `createThread()` is called without try-catch
- **Impact**: If thread creation fails, app crashes with unhandled promise rejection
- **Fix**:

```typescript
} catch (error) {
  console.error('Failed to load chat threads:', error);
  try {
    const newThread = await chatService.createThread('New Chat', []);
    setThreads([...]);
  } catch (fallbackError) {
    console.error('Critical: Cannot create fallback thread', fallbackError);
    setIsLoading(false);
    // Show user-visible error
  }
}
```

### 10. **No Loading State When Switching Chat Threads**

**Location:** [frontend-next/src/components/sections/ChatSection.tsx](frontend-next/src/components/sections/ChatSection.tsx#L245-L257)

- **Issue**: Clicking different thread in sidebar immediately shows messages from old thread, then suddenly switches
- **Impact**: Confusing UI, user might send message to wrong thread
- **Fix**: Add thread-switching loading state

```typescript
const [isSwitching, setIsSwitching] = useState(false);

const handleThreadSwitch = async (threadId: number) => {
  setIsSwitching(true);
  setActiveId(threadId);
  // Load thread messages if needed
  setIsSwitching(false);
};
```

---

## 🟡 MEDIUM PRIORITY ISSUES

### 11. **AI Status Polling Never Stops**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L130-L134)

- **Issue**: `setInterval(loadAIStatus, 30000)` runs forever even when session is done
- **Impact**: Unnecessary API calls, backend load
- **Fix**: Clear interval when session ends

```typescript
useEffect(() => {
  if (currentSession?.stage === "done") return;

  loadAIStatus();
  const statusInterval = setInterval(loadAIStatus, 30000);
  return () => clearInterval(statusInterval);
}, [currentSession?.stage]);
```

### 12. **Text Sanitization Removes Valid Special Characters**

**Location:** [frontend-next/src/lib/utils/text.ts](frontend-next/src/lib/utils/text.ts#L27-L29)

- **Issue**: Regex `/[^\x09\x0A\x0D\x20-\x7E]/g` removes ALL non-ASCII characters including emojis, accented chars (é, ñ, etc.)
- **Impact**: AI responses with emoji or international characters get corrupted
- **Example**: "Great job! 👍" becomes "Great job! "
- **Fix**: Use more permissive Unicode regex

```typescript
// Keep common Unicode ranges
out = out.replace(/[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]/g, "");
```

### 13. **Timer Keeps Running After Session Ends**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L119-L127)

- **Issue**: Timer interval only checks stage on mount, not on stage change
- **Impact**: Timer continues incrementing after interview ends (cosmetic issue)
- **Fix**: Check stage in interval callback OR add stage to dependencies

```typescript
useEffect(() => {
  if (!currentSession) return;

  const timer = setInterval(() => {
    if (currentSession.stage !== "done") {
      setElapsedSec((prev) => prev + 1);
    }
  }, 1000);

  return () => clearInterval(timer);
}, [currentSession?.id]);
```

### 14. **No Timeout for TTS Generation**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L431-L441)

- **Issue**: `aiService.generateSpeech()` has no timeout, can hang forever on slow network
- **Impact**: UI stuck waiting, user has no feedback
- **Fix**: Add timeout to axios request

```typescript
// In aiService.ts
const response = await axios.post(`${getBaseURL()}/tts`, data, {
  responseType: 'arraybuffer',
  timeout: 15000, // 15 second timeout
  headers: {...},
});
```

### 15. **Auto-scroll Fires Too Often**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L107-L112)

- **Issue**: Auto-scroll runs on EVERY render when `isLeftPanelCollapsed` changes
- **Impact**: Performance hit, jerky scrolling
- **Fix**: Only scroll when messages actually change

```typescript
useEffect(() => {
  if (messagesContainerRef.current) {
    messagesContainerRef.current.scrollTop =
      messagesContainerRef.current.scrollHeight;
  }
}, [messages.length]); // Remove isLeftPanelCollapsed dependency
```

### 16. **ChatSection: Delete Chat Has No Confirmation**

**Location:** [frontend-next/src/components/sections/ChatSection.tsx](frontend-next/src/components/sections/ChatSection.tsx#L158-L176)

- **Issue**: Clicking trash icon immediately deletes thread, no undo
- **Impact**: Users can accidentally delete entire conversation history
- **Fix**: Add confirmation dialog or undo toast

### 17. **Voice Interim Text Shows in Placeholder**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L781)

- **Issue**: `placeholder={voiceInterim || 'Speak or type...'}` makes placeholder text change rapidly while speaking
- **Impact**: Distracting, looks glitchy
- **Fix**: Show interim text separately, not in placeholder

```tsx
<div className="relative">
  <input value={voiceText} placeholder="Speak or type..." />
  {voiceInterim && (
    <div className="text-xs text-gray-400 italic">{voiceInterim}</div>
  )}
</div>
```

### 18. **Missing Network Error Handling**

**Location:** Multiple locations

- **Issue**: API errors show generic "Failed to..." messages, no distinction between network errors vs server errors
- **Impact**: User can't tell if issue is their internet or backend problem
- **Fix**: Check error type and show specific messages

```typescript
catch (err) {
  let errorMsg = 'Unknown error';
  if (axios.isAxiosError(err)) {
    if (!err.response) {
      errorMsg = 'Network error. Check your connection.';
    } else if (err.response.status >= 500) {
      errorMsg = 'Server error. Try again later.';
    } else {
      errorMsg = err.response.data?.message || 'Request failed';
    }
  }
  setError(errorMsg);
}
```

---

## 🟢 LOW PRIORITY / UX IMPROVEMENTS

### 19. **No Visual Indication That Audio Is Playing**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L431-L441)

- **Issue**: When TTS plays, there's no loading spinner or audio waveform
- **Impact**: User doesn't know if audio is playing or failed
- **Fix**: Add playing state and icon

```typescript
const [isAudioPlaying, setIsAudioPlaying] = useState(false);

audioRef.current.onplay = () => setIsAudioPlaying(true);
audioRef.current.onended = () => setIsAudioPlaying(false);

// In UI:
{isAudioPlaying && <AudioWaveIcon className="animate-pulse" />}
```

### 20. **Enter Key Doesn't Work in Code Mode**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L759)

- **Issue**: Code textarea doesn't have `onKeyDown` handler for Enter to send
- **Impact**: User must click Send button, inconsistent with text mode
- **Note**: This might be intentional (Enter for newlines in code), but should be documented

### 21. **No Character/Word Count for Long Messages**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L796)

- **Issue**: Users can type unlimited text, no indication of length
- **Impact**: Very long messages might cause backend issues
- **Fix**: Add character counter and max length

```tsx
<textarea
  maxLength={5000}
  value={messageText}
  onChange={...}
/>
<div className="text-xs text-gray-500">
  {messageText.length} / 5000
</div>
```

### 22. **Speech Recognition Browser Support Not Checked**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L137-L151)

- **Issue**: Only checks if `SpeechRecognition` exists, not if it's actually usable
- **Impact**: Might show voice mode on browsers with broken implementations
- **Fix**: Add feature detection

```typescript
try {
  const testRecognition = new SpeechRecognitionCtor();
  testRecognition.abort();
  setVoiceSupported(true);
} catch {
  setVoiceSupported(false);
}
```

### 23. **ChatSection: No Empty State for Deleted Last Thread**

**Location:** [frontend-next/src/components/sections/ChatSection.tsx](frontend-next/src/components/sections/ChatSection.tsx#L166-L174)

- **Issue**: Delete logic creates new thread automatically, might be unexpected
- **Impact**: User might want empty state to start fresh
- **Consideration**: Current behavior might be intentional

### 24. **Missing Keyboard Shortcuts**

**Location:** Entire chat UI

- **Issue**: No keyboard shortcuts for common actions (Cmd+Enter to send, Cmd+N for new chat, etc.)
- **Impact**: Power users have slower workflow
- **Fix**: Add keyboard event listeners

```typescript
useEffect(() => {
  const handleKeyboard = (e: KeyboardEvent) => {
    if (e.metaKey && e.key === "Enter") {
      handleSendMessage();
    }
  };
  window.addEventListener("keydown", handleKeyboard);
  return () => window.removeEventListener("keydown", handleKeyboard);
}, []);
```

### 25. **Auto-resize Textarea Can Cause Layout Shift**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L796)

- **Issue**: `style={{ minHeight: '40px', maxHeight: '120px' }}` is static but auto-resize changes height
- **Impact**: Causes layout shifts when typing multi-line messages
- **Fix**: Reserve space or use CSS transitions

### 26. **Voice Button Doesn't Show Permission State**

**Location:** [frontend-next/src/components/sections/InterviewSection.tsx](frontend-next/src/components/sections/InterviewSection.tsx#L447-L467)

- **Issue**: If user denies microphone permission, button just fails silently
- **Impact**: User doesn't know why voice mode doesn't work
- **Fix**: Check permissions API

```typescript
const checkMicPermission = async () => {
  try {
    const result = await navigator.permissions.query({ name: "microphone" });
    if (result.state === "denied") {
      setLocalError("Microphone access denied. Check browser settings.");
    }
  } catch {}
};
```

### 27. **No Offline Indicator**

**Location:** Both chat components

- **Issue**: When user loses internet, chat continues to accept input but silently fails
- **Impact**: User wastes time typing messages that won't send
- **Fix**: Add online/offline listener

```typescript
useEffect(() => {
  const handleOffline = () => setIsOffline(true);
  const handleOnline = () => setIsOffline(false);

  window.addEventListener("offline", handleOffline);
  window.addEventListener("online", handleOnline);

  return () => {
    window.removeEventListener("offline", handleOffline);
    window.removeEventListener("online", handleOnline);
  };
}, []);
```

---

## Testing Recommendations

### Critical Path Tests Needed

1. **Long session memory leak test**: Run 50+ message conversation with voice enabled, monitor memory usage
2. **Concurrent action test**: Spam Enter key while message sending, verify no duplicates
3. **Speech recognition cleanup test**: Start recording → navigate away → check if mic indicator persists
4. **Network failure recovery test**: Disconnect internet mid-message → reconnect → verify graceful recovery
5. **Audio overlap test**: Enable voice → send 3 messages rapidly → verify only one audio plays at a time

### Browser-Specific Tests

- **Safari iOS**: Test audio autoplay policies, test speech recognition support
- **Firefox**: Test speech recognition fallback (not supported in Firefox)
- **Chrome Android**: Test speech recognition with mobile keyboard
- **Edge**: Test TTS blob URL handling

### Accessibility Tests

- Screen reader navigation through chat messages
- Keyboard-only navigation (tab order, Enter/Escape handling)
- High contrast mode rendering
- Focus management when messages auto-scroll

---

## Priority Fix Order

**Week 1 (Critical):**

1. Fix memory leak (#1) - blob URL cleanup
2. Fix race condition (#2) - session start double-call
3. Fix speech recognition cleanup (#3) - mic stays on

**Week 2 (High):** 4. Fix error recovery (#6) - failed message handling 5. Fix audio overlap (#7) - TTS playback stacking 6. Fix concurrent sends (#5) - duplicate message prevention

**Week 3 (Medium):** 7. Fix text sanitization (#12) - preserve Unicode 8. Fix AI status polling (#11) - stop when done 9. Add network error types (#18) - better error messages

**Ongoing (Low Priority):** 10. UX improvements (#19-27) - as time permits

---

## Automated Detection

Consider adding these runtime checks:

```typescript
// Memory leak detector
if (process.env.NODE_ENV === "development") {
  useEffect(() => {
    const blobUrls: string[] = [];
    const originalCreateObjectURL = URL.createObjectURL;
    URL.createObjectURL = (obj) => {
      const url = originalCreateObjectURL(obj);
      blobUrls.push(url);
      console.warn(
        `[LEAK DETECTOR] Created blob URL: ${url}. Total: ${blobUrls.length}`,
      );
      return url;
    };
  }, []);
}

// Race condition detector
if (process.env.NODE_ENV === "development") {
  let apiCallCount = 0;
  apiClient.interceptors.request.use((config) => {
    if (config.url?.includes("/start")) {
      apiCallCount++;
      if (apiCallCount > 1) {
        console.error("[RACE DETECTOR] Duplicate session start detected!");
      }
    }
    return config;
  });
}
```

---

## Summary Statistics

- **Total Issues Found**: 27
- **Critical (Must Fix)**: 5
- **High Priority**: 5
- **Medium Priority**: 8
- **Low Priority**: 9

**Estimated Fix Time**:

- Critical: ~2-3 days
- High: ~3-4 days
- Medium: ~4-5 days
- Low: ~1 week

**Total**: ~2-3 weeks for all fixes
