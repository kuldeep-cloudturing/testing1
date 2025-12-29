## Word → Mandala Art (Streamlit)

This is a small Streamlit app that:
- takes a **single word**
- uses **OpenAI (optional, automatic)** to generate a themed **color palette + motifs**
- renders a **deterministic mandala** (PNG) using the theme

### Files

- `app.py`: Streamlit UI
- `mandala_art/openai_theme.py`: OpenAI “word → theme JSON” (with fallback)
- `mandala_art/generator.py`: mandala renderer (matplotlib)
- `mandala_art/utils.py`: palette + theme utilities
- `requirements.txt`: dependencies
- `.env.example`: environment variable template

### Setup

Create a virtual environment and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### OpenAI API key

Option A (recommended): create a `.env` file:

```bash
cp .env.example .env
```

Then set:

- `OPENAI_API_KEY`
- (optional) `OPENAI_MODEL` (default is `gpt-4o-mini`)

If no key is provided, the app still works using a deterministic fallback palette based on the word.

### Run

```bash
python3 -m streamlit run app.py
```

### Notes

- The renderer is **deterministic** when you use a fixed seed.
- You can download both **PNG** and **SVG** from the app.

