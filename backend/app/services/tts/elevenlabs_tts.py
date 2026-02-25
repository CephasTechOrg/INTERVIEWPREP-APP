import contextlib
import logging
import os
import time
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

logger = logging.getLogger(__name__)


def is_elevenlabs_enabled() -> bool:
    return bool(os.getenv("ELEVENLABS_API_KEY"))


# Map interviewer id → env var name holding their voice ID
_INTERVIEWER_VOICE_ENV: dict[str, str] = {
    "cephas": "ELEVENLABS_VOICE_CEPHAS",
    "mason": "ELEVENLABS_VOICE_MASON",
    "erica": "ELEVENLABS_VOICE_ERICA",
    "maya": "ELEVENLABS_VOICE_MAYA",
}


def get_voice_id_for_interviewer(interviewer_id: str | None) -> str | None:
    """Return the ElevenLabs voice ID for the given interviewer, or None."""
    if not interviewer_id:
        return None
    env_var = _INTERVIEWER_VOICE_ENV.get(interviewer_id.strip().lower())
    if not env_var:
        return None
    return os.getenv(env_var) or None


def _client_timeout() -> float | None:
    raw = os.getenv("TTS_TIMEOUT_SECONDS")
    if raw is None:
        return 20.0
    try:
        return float(raw)
    except Exception:  # noqa: BLE001
        return 20.0


def _soft_timeout_ms() -> float:
    """
    Soft timeout to short-circuit and fall back faster than the hard HTTP timeout.
    Defaults to 4000 ms unless overridden by env TTS_SOFT_TIMEOUT_MS.
    """
    raw = os.getenv("TTS_SOFT_TIMEOUT_MS")
    if raw is None:
        return 4000.0
    try:
        return float(raw)
    except Exception:  # noqa: BLE001
        return 4000.0


def _consume_audio_stream(audio) -> bytes:
    """
    ElevenLabs SDK can return a stream/iterable; collect into bytes for HTTP response.
    """
    if isinstance(audio, (bytes, bytearray)):
        return bytes(audio)

    buf = BytesIO()
    try:
        for chunk in audio:
            if not chunk:
                continue
            if isinstance(chunk, (bytes, bytearray)):
                buf.write(chunk)
            else:
                try:
                    buf.write(bytes(chunk))
                except Exception:
                    continue
    finally:
        with contextlib.suppress(Exception):
            buf.seek(0)
    return buf.getvalue()


def elevenlabs_tts(text: str, voice_id: str | None = None) -> tuple[bytes | None, str]:
    """
    Convert text to speech using ElevenLabs. Returns (audio_bytes, content_type).
    Raises on errors; caller handles fallback.
    Pass voice_id to override the default env-configured voice.
    """
    from elevenlabs.client import ElevenLabs  # import inside to avoid hard dependency when disabled

    api_key = os.getenv("ELEVENLABS_API_KEY")
    # Use the provided voice_id, fall back to env default, then to a hardcoded fallback
    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb"
    # Defaults favor lower latency (turbo) and smaller payload (lower bitrate).
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
    output_format = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_22050_32")
    timeout = _client_timeout()
    soft_timeout = _soft_timeout_ms() / 1000.0

    client_kwargs = {"api_key": api_key}
    if timeout:
        client_kwargs["timeout"] = timeout

    client = ElevenLabs(**client_kwargs)

    attempts = 2
    last_err: Exception | None = None
    for idx in range(attempts):
        start = time.perf_counter()
        try:
            audio_stream = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_format=output_format,
            )

            audio_bytes = _consume_audio_stream(audio_stream)
            if not audio_bytes:
                raise RuntimeError("TTS returned empty audio.")

            elapsed = (time.perf_counter() - start) * 1000.0
            logger.info(
                "ElevenLabs TTS attempt %s/%s succeeded in %.1f ms (voice=%s, model=%s, format=%s)",
                idx + 1,
                attempts,
                elapsed,
                voice_id,
                model_id,
                output_format,
            )
            return audio_bytes, "audio/mpeg"
        except Exception as e:  # noqa: BLE001
            last_err = e
            elapsed = time.perf_counter() - start
            # Short-circuit on quota errors to avoid noisy retries.
            quota_exceeded = False
            status = getattr(e, "status_code", None)
            body = getattr(e, "body", None)
            if status in {401, 402, 429} and isinstance(body, dict):
                detail = body.get("detail")
                if isinstance(detail, dict) and detail.get("status") == "quota_exceeded":
                    quota_exceeded = True
            logger.exception(
                "ElevenLabs TTS attempt %s/%s failed after %.1f ms (voice=%s, model=%s, format=%s): %s",
                idx + 1,
                attempts,
                elapsed * 1000.0,
                voice_id,
                model_id,
                output_format,
                str(e),
            )
            if quota_exceeded:
                break
            if elapsed >= soft_timeout:
                break
            if idx < attempts - 1:
                continue

    if last_err:
        raise last_err
    raise RuntimeError("TTS failed with unknown error.")
