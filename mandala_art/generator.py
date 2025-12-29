from __future__ import annotations

import io
import math
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Polygon  # noqa: E402
from matplotlib.path import Path  # noqa: E402

from .utils import Theme


@dataclass(frozen=True)
class RenderResult:
    png: bytes
    svg: bytes | None


def _hex_to_rgb01(h: str) -> tuple[float, float, float]:
    h = h.strip().lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def _with_alpha(hex_color: str, alpha: float) -> tuple[float, float, float, float]:
    r, g, b = _hex_to_rgb01(hex_color)
    return (r, g, b, float(alpha))


def _smooth_closed_path(x: np.ndarray, y: np.ndarray) -> Path:
    """
    Build a smooth-ish closed cubic-bezier path through points.
    Lightweight cardinal-spline approximation suitable for mandala curves.
    """
    pts = np.column_stack([x, y]).astype(float)
    if len(pts) < 6:
        verts = np.vstack([pts, pts[:1]])
        codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
        return Path(verts, codes)

    # Wrap points for derivative estimation at ends
    p = np.vstack([pts[-2:], pts, pts[:2]])
    tension = 0.55

    verts = [tuple(pts[0])]
    codes = [Path.MOVETO]

    for i in range(2, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        d1 = (p2 - p0) * (tension / 6.0)
        d2 = (p3 - p1) * (tension / 6.0)
        c1 = p1 + d1
        c2 = p2 - d2
        verts.extend([tuple(c1), tuple(c2), tuple(p2)])
        codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])

    verts.append((0.0, 0.0))  # ignored for CLOSEPOLY
    codes.append(Path.CLOSEPOLY)
    return Path(np.array(verts, dtype=float), codes)


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
    export_svg: bool = False,
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
    dpi = 200
    fig_size = size_px / dpi
    fig, ax = plt.subplots(figsize=(fig_size, fig_size), dpi=dpi)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)

    # Background
    fig.patch.set_facecolor(theme.background)
    ax.set_facecolor(theme.background)

    # Premium vignette + subtle glow
    ax.add_patch(Circle((0, 0), 1.06, color=_with_alpha(theme.background, 1.0), zorder=0))
    ax.add_patch(Circle((0, 0), 1.04, color=_with_alpha(palette[-1], 0.06), zorder=1))
    ax.add_patch(Circle((0, 0), 0.98, color=_with_alpha(palette[0], 0.03), zorder=1))

    theta = np.linspace(0, 2 * math.pi, 3600, endpoint=True)

    # Intricate rosette fills (smooth Bezier paths)
    layers = 10 + complexity * 2
    for li in range(layers):
        frac = li / max(1, layers - 1)
        base = 0.18 + frac * 0.80
        amp = (0.015 + (1 - frac) * 0.06) * (0.85 + 0.25 * rng.random())

        k = symmetry * int(rng.integers(1, 5))
        p1 = rng.random() * 2 * math.pi
        p2 = rng.random() * 2 * math.pi
        r = base + amp * (0.65 * np.sin(k * theta + p1) + 0.35 * np.sin((2 * k) * theta + p2))
        r = np.clip(r, 0.03, 1.20)

        x = r * np.cos(theta)
        y = r * np.sin(theta)
        path = _smooth_closed_path(x, y)

        fill = palette[li % len(palette)]
        edge = palette[(li + 2) % len(palette)]
        alpha_fill = 0.06 + 0.09 * (1 - frac)
        alpha_edge = 0.10 + 0.10 * (0.5 - abs(frac - 0.5))

        ax.add_patch(
            PathPatch(
                path,
                facecolor=_with_alpha(fill, alpha_fill),
                edgecolor=_with_alpha(edge, alpha_edge),
                linewidth=0.6 if frac < 0.75 else 0.5,
                zorder=2,
                joinstyle="round",
                capstyle="round",
            )
        )

    # Fine ring engraving (many thin circles)
    ring_count = 22 + complexity * 4
    for i in range(ring_count):
        rr = 0.10 + (i / (ring_count - 1)) * 0.88
        c = palette[(i * 2) % len(palette)]
        lw = 0.25 + 0.45 * (1 - i / ring_count)
        ax.add_patch(
            Circle(
                (0, 0),
                rr,
                fill=False,
                linewidth=lw,
                edgecolor=_with_alpha(c, 0.14),
                zorder=3,
            )
        )

    # Filigree linework (rose curves)
    filigree_sets = 6 + complexity
    for i in range(filigree_sets):
        frac = i / max(1, filigree_sets - 1)
        base = 0.18 + frac * 0.78
        amp = 0.012 + (1 - frac) * 0.055
        m = symmetry * int(rng.integers(1, 6))
        phase = rng.random() * 2 * math.pi
        r = base + amp * np.cos(m * theta + phase)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        path = _smooth_closed_path(x, y)
        c = palette[(i + 1) % len(palette)]
        ax.add_patch(
            PathPatch(
                path,
                facecolor=(0, 0, 0, 0),
                edgecolor=_with_alpha(c, 0.22),
                linewidth=0.55,
                zorder=4,
                joinstyle="round",
                capstyle="round",
            )
        )

    # Dense petal spokes (layered)
    spoke_sets = 3 + complexity // 2
    for s in range(spoke_sets):
        n = symmetry * int(1 + s * 0.5)
        n = int(np.clip(n, 12, 120))
        rad = 0.16 + 0.14 * s
        width = 0.10 - 0.010 * s
        for j in range(n):
            ang = (j / n) * 2 * math.pi
            flare = 0.24 + 0.10 * math.sin(symmetry * ang)
            tip_r = rad + flare
            tip = (math.cos(ang) * tip_r, math.sin(ang) * tip_r)
            left = (
                math.cos(ang - width) * (rad + 0.06),
                math.sin(ang - width) * (rad + 0.06),
            )
            right = (
                math.cos(ang + width) * (rad + 0.06),
                math.sin(ang + width) * (rad + 0.06),
            )
            color = palette[(j + 2 * s) % len(palette)]
            ax.add_patch(
                Polygon(
                    np.array([left, tip, right]),
                    closed=True,
                    facecolor=_with_alpha(color, 0.10 + 0.06 * (s % 2)),
                    edgecolor=_with_alpha(theme.accent, 0.12),
                    linewidth=0.35,
                    zorder=5,
                    joinstyle="round",
                )
            )

    # Bead chains along multiple rings
    bead_rings = 7 + complexity
    for i in range(bead_rings):
        ring_r = 0.16 + (i / max(1, bead_rings - 1)) * 0.78
        n = int(symmetry * (5 + i * 1.5))
        n = int(np.clip(n, 40, 420))
        bead_size = 0.0028 + 0.0038 * (1 - i / bead_rings)
        for j in range(n):
            ang = (j / n) * 2 * math.pi
            jitter = (rng.random() - 0.5) * 0.0022
            x = (ring_r + jitter) * math.cos(ang)
            y = (ring_r + jitter) * math.sin(ang)
            c = palette[(i + j) % len(palette)]
            ax.add_patch(
                Circle(
                    (x, y),
                    bead_size,
                    facecolor=_with_alpha(c, 0.78),
                    edgecolor=_with_alpha(theme.accent, 0.14),
                    linewidth=0.18,
                    zorder=6,
                )
            )

    # Center jewel
    ax.add_patch(
        Circle(
            (0, 0),
            0.10,
            facecolor=_with_alpha(theme.accent, 0.55),
            edgecolor=_with_alpha(palette[0], 0.9),
            linewidth=1.3,
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

    # tiny sparkle dots near center
    for i in range(48 + complexity * 10):
        ang = rng.random() * 2 * math.pi
        rr = 0.02 + rng.random() * 0.16
        x = rr * math.cos(ang)
        y = rr * math.sin(ang)
        c = palette[i % len(palette)]
        ax.add_patch(
            Circle(
                (x, y),
                0.0015 + 0.0018 * rng.random(),
                facecolor=_with_alpha(c, 0.85),
                edgecolor=(0, 0, 0, 0),
                zorder=12,
            )
        )

    # Export
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format="png", bbox_inches="tight", pad_inches=0.10, facecolor=fig.get_facecolor())
    svg_bytes: bytes | None = None
    if export_svg:
        svg_buf = io.BytesIO()
        fig.savefig(svg_buf, format="svg", bbox_inches="tight", pad_inches=0.10, facecolor=fig.get_facecolor())
        svg_bytes = svg_buf.getvalue()
    plt.close(fig)

    return RenderResult(png=png_buf.getvalue(), svg=svg_bytes)

