# Word → Mandala (one-word mandala art generator)

A tiny zero-dependency web app: type **one word** and it generates a **deterministic mandala** on a canvas (same word → same art). You can also download the result as a PNG.

## Run locally

From the repo root:

```bash
python3 -m http.server 5173
```

Then open `http://localhost:5173` in your browser.

## Files

- `index.html`: UI (one word input + canvas)
- `styles.css`: styling
- `app.js`: deterministic mandala generator + PNG download

