import base64
import os
from io import BytesIO

import streamlit as st
from openai import OpenAI
from PIL import Image

st.set_page_config(page_title="Word → Mandala Art", page_icon="🌀")

st.title("🌀 Word → Mandala Art")
st.write("Type **one word**, click **Generate**, and get a complex mandala image.")

# --- Get API key securely (never hard-code it) ---
# Streamlit Community Cloud uses st.secrets; locally you can use env var OPENAI_API_KEY.
api_key = None
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    st.warning(
        "Missing OpenAI API key.\n\n"
        "Local: set an environment variable OPENAI_API_KEY.\n"
        "Streamlit Cloud: add OPENAI_API_KEY in the app Secrets."
    )
    st.stop()

client = OpenAI(api_key=api_key)

word = st.text_input("Enter a word", placeholder="e.g., serenity", max_chars=40)

generate = st.button("Generate Mandala")

def build_prompt(w: str) -> str:
    # Prompt designed for "complex mandala" and good aesthetics.
    return (
        f"Create a highly detailed, symmetrical mandala inspired by the word '{w}'. "
        "Intricate linework, layered radial geometry, ornate patterns, crisp edges, "
        "high contrast, harmonious color palette, centered composition, "
        "white or subtle light background, studio-quality, ultra-detailed."
    )

if generate:
    w = (word or "").strip()
    if not w:
        st.error("Please type a word.")
        st.stop()

    with st.spinner("Generating mandala..."):
        try:
            # GPT Image models return base64-encoded image data. :contentReference[oaicite:2]{index=2}
            result = client.images.generate(
                model="gpt-image-1",
                prompt=build_prompt(w),
                size="1024x1024",
                # Optional knobs:
                quality="high",
            )

            # For GPT image models, the response includes base64 image data. :contentReference[oaicite:3]{index=3}
            b64 = result.data[0].b64_json
            img_bytes = base64.b64decode(b64)

            img = Image.open(BytesIO(img_bytes))

            st.subheader(f"Mandala for: {w}")
            st.image(img, use_container_width=True)

            st.download_button(
                label="Download PNG",
                data=img_bytes,
                file_name=f"mandala_{w.lower()}.png",
                mime="image/png",
            )

        except Exception as e:
            st.error("Something went wrong while generating the image.")
            st.caption(str(e))
