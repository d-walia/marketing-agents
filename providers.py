"""Model providers for buyer-journey probes.

MODEL POLICY: probe sessions always use each vendor's DEFAULT-TIER model at
medium effort. Do not point probes at heavyweight frontier models (Claude
Fable/Opus, o-series pro models, Gemini Pro/Ultra): buyers chat with the
defaults, so the defaults are what we audit — and they're cheaper and faster.

    Claude  -> claude-sonnet-5      (effort: medium)
    ChatGPT -> gpt-5.5              (reasoning_effort: medium)
    Gemini  -> gemini-3.5-flash     (default settings)

Override via ANTHROPIC_MODEL / OPENAI_MODEL / GEMINI_MODEL env vars only if
a vendor changes its default model. Perplexity is not currently probed.

Each provider exposes:
    ask(messages) -> answer text, given [{"role": ..., "content": str}, ...]
    preflight()   -> dict describing key validity and any usage/rate-limit
                     info the vendor's API exposes (most expose very little;
                     we report what we can and where to check the rest).

Analysis and extraction run separately on Claude (see audit.py), independent
of which assistants were probed.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

PROBE_MAX_TOKENS = 4096
RETRYABLE = {429, 500, 502, 503, 529}


def _post_json(url: str, headers: dict, payload: dict, retries: int = 4):
    """POST JSON with retry on transient errors; return (data, response_headers)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read()), dict(resp.headers)
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE or attempt == retries:
                raise
            # Rate limits need real cool-down; server blips need only seconds
            wait = 30 * (attempt + 1) if e.code == 429 else 2 ** (attempt + 1)
            print(f"    transient HTTP {e.code}, retrying in {wait}s ...", file=sys.stderr)
            time.sleep(wait)
        except urllib.error.URLError:
            if attempt == retries:
                raise
            wait = 2 ** (attempt + 1)
            print(f"    connection error, retrying in {wait}s ...", file=sys.stderr)
            time.sleep(wait)


class ClaudeProvider:
    name = "claude"
    env_key = "ANTHROPIC_API_KEY"
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

    def __init__(self):
        import anthropic

        self.client = anthropic.Anthropic()

    def ask(self, messages: list) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=PROBE_MAX_TOKENS,
            output_config={"effort": "medium"},
            messages=messages,
        )
        return "".join(b.text for b in response.content if b.type == "text")

    def preflight(self) -> dict:
        try:
            raw = self.client.messages.with_raw_response.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            h = raw.headers
            detail = (
                f"rate limit remaining this minute: "
                f"{h.get('anthropic-ratelimit-requests-remaining', '?')} requests, "
                f"{h.get('anthropic-ratelimit-input-tokens-remaining', '?')} input tokens, "
                f"{h.get('anthropic-ratelimit-output-tokens-remaining', '?')} output tokens. "
                "Credit balance is not exposed by the API - check platform.claude.com > Billing."
            )
            return {"ok": True, "detail": detail}
        except Exception as e:
            return {"ok": False, "detail": f"key check failed: {e}"}


class ChatGPTProvider:
    name = "chatgpt"
    env_key = "OPENAI_API_KEY"
    model = os.environ.get("OPENAI_MODEL", "gpt-5.5")
    url = "https://api.openai.com/v1/chat/completions"

    def _request(self, messages: list, max_tokens: int):
        return _post_json(
            self.url,
            {"Authorization": f"Bearer {os.environ[self.env_key]}"},
            {
                "model": self.model,
                "messages": messages,
                "max_completion_tokens": max_tokens,
                "reasoning_effort": "medium",
            },
        )

    def ask(self, messages: list) -> str:
        data, _ = self._request(messages, PROBE_MAX_TOKENS)
        return data["choices"][0]["message"]["content"]

    def preflight(self) -> dict:
        try:
            _, h = self._request([{"role": "user", "content": "hi"}], 16)
            detail = (
                f"rate limit remaining: {h.get('x-ratelimit-remaining-requests', '?')} requests, "
                f"{h.get('x-ratelimit-remaining-tokens', '?')} tokens "
                f"(resets in {h.get('x-ratelimit-reset-requests', '?')}). "
                "Credit balance is not exposed by the API - check platform.openai.com > Usage."
            )
            return {"ok": True, "detail": detail}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            return {"ok": False, "detail": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"ok": False, "detail": f"key check failed: {e}"}


class GeminiProvider:
    name = "gemini"
    env_key = "GEMINI_API_KEY"
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    def _request(self, contents: list, max_tokens: int):
        return _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": os.environ[self.env_key]},
            {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}},
        )

    def ask(self, messages: list) -> str:
        contents = [
            {
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        data, _ = self._request(contents, PROBE_MAX_TOKENS)
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def preflight(self) -> dict:
        try:
            self._request([{"role": "user", "parts": [{"text": "hi"}]}], 16)
            return {
                "ok": True,
                "detail": (
                    "key valid. Quota/rate limits are not exposed via response headers - "
                    "check aistudio.google.com or the Cloud console for usage."
                ),
            }
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            return {"ok": False, "detail": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"ok": False, "detail": f"key check failed: {e}"}


ALL_PROVIDERS = [ClaudeProvider, ChatGPTProvider, GeminiProvider]


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
