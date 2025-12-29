from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from .utils import Theme, normalize_theme_dict


THEME_SYSTEM = """You generate concise theme specs for mandala art.
Return ONLY valid JSON (no markdown, no commentary).
"""

THEME_USER_TEMPLATE = """Create a mandala theme for the word: "{word}"

Rules:
- Return JSON with keys: palette, background, accent, mood, motifs
- palette: 6-8 hex colors like "#A1B2C3"
- background: one hex color
- accent: one hex color (should be in palette if possible)
- mood: 2-6 words
- motifs: 3-6 short motif words (e.g. "petals", "waves", "stars", "vines")
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # try to salvage: find first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        return json.loads(candidate)
    raise ValueError("Could not parse JSON from model output")


def get_theme_for_word(
    word: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout_s: float = 20.0,
) -> Theme:
    """
    Uses OpenAI chat model to generate a color palette + motifs.
    Falls back deterministically when API isn't available.
    """
    word = (word or "").strip()
    if not word:
        word = "mandala"

    # If api_key is explicitly provided (even as ""), do NOT fall back to env.
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    else:
        api_key = api_key.strip()
    model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    if not api_key:
        return normalize_theme_dict(word, {})

    try:
        client = OpenAI(api_key=api_key, timeout=timeout_s)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": THEME_SYSTEM},
                {"role": "user", "content": THEME_USER_TEMPLATE.format(word=word)},
            ],
            temperature=0.8,
        )
        content = resp.choices[0].message.content or ""
        data = _extract_json(content)
        return normalize_theme_dict(word, data)
    except Exception:
        # any error => fallback
        return normalize_theme_dict(word, {})

