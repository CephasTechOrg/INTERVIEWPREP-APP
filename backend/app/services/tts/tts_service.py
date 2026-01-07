import logging
import os
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

from app.services.tts.elevenlabs_tts import elevenlabs_tts, is_elevenlabs_enabled
from app.services.tts.default_tts import default_tts

# Load backend/.env regardless of the current working directory.
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

logger = logging.getLogger(__name__)

# Provider names
PROVIDER_ELEVENLABS = "elevenlabs"
PROVIDER_DEFAULT = "default"


def _provider_order() -> list[str]:
    """
    Resolve provider priority. Honors TTS_PRIMARY/TTS_FALLBACK (or legacy TTS_PROVIDER).
    """
    primary = (os.getenv("TTS_PRIMARY") or os.getenv("TTS_PROVIDER") or PROVIDER_ELEVENLABS).strip().lower()
    fallback = (os.getenv("TTS_FALLBACK") or PROVIDER_DEFAULT).strip().lower()

    order: list[str] = []
    for p in (primary, fallback):
        if p and p not in order:
            order.append(p)
    # Always ensure default is in the list for robustness.
    if PROVIDER_DEFAULT not in order:
        order.append(PROVIDER_DEFAULT)
    return order


def generate_speech(text: str) -> Tuple[bytes | None, str | None, str]:
    """
    Returns (audio_bytes, content_type, provider_used)
    - provider_used: "elevenlabs" | "default" | "none"
    Fallback order is driven by env vars.
    """
    if not text or not str(text).strip():
        return None, None, "none"

    providers = _provider_order()

    for provider in providers:
        if provider == PROVIDER_ELEVENLABS:
            if not is_elevenlabs_enabled():
                continue
            try:
                audio, ctype = elevenlabs_tts(text)
                if audio:
                    logger.info("TTS provider used: %s", PROVIDER_ELEVENLABS)
                    return audio, ctype, PROVIDER_ELEVENLABS
            except Exception as e:  # noqa: BLE001
                logger.exception("ElevenLabs failed, will try fallback. Reason: %s", str(e))
                continue

        if provider == PROVIDER_DEFAULT:
            try:
                audio, ctype = default_tts(text)
                if audio:
                    logger.info("TTS provider used: %s", PROVIDER_DEFAULT)
                    return audio, ctype, PROVIDER_DEFAULT
            except Exception as e:  # noqa: BLE001
                logger.exception("Default TTS failed. Reason: %s", str(e))
                continue

    return None, None, "none"


# Backwards-compatible helper used by voice endpoint (returns audio + error string).
def synthesize_speech(text: str) -> Tuple[bytes | None, str | None]:
    audio, ctype, provider = generate_speech(text)
    if audio:
        return audio, None
    return None, f"TTS failed (provider={provider})"
