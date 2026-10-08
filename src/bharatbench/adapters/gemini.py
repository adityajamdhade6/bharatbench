"""Gemini via Google AI Studio (generativelanguage API)."""
from __future__ import annotations

from .base import AdapterError, HttpAdapter, require_key


class GeminiAdapter(HttpAdapter):
    provider = "gemini"
    env_var = "GEMINI_API_KEY"
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, model, settings=None, *, api_key: str | None = None, **kw):
        args = (settings,) if settings is not None else ()
        super().__init__(model, *args, **kw)
        self._key = require_key(self.env_var, api_key)

    def _request(self, prompt: str, system: str | None) -> str:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.settings.temperature,
                "maxOutputTokens": self.settings.max_output_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        data = self._post(f"{self.base_url}/{self.model}:generateContent",
                          {"x-goog-api-key": self._key}, payload)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            reason = (data.get("promptFeedback") or {}).get("blockReason") or "no candidates"
            raise AdapterError(f"Gemini returned no text ({reason})") from e
        if not text.strip():
            raise AdapterError("Gemini returned an empty reply (token budget used up?)")
        return text
