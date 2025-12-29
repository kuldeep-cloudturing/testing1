from __future__ import annotations

import json
import os
import time

import streamlit as st
from dotenv import load_dotenv

from mandala_art.generator import render_mandala
from mandala_art.openai_theme import get_theme_for_word


load_dotenv()

st.set_page_config(page_title="Word → Mandala Art", page_icon="🌀", layout="wide")


@st.cache_data(show_spinner=False)
def _cached_theme(word: str, model: str, use_openai: bool, api_key_present: bool) -> dict:
    # Don't cache the actual key; just whether one was present.
    # Theme content is safe to cache.
    if not use_openai or not api_key_present:
        # Force fallback even if OPENAI_API_KEY is set in env.
        t = get_theme_for_word(word, api_key="", model=model)
    else:
        # When api_key is present, the caller passes it directly (not part of cache key),
        # but we still cache based on word/model to avoid repeated calls during a session.
        # This is fine for a personal app; if you need strict per-key caching, remove this cache.
        t = get_theme_for_word(word, api_key=os.getenv("OPENAI_API_KEY"), model=model)
    return t.as_dict()


@st.cache_data(show_spinner=False)
def _cached_render(theme_json: str, seed: int, complexity: int, symmetry: int, size_px: int) -> tuple[bytes, bytes]:
    theme_dict = json.loads(theme_json)
    # Rehydrate minimal Theme-like object via get_theme_for_word normalization path:
    # easiest is to call get_theme_for_word fallback normalization by passing empty key,
    # but we already have the dict, so we import the normalizer directly.
    from mandala_art.utils import normalize_theme_dict

    theme = normalize_theme_dict(theme_dict.get("word", "mandala"), theme_dict)
    out = render_mandala(theme, seed=seed, complexity=complexity, symmetry=symmetry, size_px=size_px)
    return out.png, out.svg


st.title("Word → Mandala Art")
st.caption("Type a word, get a themed mandala. Uses OpenAI for palette/motifs (optional) + a deterministic mandala renderer.")

with st.sidebar:
    st.subheader("Settings")
    use_openai = st.toggle("Use OpenAI theming", value=True)
    api_key_input = st.text_input(
        "OpenAI API key (optional)",
        type="password",
        help="If empty, the app falls back to a deterministic palette based on the word.",
    )
    if api_key_input.strip():
        os.environ["OPENAI_API_KEY"] = api_key_input.strip()

    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    st.divider()

    complexity = st.slider("Complexity", min_value=1, max_value=10, value=6)
    symmetry = st.slider("Symmetry (rotations)", min_value=4, max_value=36, value=12, step=1)
    size_px = st.select_slider("Output size", options=[512, 768, 1024, 1536], value=1024)
    seed_mode = st.radio("Seed", options=["Random", "Fixed"], horizontal=True)
    seed = st.number_input("Seed value", min_value=0, max_value=2_000_000_000, value=42, step=1, disabled=(seed_mode == "Random"))


word = st.text_input("Enter a word (theme)", value="Serenity")

col_a, col_b = st.columns([1, 2], vertical_alignment="center")
with col_a:
    go = st.button("Generate mandala", type="primary", use_container_width=True)
with col_b:
    st.write("")

if go:
    if seed_mode == "Random":
        seed = int(time.time() * 1000) % 2_000_000_000

    api_key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())

    with st.spinner("Creating theme…"):
        theme_dict = _cached_theme(word=word, model=model, use_openai=use_openai, api_key_present=api_key_present)

    theme_json = json.dumps(theme_dict, sort_keys=True)

    with st.spinner("Rendering mandala…"):
        png_bytes, svg_bytes = _cached_render(
            theme_json=theme_json,
            seed=int(seed),
            complexity=int(complexity),
            symmetry=int(symmetry),
            size_px=int(size_px),
        )

    left, right = st.columns([3, 2], vertical_alignment="top")

    with left:
        st.image(png_bytes, caption=f'"{theme_dict.get("word","")}" — {theme_dict.get("mood","")}', use_container_width=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "Download PNG",
                data=png_bytes,
                file_name=f"mandala_{theme_dict.get('word','mandala').strip().lower().replace(' ','_')}.png",
                mime="image/png",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "Download SVG",
                data=svg_bytes,
                file_name=f"mandala_{theme_dict.get('word','mandala').strip().lower().replace(' ','_')}.svg",
                mime="image/svg+xml",
                use_container_width=True,
            )

    with right:
        st.subheader("Theme details")
        st.write(f"**Mood:** {theme_dict.get('mood','')}")
        st.write("**Motifs:** " + ", ".join(theme_dict.get("motifs", []) or []))

        st.write("**Palette:**")
        pal = theme_dict.get("palette", []) or []
        st.write(" ".join([f"`{c}`" for c in pal]))
        st.color_picker("Background", value=theme_dict.get("background", "#0B0B10"), disabled=True)
        st.color_picker("Accent", value=theme_dict.get("accent", pal[0] if pal else "#FFFFFF"), disabled=True)

        with st.expander("Raw theme JSON"):
            st.code(theme_json, language="json")

else:
    st.info("Enter a word, adjust settings, then click **Generate mandala**.")

