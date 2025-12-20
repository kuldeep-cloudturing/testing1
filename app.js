/* Word → Mandala (deterministic)
   - Same word => same seed => same mandala
   - No dependencies; draws on a <canvas>
*/

/**
 * xmur3: string -> 32-bit seed function
 * https://github.com/bryc/code/blob/master/jshash/PRNGs.md (public domain style snippet)
 */
function xmur3(str) {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return h >>> 0;
  };
}

/**
 * mulberry32: 32-bit seed -> [0, 1) RNG
 * https://github.com/bryc/code/blob/master/jshash/PRNGs.md
 */
function mulberry32(a) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function pick(rng, arr) {
  return arr[Math.floor(rng() * arr.length)];
}

function hsl(h, s, l, a = 1) {
  return `hsla(${Math.round(h)} ${Math.round(s)}% ${Math.round(l)}% / ${a})`;
}

function sanitizeWord(raw) {
  const w = (raw || "").trim().split(/\s+/)[0] || "";
  // keep it as "one word", but allow unicode letters/digits and a few safe chars
  return w.slice(0, 32);
}

function computeSeed(word) {
  const seedFn = xmur3(word.toLowerCase());
  // stir a few rounds so short words differ more
  const s1 = seedFn();
  const s2 = seedFn();
  const s3 = seedFn();
  return (s1 ^ s2 ^ s3) >>> 0;
}

function setCanvasSize(canvas, desiredCSSPx) {
  const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
  const css = desiredCSSPx;
  canvas.style.width = `${css}px`;
  canvas.style.height = `${css}px`;
  canvas.width = Math.floor(css * dpr);
  canvas.height = Math.floor(css * dpr);
  return dpr;
}

function fitCanvasToContainer(canvas) {
  const wrap = canvas.parentElement;
  if (!wrap) return 1;
  const rect = wrap.getBoundingClientRect();
  // Keep square; leave some padding on small screens
  const size = clamp(Math.floor(rect.width), 320, 980);
  return setCanvasSize(canvas, size);
}

function drawBackground(ctx, w, h, rng, palette) {
  ctx.clearRect(0, 0, w, h);

  const g = ctx.createRadialGradient(w * 0.5, h * 0.48, w * 0.05, w * 0.5, h * 0.5, w * 0.55);
  g.addColorStop(0, hsl(palette.baseHue + 10, 70, 18, 0.92));
  g.addColorStop(0.55, hsl(palette.baseHue + 190, 65, 10, 0.9));
  g.addColorStop(1, "rgba(0,0,0,0.98)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  // soft film grain
  ctx.save();
  ctx.globalAlpha = 0.10;
  for (let i = 0; i < 2400; i++) {
    const x = rng() * w;
    const y = rng() * h;
    const a = 0.04 + rng() * 0.14;
    ctx.fillStyle = `rgba(255,255,255,${a})`;
    ctx.fillRect(x, y, 1, 1);
  }
  ctx.restore();
}

function makePalette(rng) {
  const baseHue = Math.floor(rng() * 360);
  const hue2 = (baseHue + 35 + rng() * 40) % 360;
  const hue3 = (baseHue + 180 + rng() * 50) % 360;
  const hue4 = (baseHue + 250 + rng() * 50) % 360;

  return {
    baseHue,
    ink: hsl(baseHue, 85, 70, 0.85),
    ink2: hsl(hue2, 88, 62, 0.85),
    ink3: hsl(hue3, 85, 62, 0.82),
    ink4: hsl(hue4, 88, 68, 0.82),
    gold: hsl((baseHue + 55) % 360, 90, 62, 0.9),
    white: "rgba(255,255,255,0.9)",
  };
}

function strokeGlow(ctx, color, lineWidth, glowColor, glowBlur) {
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.shadowColor = glowColor || color;
  ctx.shadowBlur = glowBlur ?? 10;
}

function fillGlow(ctx, color, glowColor, glowBlur) {
  ctx.fillStyle = color;
  ctx.shadowColor = glowColor || color;
  ctx.shadowBlur = glowBlur ?? 12;
}

function drawPetal(ctx, r0, r1, width, rng) {
  // petal centered on +Y axis (we’ll rotate around center)
  const c = 0.25 + rng() * 0.45;
  ctx.beginPath();
  ctx.moveTo(-width * 0.15, r0);
  ctx.bezierCurveTo(-width, r0 + (r1 - r0) * c, -width, r1, 0, r1);
  ctx.bezierCurveTo(width, r1, width, r0 + (r1 - r0) * c, width * 0.15, r0);
  ctx.closePath();
}

function drawArcBand(ctx, r0, r1, a0, a1) {
  ctx.beginPath();
  ctx.arc(0, 0, r1, a0, a1);
  ctx.arc(0, 0, r0, a1, a0, true);
  ctx.closePath();
}

function drawDot(ctx, r, size) {
  ctx.beginPath();
  ctx.arc(0, -r, size, 0, Math.PI * 2);
  ctx.closePath();
}

function drawMandala(ctx, word, seed, options) {
  const w = ctx.canvas.width;
  const h = ctx.canvas.height;

  const rng = mulberry32(seed);
  const palette = makePalette(rng);
  drawBackground(ctx, w, h, rng, palette);

  // coordinate system
  ctx.save();
  ctx.translate(w / 2, h / 2);

  const minDim = Math.min(w, h);
  const R = minDim * 0.44;

  // global slight rotation so it doesn't look perfectly upright
  ctx.rotate((rng() - 0.5) * 0.18);

  const segments = clamp(Math.floor(8 + rng() * 18), 8, 26);
  const layers = clamp(Math.floor(7 + rng() * 7), 7, 14);
  const step = (Math.PI * 2) / segments;

  // guide ring glow
  ctx.save();
  strokeGlow(ctx, hsl(palette.baseHue, 80, 70, 0.12), minDim * 0.0022, hsl(palette.baseHue, 90, 70, 0.18), 18);
  ctx.beginPath();
  ctx.arc(0, 0, R * 0.98, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();

  const inks = [palette.ink, palette.ink2, palette.ink3, palette.ink4, palette.gold, palette.white];

  for (let li = 0; li < layers; li++) {
    const t = li / (layers - 1);
    const r0 = R * (0.07 + t * 0.85);
    const r1 = r0 + R * (0.05 + rng() * 0.10);
    const stroke = pick(rng, inks);
    const fill = pick(rng, inks);

    const kind = pick(rng, ["petal", "band", "rays", "dots", "triangles"]);
    const lw = minDim * (0.0012 + rng() * 0.0026);

    for (let si = 0; si < segments; si++) {
      ctx.save();
      ctx.rotate(si * step);

      if (kind === "petal") {
        const width = R * (0.05 + rng() * 0.12);
        drawPetal(ctx, r0, r1, width, rng);
        ctx.globalAlpha = 0.85;
        fillGlow(ctx, hsl(palette.baseHue + li * 12 + si * 2, 88, 58, 0.14 + rng() * 0.20), fill, 14);
        ctx.fill();
        ctx.globalAlpha = 0.95;
        strokeGlow(ctx, stroke, lw, stroke, 14);
        ctx.stroke();
      } else if (kind === "band") {
        const span = step * (0.70 + rng() * 0.20);
        const a0 = -span / 2;
        const a1 = span / 2;
        drawArcBand(ctx, r0, r1, a0, a1);
        ctx.globalAlpha = 0.8;
        fillGlow(ctx, hsl(palette.baseHue + 160 + li * 7, 85, 55, 0.08 + rng() * 0.16), fill, 12);
        ctx.fill();
        ctx.globalAlpha = 0.95;
        strokeGlow(ctx, stroke, lw, stroke, 12);
        ctx.stroke();
      } else if (kind === "rays") {
        const rayCount = clamp(Math.floor(2 + rng() * 6), 2, 7);
        strokeGlow(ctx, stroke, lw, stroke, 12);
        for (let ri = 0; ri < rayCount; ri++) {
          const a = (-step * 0.32) + (ri / (rayCount - 1 || 1)) * (step * 0.64);
          const rr0 = r0 * (0.96 + rng() * 0.08);
          const rr1 = r1 * (0.96 + rng() * 0.08);
          ctx.beginPath();
          ctx.moveTo(Math.sin(a) * rr0, -Math.cos(a) * rr0);
          ctx.lineTo(Math.sin(a) * rr1, -Math.cos(a) * rr1);
          ctx.globalAlpha = 0.6 + rng() * 0.35;
          ctx.stroke();
        }
      } else if (kind === "dots") {
        const dotCount = clamp(Math.floor(2 + rng() * 5), 2, 6);
        for (let di = 0; di < dotCount; di++) {
          const rr = r0 + (r1 - r0) * (di / (dotCount - 1 || 1));
          const size = minDim * (0.0022 + rng() * 0.0046);
          drawDot(ctx, rr, size);
          ctx.globalAlpha = 0.55 + rng() * 0.38;
          fillGlow(ctx, pick(rng, inks), pick(rng, inks), 16);
          ctx.fill();
          ctx.globalAlpha = 0.85;
          strokeGlow(ctx, "rgba(255,255,255,0.18)", lw * 0.8, "rgba(255,255,255,0.16)", 10);
          ctx.stroke();
        }
      } else if (kind === "triangles") {
        const tw = R * (0.03 + rng() * 0.09);
        const tip = r1 * (0.96 + rng() * 0.08);
        const base = r0 * (0.96 + rng() * 0.08);
        ctx.beginPath();
        ctx.moveTo(0, -tip);
        ctx.lineTo(-tw, -base);
        ctx.lineTo(tw, -base);
        ctx.closePath();
        ctx.globalAlpha = 0.70;
        fillGlow(ctx, hsl(palette.baseHue + 40 + li * 11, 86, 54, 0.10 + rng() * 0.18), fill, 14);
        ctx.fill();
        ctx.globalAlpha = 0.95;
        strokeGlow(ctx, stroke, lw, stroke, 12);
        ctx.stroke();
      }

      ctx.restore();
    }
  }

  // center rosette
  ctx.save();
  const centerPetals = clamp(Math.floor(10 + rng() * 18), 10, 30);
  const cStep = (Math.PI * 2) / centerPetals;
  for (let i = 0; i < centerPetals; i++) {
    ctx.save();
    ctx.rotate(i * cStep);
    const r0 = R * 0.02;
    const r1 = R * (0.10 + rng() * 0.08);
    const width = R * (0.03 + rng() * 0.05);
    drawPetal(ctx, r0, r1, width, rng);
    ctx.globalAlpha = 0.9;
    fillGlow(ctx, hsl(palette.baseHue + i * 7, 90, 60, 0.16), palette.ink, 14);
    ctx.fill();
    ctx.globalAlpha = 0.95;
    strokeGlow(ctx, palette.white, minDim * 0.0016, palette.white, 12);
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();

  // center dot
  ctx.save();
  ctx.globalAlpha = 0.95;
  fillGlow(ctx, palette.gold, palette.gold, 18);
  ctx.beginPath();
  ctx.arc(0, 0, R * 0.018, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.restore();

  // subtle word signature (hidden-ish)
  if (options?.signature) {
    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.font = `${Math.max(12, Math.floor(w * 0.02))}px ui-sans-serif, system-ui`;
    ctx.textAlign = "center";
    ctx.fillText(word, w / 2, h - Math.max(14, Math.floor(w * 0.03)));
    ctx.restore();
  }
}

function main() {
  const canvas = document.getElementById("mandalaCanvas");
  const form = document.getElementById("wordForm");
  const input = document.getElementById("wordInput");
  const downloadBtn = document.getElementById("downloadBtn");
  const seedLabel = document.getElementById("seedLabel");

  if (!canvas || !form || !input || !downloadBtn || !seedLabel) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  function renderFromInput() {
    const word = sanitizeWord(input.value);
    if (!word) return;
    const seed = computeSeed(word);
    fitCanvasToContainer(canvas);
    // We draw in device pixels (canvas.width/height), so keep the default transform.
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    drawMandala(ctx, word, seed, { signature: true });
    seedLabel.textContent = `Seed: ${seed} • Segments & layers are derived from the word`;
  }

  // Resize handling
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => renderFromInput(), 60);
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    input.value = sanitizeWord(input.value);
    renderFromInput();
  });

  input.addEventListener("input", () => {
    // live preview after a tiny debounce
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      if (sanitizeWord(input.value)) renderFromInput();
    }, 250);
  });

  downloadBtn.addEventListener("click", () => {
    const word = sanitizeWord(input.value);
    if (!word) return;
    const safeName = word.replace(/[^a-z0-9_-]+/gi, "_");
    const a = document.createElement("a");
    a.download = `mandala-${safeName || "mandala"}.png`;
    a.href = canvas.toDataURL("image/png");
    a.click();
  });

  // Default word
  input.value = "harmony";
  renderFromInput();
  input.focus();
  input.select();
}

document.addEventListener("DOMContentLoaded", main);
