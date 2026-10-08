"""Shared implementation for OpenAI-compatible chat-completions providers."""
from __future__ import annotations

from .base import AdapterError, HttpAdapter, chat_messages, require_key


class OpenAICompatAdapter(HttpAdapter):
    env_var = ""
    url = ""

    def __init__(self, model, settings=None, *, api_key: str | None = None, **kw):
        args = (settings,) if settings is not None else ()
        super().__init__(model, *args, **kw)
        self._key = require_key(self.env_var, api_key)

    def _request(self, prompt: str, system: str | None) -> str:
        payload = {
            "model": self.model,
            "messages": chat_messages(prompt, system),
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_output_tokens,
        }
        data = self._post(self.url, {"Authorization": f"Bearer {self._key}"}, payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            err = data.get("error") if isinstance(data, dict) else None
            raise AdapterError(f"{self.provider} returned no text ({err or 'no choices'})") from e
        if not (text or "").strip():
            raise AdapterError(f"{self.provider} returned an empty reply (token budget used up?)")
        return text
