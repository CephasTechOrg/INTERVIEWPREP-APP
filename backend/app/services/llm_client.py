import asyncio
import json
import logging
import random
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Raised when an LLM call fails in a way the app should surface gracefully."""

    pass


_llm_last_ok_at: float | None = None
_llm_last_error_at: float | None = None
_llm_last_error: str | None = None


def _record_llm_ok() -> None:
    """Track the last successful call for health/status reporting."""
    global _llm_last_ok_at
    _llm_last_ok_at = time.time()


def _record_llm_error(message: str) -> None:
    """Track the last error for health/status reporting."""
    global _llm_last_error_at, _llm_last_error
    _llm_last_error_at = time.time()
    _llm_last_error = str(message or "LLM error")


def get_llm_status() -> dict:
    """
    Returns a small status object for the frontend badge.

    Note: this is best-effort and reflects the last observed request outcome.
    """
    configured = bool((settings.DEEPSEEK_API_KEY or "").strip())
    last_ok_at = _llm_last_ok_at
    last_error_at = _llm_last_error_at
    last_error = _llm_last_error

    if not configured:
        return {
            "configured": False,
            "status": "offline",
            "fallback_mode": True,
            "reason": "DEEPSEEK_API_KEY not set",
            "last_ok_at": last_ok_at,
            "last_error_at": last_error_at,
            "last_error": last_error,
            "base_url": settings.DEEPSEEK_BASE_URL,
            "model": settings.DEEPSEEK_MODEL,
        }

    if last_ok_at is None and last_error_at is None:
        status = "unknown"
    elif last_ok_at is not None and (last_error_at is None or last_ok_at >= last_error_at):
        status = "online"
    else:
        status = "offline"

    return {
        "configured": True,
        "status": status,
        "fallback_mode": status != "online",
        "last_ok_at": last_ok_at,
        "last_error_at": last_error_at,
        "last_error": last_error,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "model": settings.DEEPSEEK_MODEL,
    }


class DeepSeekClient:
    """
    Thin DeepSeek chat client (text-in, text-out).
    Adjust endpoint/payload to match your exact DeepSeek API.
    """

    def __init__(self) -> None:
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.api_key = (settings.DEEPSEEK_API_KEY or "").strip() or None
        self.model = settings.DEEPSEEK_MODEL
        self.timeout = max(5, int(getattr(settings, "DEEPSEEK_TIMEOUT_SECONDS", 45) or 45))
        self.max_retries = max(0, int(getattr(settings, "DEEPSEEK_MAX_RETRIES", 2) or 0))
        self.backoff = float(getattr(settings, "DEEPSEEK_RETRY_BACKOFF_SECONDS", 0.8) or 0.0)

        if settings.ENV == "dev":
            print("DeepSeek key loaded:", bool(self.api_key))

    async def _post_with_retries(self, url: str, headers: dict, payload: dict) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                start = time.perf_counter()
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.post(url, headers=headers, json=payload)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                logger.info(
                    "DeepSeek chat attempt=%s status=%s elapsed_ms=%.1f", attempt + 1, r.status_code, elapsed_ms
                )

                if r.status_code < 400:
                    return r

                msg = f"DeepSeek API error {r.status_code}: {r.text}"
                _record_llm_error(msg)
                if r.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                raise LLMClientError(msg)
            except httpx.HTTPError as e:
                last_error = e
                _record_llm_error(f"DeepSeek request failed: {e!s}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                raise LLMClientError(f"DeepSeek request failed: {e!s}") from e
        if last_error:
            raise LLMClientError(f"DeepSeek request failed: {last_error!s}") from last_error
        raise LLMClientError("DeepSeek request failed: unknown error")

    def _retry_delay(self, attempt: int) -> float:
        if self.backoff <= 0:
            return 0.0
        jitter = random.random() * 0.25
        return (self.backoff * (2**attempt)) + jitter

    async def chat(self, system_prompt: str, user_prompt: str, history: list[dict] | None = None) -> str:
        if not self.api_key:
            _record_llm_error("DEEPSEEK_API_KEY is not set.")
            raise LLMClientError("DEEPSEEK_API_KEY is not set.")

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            # history items should be like {"role": "user"/"assistant", "content": "..."}
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
        }

        try:
            r = await self._post_with_retries(url, headers, payload)
            data = r.json()
            out = data["choices"][0]["message"]["content"]
        except Exception as e:
            _record_llm_error(f"DeepSeek invalid response: {e!s}")
            raise LLMClientError(f"DeepSeek invalid response: {e!s}") from e
        _record_llm_ok()
        return out

    async def chat_json(self, system_prompt: str, user_prompt: str, history: list[dict] | None = None) -> dict:
        raw = await self.chat(system_prompt, user_prompt, history=history)

        raw = (raw or "").strip()
        if not raw:
            raise LLMClientError("AI returned invalid JSON: empty response")

        # Common: ```json ... ``` or ``` ... ```
        if raw.startswith("```"):
            raw2 = raw.strip("`").strip()
            if raw2.lower().startswith("json"):
                raw2 = raw2[4:].strip()
            raw = raw2

        def _loads(s: str):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return None

        obj = _loads(raw)
        if obj is None:
            # Try substring between first '{' and last '}' (or '[' and ']')
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = _loads(raw[start : end + 1])

        if obj is None:
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                obj = _loads(raw[start : end + 1])

        if obj is None or not isinstance(obj, dict):
            _record_llm_error("AI returned invalid JSON")
            raise LLMClientError("AI returned invalid JSON: expected an object")

        return obj
