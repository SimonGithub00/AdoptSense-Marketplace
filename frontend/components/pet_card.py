"""
Pet card component for the browse grid.

CRITICAL: All HTML rendered via st.markdown is built as a single minified
string with no newlines inside attributes. Streamlit's markdown parser
is fragile around multi-line HTML inside unsafe_allow_html=True.
"""
import streamlit as st

from frontend.styles import COLOR_PRIMARY, COLOR_TEXT_MUTED, COLOR_BORDER


PLACEHOLDER_GRADIENTS = [
    "linear-gradient(135deg, #FCE5D8 0%, #F5C9A8 100%)",
    "linear-gradient(135deg, #E8DCC9 0%, #C9B89A 100%)",
    "linear-gradient(135deg, #D8E4F5 0%, #B0C4E0 100%)",
    "linear-gradient(135deg, #F5E1E8 0%, #E0B5C5 100%)",
    "linear-gradient(135deg, #E0F0E5 0%, #B5D8C0 100%)",
    "linear-gradient(135deg, #F0E8DC 0%, #D6C4A8 100%)",
]


def render_pet_card(
    pet_name: str,
    breed: str,
    age_years: float,
    gender: str,
    location: str,
    description: str,
    match_score: int | None = None,
    placeholder_index: int = 0,
    on_click_key: str | None = None,
):
    """Render one pet card as a single minified HTML block."""
    gradient = PLACEHOLDER_GRADIENTS[placeholder_index % len(PLACEHOLDER_GRADIENTS)]
    age_label = f"{int(age_years)} yr" if age_years >= 1 else f"{int(age_years * 12)} mo"

    match_badge = ""
    if match_score is not None:
        match_badge = (
            f'<div style="position:absolute;top:10px;left:10px;background:{COLOR_PRIMARY};'
            f'color:#FFFFFF;padding:3px 10px;border-radius:4px;font-size:10px;'
            f'font-weight:500;letter-spacing:0.3px;">{match_score}% MATCH</div>'
        )

    heart = (
        f'<div style="position:absolute;top:10px;right:10px;'
        f'background:rgba(255,255,255,0.95);width:30px;height:30px;'
        f'border-radius:50%;display:flex;align-items:center;justify-content:center;">'
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        f'stroke="{COLOR_PRIMARY}" stroke-width="2">'
        f'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'
        f'</svg></div>'
    )

    photo_box = (
        f'<div style="aspect-ratio:1;background:{gradient};position:relative;'
        f'display:flex;align-items:center;justify-content:center;">'
        f'{match_badge}{heart}'
        f'<span style="color:rgba(255,255,255,0.7);font-size:11px;'
        f'text-transform:uppercase;letter-spacing:1px;">photo</span>'
        f'</div>'
    )

    info_box = (
        f'<div style="padding:14px;flex:1;display:flex;flex-direction:column;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:6px;">'
        f'<span style="font-size:16px;font-weight:500;color:{COLOR_PRIMARY};">{pet_name}</span>'
        f'<span style="font-size:11px;color:{COLOR_TEXT_MUTED};">{location}</span>'
        f'</div>'
        f'<div style="font-size:12px;color:#4B5563;margin-bottom:8px;">'
        f'{breed} · {age_label} · {gender}</div>'
        f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};line-height:1.4;flex:1;">'
        f'{description}</div>'
        f'</div>'
    )

    card = (
        f'<div style="background:#FFFFFF;border:1px solid {COLOR_BORDER};'
        f'border-radius:12px;overflow:hidden;height:100%;display:flex;'
        f'flex-direction:column;margin-bottom:8px;">'
        f'{photo_box}{info_box}</div>'
    )

    st.markdown(card, unsafe_allow_html=True)

    # Action button below the card (Streamlit can't make HTML cards clickable)
    if on_click_key and st.button("View details", key=on_click_key,
                                   use_container_width=True):
        st.session_state.selected_pet = pet_name
        st.session_state.view = "pet_detail"
        st.rerun()
