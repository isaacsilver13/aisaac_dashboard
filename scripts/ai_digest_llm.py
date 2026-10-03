"""Provider-agnostic text completion for the AI digest, using only the standard library.

Add a provider by writing one function `(model, system, user, api_key, max_tokens, timeout) -> str`
and registering it in PROVIDERS with the env var that holds its key. Keys come from the
environment only (never a config file) and are never printed.

    DIGEST_LLM_PROVIDER   anthropic (default) | openai
    DIGEST_LLM_MODEL      model id; anthropic defaults to claude-sonnet-5-5, openai has no default
    ANTHROPIC_API_KEY / OPENAI_API_KEY
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable

RETRY_STATUSES = {429, 500, 502, 503, 504, 529}


class LLMError(RuntimeError):
    """Configuration or API failure. The message never contains a credential."""


def _post(url: str, headers: dict[str, str], body: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    last: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in RETRY_STATUSES:
                raise LLMError(f"LLM API returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
        time.sleep(2 * (attempt + 1))
    raise LLMError(f"LLM API unreachable after 3 attempts: {type(last).__name__}")


def _anthropic(model: str, system: str, user: str, api_key: str, max_tokens: int, timeout: float):
    data = _post(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout,
    )
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _openai(model: str, system: str, user: str, api_key: str, max_tokens: int, timeout: float):
    data = _post(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
        },
        timeout,
    )
    return data["choices"][0]["message"]["content"] or ""


# provider -> (completion function, env var holding its API key, default model or None)
PROVIDERS: dict[str, tuple[Callable[..., str], str, str | None]] = {
    "anthropic": (_anthropic, "ANTHROPIC_API_KEY", "claude-sonnet-5-5"),
    "openai": (_openai, "OPENAI_API_KEY", None),
}


def resolve(env: dict[str, str] | None = None) -> tuple[str, str]:
    """Return (provider, model) from the environment, or raise LLMError saying what is missing."""
    env = os.environ if env is None else env
    provider = (env.get("DIGEST_LLM_PROVIDER") or "anthropic").lower()
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown DIGEST_LLM_PROVIDER '{provider}'. Choose: {', '.join(PROVIDERS)}.")
    model = env.get("DIGEST_LLM_MODEL") or PROVIDERS[provider][2]
    if not model:
        raise LLMError(f"Set DIGEST_LLM_MODEL for provider '{provider}'.")
    return provider, model


def complete(
    system: str,
    user: str,
    *,
    env: dict[str, str] | None = None,
    max_tokens: int = 8000,
    timeout: float = 180,
) -> tuple[str, str]:
    """Run one completion. Returns (text, "provider/model") for recording in the digest."""
    env = os.environ if env is None else env
    provider, model = resolve(env)
    function, key_var, _ = PROVIDERS[provider]
    api_key = env.get(key_var)
    if not api_key:
        raise LLMError(f"{key_var} is not set.")
    return function(model, system, user, api_key, max_tokens, timeout), f"{provider}/{model}"
