from __future__ import annotations

import colorsys
import hashlib
import re
from dataclasses import dataclass
from typing import Iterable


HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def normalize_hex(color: str, *, default: str = "#FFFFFF") -> str:
    if not isinstance(color, str):
        return default
    c = color.strip()
    if not HEX_RE.match(c):
        return default
    if not c.startswith("#"):
        c = f"#{c}"
    return c.upper()


def stable_int_hash(text: str) -> int:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def hsl_to_hex(h: float, s: float, l: float) -> str:
    # colorsys uses HLS (not HSL): (h, l, s)
    r, g, b = colorsys.hls_to_rgb(h % 1.0, _clamp01(l), _clamp01(s))
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def fallback_palette(word: str, *, n: int = 7) -> list[str]:
    base = stable_int_hash(word.lower().strip() or "mandala")
    rng = base
    colors: list[str] = []
    for i in range(n):
        # deterministic pseudo-rng using hashing
        rng = stable_int_hash(f"{word}|{rng}|{i}")
        h = ((rng >> 8) % 360) / 360.0
        s = 0.55 + ((rng >> 20) % 35) / 100.0  # 0.55..0.89
        l = 0.42 + ((rng >> 30) % 20) / 100.0  # 0.42..0.61
        colors.append(hsl_to_hex(h, s, l))
    return colors


def choose_contrasting_bg(palette: Iterable[str]) -> str:
    # Simple heuristic: default to deep near-black if palette is bright, else off-white.
    # We'll estimate brightness by average channel values.
    vals = []
    for c in palette:
        c = normalize_hex(c, default="#000000")
        r = int(c[1:3], 16) / 255.0
        g = int(c[3:5], 16) / 255.0
        b = int(c[5:7], 16) / 255.0
        vals.append((r + g + b) / 3.0)
    if not vals:
        return "#0B0B10"
    avg = sum(vals) / len(vals)
    return "#0B0B10" if avg > 0.55 else "#FAF7F2"


@dataclass(frozen=True)
class Theme:
    word: str
    palette: list[str]
    background: str
    accent: str
    mood: str
    motifs: list[str]

    def as_dict(self) -> dict:
        return {
            "word": self.word,
            "palette": list(self.palette),
            "background": self.background,
            "accent": self.accent,
            "mood": self.mood,
            "motifs": list(self.motifs),
        }


def normalize_theme_dict(word: str, data: dict) -> Theme:
    palette_in = data.get("palette") if isinstance(data, dict) else None
    if not isinstance(palette_in, list):
        palette_in = []
    palette = [normalize_hex(x, default="#FFFFFF") for x in palette_in][:10]
    if len(palette) < 5:
        palette = fallback_palette(word, n=7)

    background = normalize_hex(data.get("background", ""), default=choose_contrasting_bg(palette))
    accent = normalize_hex(data.get("accent", ""), default=palette[0])
    mood = (data.get("mood", "") if isinstance(data, dict) else "") or "themed"
    if not isinstance(mood, str):
        mood = "themed"
    mood = mood.strip()[:80]

    motifs_in = data.get("motifs") if isinstance(data, dict) else None
    motifs: list[str] = []
    if isinstance(motifs_in, list):
        for m in motifs_in[:8]:
            if isinstance(m, str) and m.strip():
                motifs.append(m.strip()[:40])
    if not motifs:
        motifs = ["petals", "rings", "dots"]

    return Theme(
        word=word.strip(),
        palette=palette,
        background=background,
        accent=accent,
        mood=mood,
        motifs=motifs,
    )

