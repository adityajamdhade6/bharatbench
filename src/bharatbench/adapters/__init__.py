"""Model adapters (Gemini, Groq, OpenRouter) behind one interface."""
from __future__ import annotations

from .base import (Adapter, AdapterError, MissingKeyError, RateLimiter, RateLimitError,
                   RetryPolicy, Settings, TransientError)
from .gemini import GeminiAdapter
from .groq import GroqAdapter
from .openrouter import OpenRouterAdapter

PROVIDERS: dict[str, type[Adapter]] = {
    "gemini": GeminiAdapter,
    "groq": GroqAdapter,
    "openrouter": OpenRouterAdapter,
}

# Free-tier requests per minute. Conservative defaults; tune to your own quota.
DEFAULT_RPM = {"gemini": 10, "groq": 20, "openrouter": 30}

# Short names -> (provider, provider model id). Check these against each
# provider's current model list; use "provider:model-id" to bypass the table.
MODEL_ALIASES: dict[str, tuple[str, str]] = {
    "gemini-flash": ("gemini", "gemini-3.8-flash"),
    "gemini-flash-lite": ("gemini", "gemini-3.5-flash-lite"),
    "gemini-3.1-flash-lite": ("gemini", "gemini-3.1-flash-lite"),
    "gemma-4-31b": ("gemini", "gemma-4-31b-it"),
    "gemma-4-26b": ("gemini", "gemma-4-26b-a4b-it"),
    "llama-3.3-70b": ("groq", "llama-3.3-70b-versatile"),
    "llama-3.1-8b": ("groq", "llama-3.1-8b-instant"),
    "llama-3.3-70b-or": ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
    "llama-4-maverick": ("openrouter", "meta-llama/llama-4-maverick"),
    "qwen-flash": ("openrouter", "qwen/qwen3.8-flash"),
    "qwen-27b": ("openrouter", "qwen/qwen3.8-27b"),
    "mistral-small": ("openrouter", "mistralai/mistral-small-2603"),
    "mistral-large": ("openrouter", "mistralai/mistral-large-2512"),
}


def resolve_model(spec: str) -> tuple[str, str]:
    """'gemini-flash' or 'groq:some-model' -> (provider, model_id)."""
    spec = spec.strip()
    if spec in MODEL_ALIASES:
        return MODEL_ALIASES[spec]
    if ":" in spec:
        provider, _, model = spec.partition(":")
        if provider in PROVIDERS and model:
            return provider, model
    known = ", ".join(sorted(MODEL_ALIASES))
    raise ValueError(f"unknown model {spec!r}. Known aliases: {known}; "
                     f"or use provider:model-id with provider in {sorted(PROVIDERS)}")


_LIMITERS: dict[str, RateLimiter] = {}


def provider_limiter(provider: str) -> RateLimiter:
    """One limiter per provider, shared by every model on it (the quota is per key)."""
    if provider not in _LIMITERS:
        _LIMITERS[provider] = RateLimiter(DEFAULT_RPM[provider])
    return _LIMITERS[provider]


def build_adapter(spec: str, settings: Settings | None = None, **kw) -> Adapter:
    provider, model = resolve_model(spec)
    return PROVIDERS[provider](model, settings, limiter=provider_limiter(provider), **kw)


__all__ = [
    "Adapter", "AdapterError", "MissingKeyError", "RateLimiter", "RateLimitError", "RetryPolicy",
    "Settings", "TransientError", "GeminiAdapter", "GroqAdapter", "OpenRouterAdapter",
    "PROVIDERS", "provider_limiter", "MODEL_ALIASES", "DEFAULT_RPM", "resolve_model", "build_adapter",
]
