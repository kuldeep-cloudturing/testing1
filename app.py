from __future__ import annotations

import json
import os

import streamlit as st
from dotenv import load_dotenv

from mandala_art.generator import render_mandala
from mandala_art.openai_theme import get_theme_for_word
from mandala_art.utils import stable_int_hash


load_dotenv()

st.set_page_config(page_title="Word → Mandala Art", page_icon="🌀", layout="wide")


@st.cache_data(show_spinner=False)
def _cached_theme(word: str, model: str, api_key_present: bool) -> dict:
    # Don't cache the actual key; just whether one was present.
    if api_key_present:
        t = get_theme_for_word(word, api_key=os.getenv("OPENAI_API_KEY"), model=model)
    else:
        t = get_theme_for_word(word, api_key="", model=model)
    return t.as_dict()


@st.cache_data(show_spinner=False)
def _cached_render(theme_json: str, seed: int, complexity: int, symmetry: int, size_px: int) -> bytes:
    theme_dict = json.loads(theme_json)
    # Rehydrate minimal Theme-like object via get_theme_for_word normalization path:
    # easiest is to call get_theme_for_word fallback normalization by passing empty key,
    # but we already have the dict, so we import the normalizer directly.
    from mandala_art.utils import normalize_theme_dict

    theme = normalize_theme_dict(theme_dict.get("word", "mandala"), theme_dict)
    out = render_mandala(theme, seed=seed, complexity=complexity, symmetry=symmetry, size_px=size_px, export_svg=False)
    return out.png


st.title("Word → Mandala Art")
st.caption("Enter a word → get a themed mandala. (OpenAI theming is used automatically if `OPENAI_API_KEY` is set.)")

word = st.text_input("Word", value="", placeholder="e.g. Serenity, Ocean, Diwali, Lotus")
go = st.button("Generate mandala", type="primary")

if go:
    word = (word or "").strip()
    if not word:
        st.warning("Please enter a word.")
        st.stop()

    api_key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    seed = stable_int_hash(word) % 2_000_000_000

    with st.spinner("Creating theme…"):
        theme_dict = _cached_theme(word=word, model=model, api_key_present=api_key_present)

    theme_json = json.dumps(theme_dict, sort_keys=True)

    with st.spinner("Rendering mandala…"):
        png_bytes = _cached_render(
            theme_json=theme_json,
            seed=int(seed),
            complexity=8,
            symmetry=16,
            size_px=1024,
        )

    st.image(png_bytes, caption=f'"{theme_dict.get("word","")}" — {theme_dict.get("mood","")}', use_container_width=True)
    st.download_button(
        "Download PNG",
        data=png_bytes,
        file_name=f"mandala_{theme_dict.get('word','mandala').strip().lower().replace(' ','_')}.png",
        mime="image/png",
    )

else:
    st.info("Type a word and click **Generate mandala**.")

