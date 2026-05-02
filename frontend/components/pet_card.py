"""
Pet card component used by the browse grid.

Renders a single pet listing as a card with photo, name, meta, and an
optional adoption-speed badge (only shown to shelter managers per spec).
"""
import base64
from pathlib import Path

import streamlit as st

from frontend.styles import COLOR_PRIMARY, COLOR_TEXT_MUTED, COLOR_BORDER
from frontend.utils import db
from frontend.utils.matching_platform import (
    ADOPTION_SPEED_COLORS, ADOPTION_SPEED_LABELS, TYPE_MAP,
)


# Soft gradients used as placeholders when no real photo exists.
PLACEHOLDER_GRADIENTS = [
    "linear-gradient(135deg, #FCE5D8 0%, #F5C9A8 100%)",
    "linear-gradient(135deg, #E8DCC9 0%, #C9B89A 100%)",
    "linear-gradient(135deg, #D8E4F5 0%, #B0C4E0 100%)",
    "linear-gradient(135deg, #F5E1E8 0%, #E0B5C5 100%)",
    "linear-gradient(135deg, #E0F0E5 0%, #B5D8C0 100%)",
    "linear-gradient(135deg, #F0E8DC 0%, #D6C4A8 100%)",
]


def _img_to_data_uri(path: str) -> str | None:
    """Read an image from disk and return a base64 data URI, or None on error."""
    try:
        p = Path(path)
        if not p.exists():
            return None
        ext = p.suffix.lower().lstrip(".")
        mime = "image/png" if ext == "png" else "image/jpeg"
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"
    except Exception:
        return None


def render_pet_card(listing: dict, show_speed: bool = False, key_prefix: str = "pc"):
    """Render one pet card with a clickable 'View details' button below it.

    Args:
        listing: Row from db.get_listings() (dict)
        show_speed: True for shelter managers, False for adopters
        key_prefix: Unique prefix so the same listing can render in multiple grids
    """
    listing_id = listing["id"]
    pet_name = listing.get("pet_name", "—")
    pet_type = listing.get("type", 1)
    age_months = listing.get("age", 0)
    fee = listing.get("fee", 0)
    shelter_name = listing.get("shelter_name") or listing.get("shelter_username", "")

    # Try to load the first uploaded photo; fall back to a gradient
    photos = db.get_photos(listing_id)
    photo_uri = None
    for p in photos:
        # Prefer studio-ready version if available
        path = p.get("studio_photo_path") if p.get("is_studio_ready") else p.get("photo_path")
        photo_uri = _img_to_data_uri(path)
        if photo_uri:
            break

    # Build the photo / placeholder block
    if photo_uri:
        photo_block = (
            f'<div style="aspect-ratio:1;position:relative;overflow:hidden;">'
            f'<img src="{photo_uri}" alt="{pet_name}" '
            f'style="width:100%;height:100%;object-fit:cover;display:block;"/>'
            f'{_speed_badge_html(listing, show_speed)}'
            f'{_heart_button_html()}'
            f'</div>'
        )
    else:
        gradient = PLACEHOLDER_GRADIENTS[listing_id % len(PLACEHOLDER_GRADIENTS)]
        emoji = "🐶" if pet_type == 1 else "🐱"
        photo_block = (
            f'<div style="aspect-ratio:1;background:{gradient};position:relative;'
            f'display:flex;align-items:center;justify-content:center;font-size:3rem;">'
            f'{emoji}'
            f'{_speed_badge_html(listing, show_speed)}'
            f'{_heart_button_html()}'
            f'</div>'
        )

    # Meta block
    age_label = f"{int(age_months)} mo" if age_months < 24 else f"{int(age_months / 12)} yr"
    fee_label = "Free" if not fee or fee == 0 else f"€{int(fee)}"
    type_label = TYPE_MAP.get(pet_type, "Pet").split()[0]  # strip emoji

    info_block = (
        f'<div style="padding:14px;flex:1;display:flex;flex-direction:column;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'margin-bottom:6px;">'
        f'<span style="font-size:16px;font-weight:500;color:{COLOR_PRIMARY};">{pet_name}</span>'
        f'<span style="font-size:11px;color:{COLOR_TEXT_MUTED};">{fee_label}</span>'
        f'</div>'
        f'<div style="font-size:12px;color:#4B5563;margin-bottom:8px;">'
        f'{type_label} · {age_label}</div>'
        f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};line-height:1.4;flex:1;">'
        f'🏥 {shelter_name}</div>'
        f'</div>'
    )

    card = (
        f'<div style="background:#FFFFFF;border:1px solid {COLOR_BORDER};'
        f'border-radius:12px;overflow:hidden;height:100%;display:flex;'
        f'flex-direction:column;margin-bottom:8px;">'
        f'{photo_block}{info_block}</div>'
    )
    st.markdown(card, unsafe_allow_html=True)

    # Click target — Streamlit can't make HTML cards clickable, so this button
    # sits below each card. Visually it's tied to the card via the gap=0 layout.
    if st.button("View details", key=f"{key_prefix}_view_{listing_id}",
                 use_container_width=True):
        st.session_state.mp_view = "detail"
        st.session_state.mp_listing_id = listing_id
        st.rerun()


def _speed_badge_html(listing: dict, show_speed: bool) -> str:
    """Adoption-speed badge, only shown when show_speed=True (shelter view)."""
    if not show_speed:
        return ""
    speed = listing.get("adoption_speed_pred")
    if speed is None:
        return ""
    color = ADOPTION_SPEED_COLORS.get(speed, "#999")
    label = ADOPTION_SPEED_LABELS.get(speed, "?")
    return (
        f'<div style="position:absolute;top:10px;left:10px;background:{color};'
        f'color:#FFFFFF;padding:3px 10px;border-radius:4px;font-size:10px;'
        f'font-weight:500;letter-spacing:0.3px;">{label}</div>'
    )


def _heart_button_html() -> str:
    """Decorative heart icon (the actual save action sits on the detail page)."""
    return (
        f'<div style="position:absolute;top:10px;right:10px;'
        f'background:rgba(255,255,255,0.95);width:30px;height:30px;'
        f'border-radius:50%;display:flex;align-items:center;justify-content:center;">'
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        f'stroke="{COLOR_PRIMARY}" stroke-width="2">'
        f'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78'
        f'l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'
        f'</svg></div>'
    )
