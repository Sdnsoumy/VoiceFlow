"""modes.py — Refinement modes and task profiles.

Refinement modes define the system prompt sent to the LLM (e.g. "Fix grammar",
"Bullet points", "Email").  Users can edit prompts from the Settings UI.

Task profiles are higher-level presets shown on the launcher screen.  Each
profile selects a mode and optionally enables/disables LLM refinement,
so the app adapts to the user’s current activity (coding, email, dictation).
"""

from __future__ import annotations

DEFAULT_MODES: list[dict] = [
    {
        "name": "Default",
        "prompt": "Fix grammar and clean up the following transcript. Return only the cleaned text.",
    },
    {
        "name": "Email",
        "prompt": (
            "Rewrite the following voice note as the body of a professional email. "
            "Keep the meaning intact, use clear sentences, and add a one-line greeting and sign-off. "
            "Return only the email body."
        ),
    },
    {
        "name": "Code comment",
        "prompt": (
            "Rewrite the following voice note as a concise developer-facing code comment. "
            "Use technical, neutral language. Return only the comment text without comment markers."
        ),
    },
    {
        "name": "Bullets",
        "prompt": (
            "Convert the following voice note into a tight bulleted list. "
            "Each bullet should be one short, self-contained idea. Return only the bullets."
        ),
    },
    {
        "name": "Meeting notes",
        "prompt": (
            "Summarize the following voice note as concise meeting notes with a 'Decisions' "
            "section and an 'Action items' section. Return only the formatted notes."
        ),
    },
]


# ---------------------------------------------------------------------------
# Task profiles — each one configures the app's entire behavior for a
# specific use-case.  The launcher shows these on startup so the user can
# pick *what* they're doing, and the app adapts accordingly.
# ---------------------------------------------------------------------------

TASK_PROFILES: list[dict] = [
    {
        "id": "prompting",
        "name": "Prompt Writing",
        "icon": "\u270d\ufe0f",
        "description": "Craft AI prompts \u2014 preserves intent, structures clearly, keeps technical terms",
        "llm_enabled": True,
        "active_mode": "Default",
        "prompt": (
            "The user is dictating an AI prompt. Clean up filler words and grammar but "
            "preserve every technical term, instruction, placeholder, and constraint exactly. "
            "Structure the text as a clear, well-formatted prompt with logical paragraphs. "
            "Do NOT add your own instructions or examples. Return only the cleaned prompt."
        ),
    },
    {
        "id": "coding",
        "name": "Coding",
        "icon": "\U0001f4bb",
        "description": "Voice-to-code \u2014 converts speech into comments, docs, or pseudocode",
        "llm_enabled": True,
        "active_mode": "Code comment",
        "prompt": (
            "The user is a developer dictating while coding. Convert their voice note into "
            "clean, technical text suitable for code comments, docstrings, or commit messages. "
            "Preserve variable names, function names, and technical jargon exactly as spoken. "
            "Use concise, imperative language. Return only the technical text."
        ),
    },
    {
        "id": "email",
        "name": "Email Writing",
        "icon": "\U0001f4e7",
        "description": "Speak your thoughts \u2014 get a polished professional email",
        "llm_enabled": True,
        "active_mode": "Email",
        "prompt": (
            "The user is dictating an email. Rewrite their voice note as a professional, "
            "well-structured email body. Add an appropriate greeting and sign-off. "
            "Keep the tone professional but natural. Fix grammar and remove filler words. "
            "Return only the email body."
        ),
    },
    {
        "id": "notes",
        "name": "Note Taking",
        "icon": "\U0001f4dd",
        "description": "Quick capture \u2014 minimal cleanup, preserves your raw thoughts",
        "llm_enabled": False,
        "active_mode": "Default",
        "prompt": (
            "Lightly clean up this voice note. Fix obvious grammar errors and remove filler "
            "words (um, uh, like) but keep the original phrasing, tone, and structure intact. "
            "Do NOT reorganize, summarize, or rephrase. Return only the cleaned text."
        ),
    },
    {
        "id": "meeting",
        "name": "Meeting Notes",
        "icon": "\U0001f91d",
        "description": "Record discussions \u2014 auto-structured with decisions and action items",
        "llm_enabled": True,
        "active_mode": "Meeting notes",
        "prompt": (
            "The user is recording meeting notes. Summarize into clear, structured meeting "
            "notes with these sections: Summary (1-2 sentences), Key Points (bullets), "
            "Decisions (bullets), Action Items (bullets with owners if mentioned). "
            "Return only the formatted notes."
        ),
    },
    {
        "id": "general",
        "name": "General Dictation",
        "icon": "\U0001f399\ufe0f",
        "description": "All-purpose voice-to-text with grammar cleanup",
        "llm_enabled": True,
        "active_mode": "Default",
        "prompt": (
            "Fix grammar and clean up the following transcript. Remove filler words. "
            "Return only the cleaned text."
        ),
    },
]


def get_task_profile(task_id: str) -> dict | None:
    for t in TASK_PROFILES:
        if t["id"] == task_id:
            return t
    return None


def list_task_profiles() -> list[dict]:
    return list(TASK_PROFILES)


def get_mode(config: dict, name: str | None = None) -> dict:
    # If a task profile is active and has a custom prompt, use that
    task_id = config.get("active_task")
    if task_id:
        profile = get_task_profile(task_id)
        if profile and profile.get("prompt"):
            return {"name": profile["name"], "prompt": profile["prompt"]}

    modes = config.get("modes") or DEFAULT_MODES
    target = name or config.get("active_mode") or "Default"
    for m in modes:
        if m.get("name") == target:
            return m
    return modes[0] if modes else {"name": "Default", "prompt": ""}


def list_modes(config: dict) -> list[str]:
    return [m["name"] for m in (config.get("modes") or DEFAULT_MODES)]

