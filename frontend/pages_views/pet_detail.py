"""
Pet detail page — shown when an adopter clicks a pet card.
"""
import streamlit as st

from frontend.styles import (
    COLOR_PRIMARY,
    COLOR_BG_SOFT,
    COLOR_BORDER,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
)
from frontend.components.pet_card import PLACEHOLDER_GRADIENTS
from frontend.pages_views.demo_data import get_pet_by_name


def render_pet_detail_page():
    pet_name = st.session_state.get("selected_pet")
    pet = get_pet_by_name(pet_name) if pet_name else None

    if pet is None:
        st.warning("No pet selected.")
        if st.button("← Back to Browse", key="detail_back_missing_pet"):
            st.session_state.view = "browse"
            st.rerun()
        return

    # Back link with a unique key based on pet name
    if st.button("← Back to Browse", key=f"detail_back_{pet.name}"):
        st.session_state.view = "browse"
        st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.2, 1], gap="large")

    with left:
        _render_photo_gallery(pet)

    with right:
        _render_info_panel(pet)


def _render_photo_gallery(pet):
    main_gradient = PLACEHOLDER_GRADIENTS[pet.placeholder_index % len(PLACEHOLDER_GRADIENTS)]

    main_html = (
        f'<div style="aspect-ratio:4/3;background:{main_gradient};border-radius:14px;'
        f'position:relative;display:flex;align-items:center;justify-content:center;'
        f'margin-bottom:12px;">'
        f'<div style="position:absolute;top:16px;left:16px;background:{COLOR_PRIMARY};'
        f'color:#FFFFFF;padding:6px 14px;border-radius:6px;font-size:12px;'
        f'font-weight:500;letter-spacing:0.3px;">{pet.match_score}% MATCH</div>'
        f'<div style="position:absolute;top:16px;right:16px;background:rgba(255,255,255,0.95);'
        f'width:40px;height:40px;border-radius:50%;display:flex;align-items:center;'
        f'justify-content:center;">'
        f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        f'stroke="{COLOR_PRIMARY}" stroke-width="2">'
        f'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'
        f'</svg></div>'
        f'<span style="color:rgba(255,255,255,0.7);font-size:13px;'
        f'text-transform:uppercase;letter-spacing:1px;">Pet photo</span>'
        f'</div>'
    )
    st.markdown(main_html, unsafe_allow_html=True)

    # Build all four thumbnails as one HTML grid
    thumbs = []
    for i in range(4):
        gradient = PLACEHOLDER_GRADIENTS[(pet.placeholder_index + i) % len(PLACEHOLDER_GRADIENTS)]
        border = f"2px solid {COLOR_PRIMARY}" if i == 0 else f"1px solid {COLOR_BORDER}"
        thumbs.append(
            f'<div style="aspect-ratio:1;background:{gradient};'
            f'border-radius:8px;border:{border};"></div>'
        )
    grid_html = (
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">'
        f'{"".join(thumbs)}</div>'
    )
    st.markdown(grid_html, unsafe_allow_html=True)


def _render_info_panel(pet):
    age_label = (
        f"{int(pet.age_years)} yr{'s' if pet.age_years >= 2 else ''}"
        if pet.age_years >= 1
        else f"{int(pet.age_years * 12)} mo"
    )

    # Header: name + location + meta
    header_html = (
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
        f'margin-bottom:8px;">'
        f'<h1 style="font-size:36px;font-weight:600;color:{COLOR_PRIMARY};margin:0;'
        f'letter-spacing:-0.5px;">{pet.name}</h1>'
        f'<span style="font-size:14px;color:{COLOR_TEXT_MUTED};">📍 {pet.location}, PT</span>'
        f'</div>'
        f'<div style="font-size:15px;color:{COLOR_TEXT_BODY};margin-bottom:24px;">'
        f'{pet.breed} · {age_label} · {pet.gender} · {pet.weight_kg} kg</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # "Why we matched you" highlight
    match_html = (
        f'<div style="background:{COLOR_BG_SOFT};border-radius:12px;padding:18px;'
        f'margin-bottom:24px;">'
        f'<div style="font-size:12px;color:{COLOR_PRIMARY};font-weight:500;'
        f'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">'
        f'Why we matched you</div>'
        f'<div style="font-size:14px;color:{COLOR_PRIMARY};line-height:1.5;">'
        f'{pet.name} fits your active lifestyle and apartment-friendly preferences. '
        f'Their personality scores high on "good with first-time owners".</div>'
        f'</div>'
    )
    st.markdown(match_html, unsafe_allow_html=True)

    # About section
    about_html = (
        f'<h3 style="font-size:15px;font-weight:600;color:{COLOR_PRIMARY};'
        f'margin:0 0 10px;">About {pet.name}</h3>'
        f'<p style="font-size:14px;color:{COLOR_TEXT_BODY};line-height:1.6;'
        f'margin:0 0 24px;">{pet.description}. Well-trained, knows basic commands, '
        f'looking for a loving family.</p>'
    )
    st.markdown(about_html, unsafe_allow_html=True)

    # 2x2 info grid as ONE HTML block
    info_grid_html = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;'
        f'margin-bottom:24px;">'
        f'{_info_box_html("Health", "✓ " + pet.health)}'
        f'{_info_box_html("Adoption Fee", f"€{pet.fee_eur}")}'
        f'{_info_box_html("Good with", pet.good_with)}'
        f'{_info_box_html("Energy Level", pet.energy)}'
        f'</div>'
    )
    st.markdown(info_grid_html, unsafe_allow_html=True)

    # Shelter card
    initials = "".join([w[0] for w in pet.shelter_name.split()[:2]]).upper()
    verified_badge = ""
    if pet.shelter_verified:
        verified_badge = (
            ' <span style="color:#4CAF50;font-size:11px;">✓ Verified</span>'
        )
    shelter_html = (
        f'<div style="background:#F8F9FB;border:1px solid {COLOR_BORDER};'
        f'border-radius:12px;padding:14px;margin-bottom:20px;display:flex;'
        f'align-items:center;gap:12px;">'
        f'<div style="width:40px;height:40px;background:{COLOR_PRIMARY};'
        f'color:#FFFFFF;border-radius:50%;display:flex;align-items:center;'
        f'justify-content:center;font-weight:500;flex-shrink:0;font-size:13px;">'
        f'{initials}</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:13px;font-weight:500;color:{COLOR_PRIMARY};">'
        f'{pet.shelter_name}{verified_badge}</div>'
        f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};">'
        f'Listed {pet.listed_days_ago} days ago · Responds within 2h</div>'
        f'</div></div>'
    )
    st.markdown(shelter_html, unsafe_allow_html=True)

    # CTAs
    cta1, cta2 = st.columns([2, 1], gap="small")
    with cta1:
        if st.button("Contact Shelter", type="primary",
                     use_container_width=True,
                     key=f"detail_contact_{pet.name}"):
            st.success(f"Message sent to {pet.shelter_name}!")
    with cta2:
        if st.button("♡ Save", type="secondary",
                     use_container_width=True,
                     key=f"detail_save_{pet.name}"):
            st.toast(f"Saved {pet.name} to your watchlist")


def _info_box_html(label: str, value: str) -> str:
    """Return one info box as a minified HTML string."""
    return (
        f'<div style="background:#FFFFFF;border:1px solid {COLOR_BORDER};'
        f'border-radius:10px;padding:12px;">'
        f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};margin-bottom:4px;">'
        f'{label}</div>'
        f'<div style="font-size:14px;font-weight:500;color:{COLOR_PRIMARY};">'
        f'{value}</div></div>'
    )
