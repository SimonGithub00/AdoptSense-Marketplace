"""
Pet card component used by the browse grid.

IMPORTANT: this version uses native Streamlit primitives (st.container,
st.image, st.button) instead of one big HTML markdown blob. The previous
HTML-only version visually looked nicer but Streamlit's iframe-style
markdown container was swallowing click events on the "View details"
button beneath it. Native components don't have that problem.
"""
import base64
from pathlib import Path

import streamlit as st

from frontend.styles import COLOR_PRIMARY, COLOR_TEXT_MUTED, COLOR_BORDER
from frontend.utils import db
from frontend.utils.matching_platform import (
    ADOPTION_SPEED_COLORS, ADOPTION_SPEED_LABELS, TYPE_MAP,
)


# Soft gradient backgrounds for placeholder tiles (when no photo exists)
PLACEHOLDER_GRADIENTS = [
    "linear-gradient(135deg, #FCE5D8 0%, #F5C9A8 100%)",
    "linear-gradient(135deg, #E8DCC9 0%, #C9B89A 100%)",
    "linear-gradient(135deg, #D8E4F5 0%, #B0C4E0 100%)",
    "linear-gradient(135deg, #F5E1E8 0%, #E0B5C5 100%)",
    "linear-gradient(135deg, #E0F0E5 0%, #B5D8C0 100%)",
    "linear-gradient(135deg, #F0E8DC 0%, #D6C4A8 100%)",
]


def _photo_bytes(listing_id: int) -> bytes | None:
    """Return the first available photo bytes for a listing, or None."""
    for p in db.get_photos(listing_id):
        # Prefer studio-ready version if available
        path = p.get("studio_photo_path") if p.get("is_studio_ready") else p.get("photo_path")
        if not path:
            continue
        try:
            return Path(path).read_bytes()
        except Exception:
            continue
    return None


def render_pet_card(listing: dict, show_speed: bool = False, key_prefix: str = "pc",
                    compatibility_pct: float | None = None):
    """Render a single pet card with a working 'View details' button."""
    listing_id = listing["id"]
    pet_name = listing.get("pet_name", "—")
    pet_type = listing.get("type", 1)
    age_months = listing.get("age", 0) or 0
    fee = listing.get("fee", 0) or 0
    shelter_name = listing.get("shelter_name") or listing.get("shelter_username", "")
    speed = listing.get("adoption_speed_pred") if show_speed else None

    age_label = f"{int(age_months)} mo" if age_months < 24 else f"{int(age_months / 12)} yr"
    fee_label = "Free" if fee == 0 else f"€{int(fee)}"
    type_label = TYPE_MAP.get(pet_type, "Pet").split()[0]  # strip emoji

    with st.container(border=True):
        # ── Photo (or placeholder) ──────────────────────────────────────────
        photo_bytes = _photo_bytes(listing_id)
        if photo_bytes:
            st.image(photo_bytes, width='stretch')
        else:
            gradient = PLACEHOLDER_GRADIENTS[listing_id % len(PLACEHOLDER_GRADIENTS)]
            emoji = "🐶" if pet_type == 1 else "🐱"
            st.markdown(
                f'<div style="background:{gradient};border-radius:6px;'
                f'padding:48px 0;text-align:center;font-size:48px;line-height:1;'
                f'margin-bottom:8px;">{emoji}</div>',
                unsafe_allow_html=True,
            )

        # ── AI enhancement badge (opal/glass style) ──────────────────────────
        photos_data = db.get_photos(listing_id)
        has_studio = any(p.get("is_studio_ready") for p in photos_data)
        has_ai_desc = bool(listing.get("description_improved"))
        if has_studio or has_ai_desc:
            badges = []
            if has_studio:
                badges.append("✨ Photo enhanced")
            if has_ai_desc:
                badges.append("✨ Description enhanced")
            badge_text = " · ".join(badges)
            st.markdown(
                f'<div style="display:inline-block;background:rgba(255,255,255,0.82);'
                f'backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);'
                f'border:1px solid rgba(30,39,97,0.18);border-radius:4px;'
                f'padding:2px 7px;font-size:10px;color:#1E2761;font-weight:500;'
                f'letter-spacing:0.2px;margin-bottom:4px;">'
                f'{badge_text}</div>',
                unsafe_allow_html=True,
            )

        # ── Speed + confidence badge for shelter managers ───────────────────
        if speed is not None:
            color = ADOPTION_SPEED_COLORS.get(speed, "#999")
            label = ADOPTION_SPEED_LABELS.get(speed, "?")
            st.markdown(
                f'<span style="background:{color};color:#FFFFFF;padding:2px 10px;'
                f'border-radius:4px;font-size:11px;font-weight:500;'
                f'letter-spacing:0.3px;">{label}</span>',
                unsafe_allow_html=True,
            )

        # ── Compatibility badge (smart filter) ─────────────────────────────
        if compatibility_pct is not None:
            pct = int(round(compatibility_pct))
            if pct >= 75:
                bg, fg = "#1E7A4A", "#FFFFFF"
            elif pct >= 50:
                bg, fg = "#2A7AB8", "#FFFFFF"
            else:
                bg, fg = "#6B7280", "#FFFFFF"
            st.markdown(
                f'<span style="background:{bg};color:{fg};padding:2px 10px;'
                f'border-radius:4px;font-size:11px;font-weight:500;'
                f'letter-spacing:0.3px;">{pct}% match</span>',
                unsafe_allow_html=True,
            )

        # ── Pet name + fee ─────────────────────────────────────────────────
        name_html = (
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;margin:8px 0 4px;">'
            f'<span style="font-size:16px;font-weight:500;color:{COLOR_PRIMARY};">'
            f'{pet_name}</span>'
            f'<span style="font-size:12px;color:{COLOR_TEXT_MUTED};">{fee_label}</span>'
            f'</div>'
        )
        st.markdown(name_html, unsafe_allow_html=True)

        # ── Type · age ──────────────────────────────────────────────────────
        meta_html = (
            f'<div style="font-size:12px;color:#4B5563;margin-bottom:6px;">'
            f'{type_label} · {age_label}</div>'
        )
        st.markdown(meta_html, unsafe_allow_html=True)

        # ── Shelter ─────────────────────────────────────────────────────────
        if shelter_name:
            shelter_html = (
                f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};'
                f'margin-bottom:10px;">🏥 {shelter_name}</div>'
            )
            st.markdown(shelter_html, unsafe_allow_html=True)

        # ── View details button ────────────────────────────────────────────
        if st.button("View details", key=f"{key_prefix}_view_{listing_id}",
                     use_container_width=True, type="secondary"):
            st.session_state.mp_view = "detail"
            st.session_state.mp_listing_id = listing_id
            st.rerun()