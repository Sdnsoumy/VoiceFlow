
"""refiner.py — LLM post-processing of raw transcripts.

Takes a raw Whisper transcript and sends it to a configured LLM provider
to fix grammar, rephrase for email, format as bullets, etc.  The system
prompt is determined by the active refinement mode.

Supported providers:
  - Ollama   — local inference (default)
  - Groq     — cloud API with free tier
  - OpenAI   — GPT models via official API
  - OpenAI-compat / LM Studio — any endpoint with OpenAI-style chat API

All network calls are synchronous with a configurable timeout.  If a call
fails, the raw transcript is returned unchanged (never lose user's words).
"""

from __future__ import annotations

import requests

from modes import get_mode
from paster import apply_clipboard_template


def _safe_timeout(config: dict, default: float = 60.0) -> float:
    """Parse the timeout value from config, falling back to *default* on bad input."""
    try:
        return float(config.get("ollama_timeout", default))
    except (TypeError, ValueError):
        return default


def _refine_ollama(text: str, prompt_prefix: str, config: dict) -> str:
    """Send text to a local Ollama instance for refinement.

    Uses the /api/generate endpoint (non-streaming).
    """
    base_url = (config.get("ollama_url") or "http://localhost:11434").rstrip("/")
    model = config.get("llm_model") or "llama3"
    timeout = _safe_timeout(config)

    payload = {
        "model": model,
        "prompt": f"{prompt_prefix}\n\n{text}",
        "stream": False,
        "options": {"temperature": 0.2},
    }

    try:
        resp = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
        resp.raise_for_status()
        refined = (resp.json().get("response") or "").strip()
        return refined or text
    except requests.RequestException as exc:
        print(f"[refiner] ollama call failed ({type(exc).__name__}); returning original text")
        return text


def _refine_groq(text: str, prompt_prefix: str, config: dict) -> str:
    """Send text to Groq's cloud API (OpenAI-compatible chat format).

    Requires a groq_api_key in config.  Falls back to raw text if not set.
    """
    api_key = config.get("groq_api_key") or ""
    if not api_key:
        print("[refiner] groq_api_key not set; returning original text")
        return text
    base_url = (config.get("groq_url") or "https://api.groq.com/openai/v1").rstrip("/")
    model = config.get("llm_model") or "llama3-8b-8192"
    timeout = _safe_timeout(config)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_prefix},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        choices = resp.json().get("choices") or []
        if choices:
            refined = (choices[0].get("message", {}).get("content") or "").strip()
            return refined or text
        return text
    except requests.RequestException as exc:
        print(f"[refiner] groq call failed ({type(exc).__name__}); returning original text")
        return text


def _refine_openai_compat(text: str, prompt_prefix: str, config: dict) -> str:
    """Generic OpenAI-compatible endpoint (works with OpenAI, Anthropic proxies,
    LM Studio, text-generation-webui, etc.)."""
    api_key = config.get("openai_api_key") or ""
    base_url = (config.get("openai_base_url") or "https://api.openai.com/v1").rstrip("/")
    model = config.get("llm_model") or "gpt-3.5-turbo"
    timeout = _safe_timeout(config)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_prefix},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        choices = resp.json().get("choices") or []
        if choices:
            refined = (choices[0].get("message", {}).get("content") or "").strip()
            return refined or text
        return text
    except requests.RequestException as exc:
        print(f"[refiner] openai-compat call failed ({type(exc).__name__}); returning original text")
        return text


def refine(text: str, config: dict) -> str:
    """Main entry point: route text to the correct provider for refinement.

    Returns the original text unchanged if LLM is disabled, text is empty,
    or the provider call fails.
    """
    if not text or not config.get("llm_enabled"):
        return text

    provider = (config.get("llm_provider") or "ollama").lower()
    mode = get_mode(config)
    prompt_prefix = mode.get("prompt") or config.get("llm_prompt") or "Clean up this transcript:"
    prompt_prefix = apply_clipboard_template(prompt_prefix)

    # --- Phase 10: context-aware refinement ---
    prev = config.get("_last_transcript", "")
    if prev and config.get("context_aware", False):
        prompt_prefix += f"\n\nPrevious transcript for context:\n{prev}"

    if provider == "groq":
        return _refine_groq(text, prompt_prefix, config)
    if provider == "ollama":
        return _refine_ollama(text, prompt_prefix, config)
    if provider in ("openai", "openai-compat", "lmstudio"):
        return _refine_openai_compat(text, prompt_prefix, config)

    print(f"[refiner] provider {provider!r} not implemented; passing through")
    return text






