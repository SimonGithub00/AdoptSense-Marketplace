"""
Home / landing page for adopters.
"""
import base64
from pathlib import Path

import streamlit as st

from frontend.styles import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_BG_SOFT,
    COLOR_BORDER,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
)
from frontend.components.pet_card import render_pet_card
from frontend.pages_views.demo_data import DEMO_PETS


# ----------------------------------------------------------------------------
# Hero image loading
# ----------------------------------------------------------------------------
# Looks for a local file at frontend/assets/hero.jpeg (or .jpg / .png).
# Falls back to an Unsplash URL if no local file is found.
# This makes it easy to swap in a custom photo without touching code.

_FALLBACK_URL = (
    "https://images.unsplash.com/photo-1583337130417-3346a1be7dee"
    "?auto=format&fit=crop&w=800&q=80"
)


@st.cache_data
def _get_hero_image_src() -> str:
    """Return an <img src=...> value, using a local file if it exists.

    Why base64? Streamlit serves your app through a Tornado server. A naked
    relative path like 'frontend/assets/hero.jpeg' inside an <img src> won't
    resolve — the browser tries to fetch it from the Streamlit server's URL,
    not your filesystem. Base64-encoding the bytes embeds them directly into
    the HTML, which always works.
    """
    assets_dir = Path(__file__).parent.parent / "assets"
    for filename in ("hero.jpeg", "hero.jpg", "hero.png"):
        path = assets_dir / filename
        if path.exists():
            mime = "image/png" if filename.endswith(".png") else "image/jpeg"
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{data}"
    return _FALLBACK_URL


def render_home_page():
    """Render the full adopter-facing home page."""
    _render_hero()
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    _render_recommended_section()


def _render_hero():
    left, right = st.columns([1, 1], gap="large")

    with left:
        headline_html = (
            f'<h1 style="font-size:42px;font-weight:600;color:{COLOR_PRIMARY};'
            f'line-height:1.15;margin:0 0 16px;letter-spacing:-1px;">'
            f'Find your perfect companion faster.</h1>'
            f'<p style="font-size:16px;color:{COLOR_TEXT_BODY};line-height:1.6;'
            f'margin:0 0 28px;">AI-powered pet adoption that connects rescue '
            f'animals with loving homes — backed by a growing dataset of 15,000+ '
            f'adoptions, getting smarter with every match.</p>'
        )
        st.markdown(headline_html, unsafe_allow_html=True)

        features_html = _build_feature_cards()
        st.markdown(features_html, unsafe_allow_html=True)

        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

        cta1, cta2, _ = st.columns([1, 1, 2])
        with cta1:
            if st.button("Get Started →", type="primary",
                         use_container_width=True, key="hero_cta_primary"):
                st.session_state.view = "browse"
                st.rerun()
        with cta2:
            if st.button("Browse Pets", type="secondary",
                         use_container_width=True, key="hero_cta_secondary"):
                st.session_state.view = "browse"
                st.rerun()

    with right:
        # Larger hero image — bumped from 320 to 420 px and tightened margins
        hero_src = _get_hero_image_src()
        hero_img_html = (
            f'<div style="position:relative;display:flex;justify-content:center;'
            f'align-items:center;min-height:460px;">'
            f'<div style="position:absolute;width:420px;height:420px;'
            f'background:{COLOR_SECONDARY};border-radius:50%;opacity:0.5;"></div>'
            f'<img src="{hero_src}" alt="Pet" '
            f'style="position:relative;z-index:1;width:420px;height:420px;'
            f'object-fit:cover;border-radius:50%;border:8px solid #FFFFFF;'
            f'box-shadow:0 12px 48px rgba(30,39,97,0.18);"/>'
            f'</div>'
        )
        st.markdown(hero_img_html, unsafe_allow_html=True)


def _build_feature_cards() -> str:
    features = [
        ("M9 11l3 3L22 4 M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
         "AI Match", "Smart matching on lifestyle"),
        ("M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
         "Trusted Shelters", "Verified partners only"),
        ("M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4L12 14.01l-3-3",
         "Better Future", "Data-driven outcomes"),
    ]

    cards = []
    for icon_path, title, desc in features:
        card = (
            f'<div style="background:#FFFFFF;border:1px solid {COLOR_BORDER};'
            f'border-radius:10px;padding:16px;">'
            f'<div style="width:32px;height:32px;background:{COLOR_BG_SOFT};'
            f'border-radius:8px;display:flex;align-items:center;'
            f'justify-content:center;margin-bottom:8px;">'
            f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
            f'stroke="{COLOR_PRIMARY}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round"><path d="{icon_path}"/></svg></div>'
            f'<div style="font-size:13px;font-weight:500;color:{COLOR_PRIMARY};'
            f'margin-bottom:2px;">{title}</div>'
            f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};line-height:1.4;">'
            f'{desc}</div></div>'
        )
        cards.append(card)

    return (
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">'
        f'{"".join(cards)}</div>'
    )


def _render_recommended_section():
    header_html = (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:16px;">'
        f'<h2 style="font-size:22px;font-weight:600;color:{COLOR_PRIMARY};margin:0;">'
        f'Recommended for you</h2>'
        f'<span style="font-size:13px;color:{COLOR_TEXT_MUTED};">View all →</span>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    cols = st.columns(4, gap="medium")
    for idx, pet in enumerate(DEMO_PETS[:4]):
        with cols[idx]:
            render_pet_card(
                pet_name=pet.name,
                breed=pet.breed,
                age_years=pet.age_years,
                gender=pet.gender,
                location=pet.location,
                description=pet.description,
                match_score=pet.match_score,
                placeholder_index=pet.placeholder_index,
                on_click_key=f"home_view_{pet.name}",
            )
