from __future__ import annotations

import io
import math
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402

from .utils import Theme


@dataclass(frozen=True)
class RenderResult:
    png: bytes
    svg: bytes


def _hex_to_rgb01(h: str) -> tuple[float, float, float]:
    h = h.strip().lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def _with_alpha(hex_color: str, alpha: float) -> tuple[float, float, float, float]:
    r, g, b = _hex_to_rgb01(hex_color)
    return (r, g, b, float(alpha))


def _radial_wave(
    theta: np.ndarray,
    *,
    symmetry: int,
    base: float,
    amp: float,
    rng: np.random.Generator,
) -> np.ndarray:
    # enforce symmetry by making frequencies multiples of symmetry
    k1 = symmetry * int(rng.integers(1, 5))
    k2 = symmetry * int(rng.integers(2, 7))
    p1 = rng.random() * 2 * math.pi
    p2 = rng.random() * 2 * math.pi
    r = base + amp * (0.70 * np.sin(k1 * theta + p1) + 0.30 * np.sin(k2 * theta + p2))
    return np.clip(r, 0.02, 1.2)


def render_mandala(
    theme: Theme,
    *,
    seed: int,
    complexity: int = 6,
    symmetry: int = 12,
    size_px: int = 1024,
) -> RenderResult:
    """
    Deterministic mandala renderer using matplotlib.
    - seed controls RNG
    - complexity roughly controls number of layers/details
    - symmetry controls rotational symmetry
    """
    complexity = int(np.clip(complexity, 1, 10))
    symmetry = int(np.clip(symmetry, 4, 36))
    seed = int(seed)

    rng = np.random.default_rng(seed)
    palette = list(theme.palette)

    # Figure
    dpi = 160
    fig_size = size_px / dpi
    fig, ax = plt.subplots(figsize=(fig_size, fig_size), dpi=dpi)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)

    # Background
    fig.patch.set_facecolor(theme.background)
    ax.set_facecolor(theme.background)

    # Soft vignette
    ax.add_patch(Circle((0, 0), 1.05, color=_with_alpha(theme.background, 1.0), zorder=0))
    ax.add_patch(Circle((0, 0), 1.02, color=_with_alpha(palette[-1], 0.05), zorder=1))

    # Base rings
    ring_count = 2 + complexity
    for i in range(ring_count):
        r = 0.12 + (i / max(1, ring_count - 1)) * 0.85
        c = palette[i % len(palette)]
        lw = 0.8 + 1.0 * (1 - i / ring_count)
        ax.add_patch(
            Circle(
                (0, 0),
                r,
                fill=False,
                linewidth=lw,
                edgecolor=_with_alpha(c, 0.30),
                zorder=3,
            )
        )

    # Wavy filled layers
    layers = 2 + complexity * 2
    theta = np.linspace(0, 2 * math.pi, 1800, endpoint=True)
    for li in range(layers):
        base = 0.18 + (li / max(1, layers - 1)) * 0.78
        amp = 0.03 + 0.06 * (1 - li / max(1, layers))
        r = _radial_wave(theta, symmetry=symmetry, base=base, amp=amp, rng=rng)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        poly = Polygon(
            np.column_stack([x, y]),
            closed=True,
            facecolor=_with_alpha(palette[li % len(palette)], 0.10 + 0.08 * (li % 3)),
            edgecolor=_with_alpha(palette[(li + 2) % len(palette)], 0.18),
            linewidth=0.6,
            zorder=2,
        )
        ax.add_patch(poly)

    # Petal spokes (motif-ish)
    spoke_sets = 1 + complexity // 2
    for s in range(spoke_sets):
        n = symmetry + s * (symmetry // 3)
        n = int(np.clip(n, 6, 72))
        rad = 0.25 + 0.20 * s
        for j in range(n):
            ang = (j / n) * 2 * math.pi
            # create a "petal" by three points (teardrop-ish)
            tip = (math.cos(ang) * (rad + 0.32), math.sin(ang) * (rad + 0.32))
            left = (
                math.cos(ang - 0.08) * (rad + 0.08),
                math.sin(ang - 0.08) * (rad + 0.08),
            )
            right = (
                math.cos(ang + 0.08) * (rad + 0.08),
                math.sin(ang + 0.08) * (rad + 0.08),
            )
            color = palette[(j + s) % len(palette)]
            ax.add_patch(
                Polygon(
                    np.array([left, tip, right]),
                    closed=True,
                    facecolor=_with_alpha(color, 0.16),
                    edgecolor=_with_alpha(theme.accent, 0.18),
                    linewidth=0.5,
                    zorder=4,
                )
            )

    # Dots / beads
    bead_rings = 2 + complexity
    for i in range(bead_rings):
        ring_r = 0.22 + (i / max(1, bead_rings - 1)) * 0.70
        n = int(symmetry * (1.2 + i * 0.35))
        n = int(np.clip(n, 8, 160))
        bead_size = 0.007 + 0.010 * (1 - i / bead_rings)
        for j in range(n):
            ang = (j / n) * 2 * math.pi
            jitter = (rng.random() - 0.5) * 0.003 * (1 + complexity * 0.2)
            x = (ring_r + jitter) * math.cos(ang)
            y = (ring_r + jitter) * math.sin(ang)
            c = palette[(i + j) % len(palette)]
            ax.add_patch(
                Circle(
                    (x, y),
                    bead_size,
                    facecolor=_with_alpha(c, 0.70),
                    edgecolor=_with_alpha(theme.accent, 0.25),
                    linewidth=0.25,
                    zorder=5,
                )
            )

    # Center jewel
    ax.add_patch(
        Circle(
            (0, 0),
            0.10,
            facecolor=_with_alpha(theme.accent, 0.55),
            edgecolor=_with_alpha(palette[0], 0.9),
            linewidth=1.2,
            zorder=10,
        )
    )
    ax.add_patch(
        Circle(
            (0, 0),
            0.045,
            facecolor=_with_alpha(palette[-1], 0.85),
            edgecolor=_with_alpha("#FFFFFF", 0.35),
            linewidth=0.8,
            zorder=11,
        )
    )

    # Export
    png_buf = io.BytesIO()
    svg_buf = io.BytesIO()
    fig.savefig(png_buf, format="png", bbox_inches="tight", pad_inches=0.10, facecolor=fig.get_facecolor())
    fig.savefig(svg_buf, format="svg", bbox_inches="tight", pad_inches=0.10, facecolor=fig.get_facecolor())
    plt.close(fig)

    return RenderResult(png=png_buf.getvalue(), svg=svg_buf.getvalue())

