"""
Placeholder default/robotic TTS adapter.

If you have an existing backend TTS engine, implement it here and return (audio_bytes, content_type).
If your fallback is frontend speechSynthesis, keep this as-is so the backend returns text and the
frontend can synthesize locally.
"""


def default_tts(_text: str) -> tuple[bytes | None, str | None]:
    # No backend default TTS implemented; return None so the caller can fall back to text/front-end TTS.
    return None, None
