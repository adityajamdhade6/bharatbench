"""Groq (OpenAI-compatible endpoint)."""
from .openai_compat import OpenAICompatAdapter


class GroqAdapter(OpenAICompatAdapter):
    provider = "groq"
    env_var = "GROQ_API_KEY"
    url = "https://api.groq.com/openai/v1/chat/completions"
