"""OpenRouter (OpenAI-compatible endpoint)."""
from .openai_compat import OpenAICompatAdapter


class OpenRouterAdapter(OpenAICompatAdapter):
    provider = "openrouter"
    env_var = "OPENROUTER_API_KEY"
    url = "https://openrouter.ai/api/v1/chat/completions"
