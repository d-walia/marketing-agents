"""Model providers for buyer-journey probes.

Each provider exposes ask(messages) -> answer text, where messages is a list
of {"role": "user"|"assistant", "content": str}. A provider is active only
when its API key is present in the environment, so the audit probes every
assistant you have keys for and skips the rest.

Claude is also used (separately) as the analysis engine that extracts and
synthesizes findings, regardless of which assistants were probed.
"""

import json
import os
import urllib.request

PROBE_MAX_TOKENS = 4096


def _post_json(url: str, headers: dict, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())


class ClaudeProvider:
    name = "claude"
    env_key = "ANTHROPIC_API_KEY"
    model = "claude-opus-4-8"

    def __init__(self):
        import anthropic

        self.client = anthropic.Anthropic()

    def ask(self, messages: list[dict]) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=PROBE_MAX_TOKENS,
            messages=messages,
        )
        return "".join(b.text for b in response.content if b.type == "text")


class OpenAICompatibleProvider:
    """Base for OpenAI-style chat-completions APIs (ChatGPT, Perplexity)."""

    url: str
    name: str
    env_key: str
    model: str

    def ask(self, messages: list[dict]) -> str:
        data = _post_json(
            self.url,
            {"Authorization": f"Bearer {os.environ[self.env_key]}"},
            {"model": self.model, "messages": messages, "max_tokens": PROBE_MAX_TOKENS},
        )
        return data["choices"][0]["message"]["content"]


class ChatGPTProvider(OpenAICompatibleProvider):
    name = "chatgpt"
    env_key = "OPENAI_API_KEY"
    model = os.environ.get("OPENAI_MODEL", "gpt-5")
    url = "https://api.openai.com/v1/chat/completions"


class PerplexityProvider(OpenAICompatibleProvider):
    name = "perplexity"
    env_key = "PERPLEXITY_API_KEY"
    model = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
    url = "https://api.perplexity.ai/chat/completions"


class GeminiProvider:
    name = "gemini"
    env_key = "GEMINI_API_KEY"
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

    def ask(self, messages: list[dict]) -> str:
        contents = [
            {
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        data = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": os.environ[self.env_key]},
            {"contents": contents},
        )
        return data["candidates"][0]["content"]["parts"][0]["text"]


ALL_PROVIDERS = [ClaudeProvider, ChatGPTProvider, GeminiProvider, PerplexityProvider]


def active_providers(requested=None):
    """Instantiate every provider whose API key is set (optionally filtered)."""
    active, skipped = [], []
    for cls in ALL_PROVIDERS:
        if requested and cls.name not in requested:
            continue
        if os.environ.get(cls.env_key):
            active.append(cls())
        else:
            skipped.append(cls.name)
    return active, skipped
