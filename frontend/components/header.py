"""
Top navigation bar — Logo + horizontal nav menu + user avatar, all in one row.

Uses streamlit-option-menu for the horizontal nav links so it actually
looks like a real top navigation, not a Streamlit tab strip.

Returns the selected nav option so app.py can route to the right page.
"""
import streamlit as st
from streamlit_option_menu import option_menu

from frontend.styles import (
    COLOR_PRIMARY,
    COLOR_BG_SOFT,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    logo_svg,
)


def render_navbar(
    nav_options: list[str],
    user_name: str = "Nora",
    role_label: str | None = None,
    default_index: int = 0,
) -> str:
    """Render the full top navbar and return the selected nav option.

    Layout (all in one horizontal strip):
      [Logo + AdoptSense + optional badge] | [nav menu] | [avatar + name]

    Args:
        nav_options: list of nav labels, e.g. ["Home", "About", "Tools"]
        user_name: name shown next to avatar
        role_label: optional badge like "SHELTER"
        default_index: which nav option is selected by default

    Returns:
        The label of the currently selected nav option.
    """
    initial = user_name[:1].upper() if user_name else "?"

    # Three columns: brand (left), nav (center, flex), user (right)
    # Width ratios chosen so the nav has plenty of room while brand and user
    # stay compact.
    brand_col, nav_col, user_col = st.columns([2.5, 4, 1.5], gap="medium")

    with brand_col:
        role_badge = ""
        if role_label:
            role_badge = (
                f'<span style="font-size:11px;background:{COLOR_BG_SOFT};'
                f'color:{COLOR_PRIMARY};padding:4px 10px;border-radius:4px;'
                f'font-weight:500;margin-left:10px;letter-spacing:0.5px;">'
                f'{role_label}</span>'
            )

        # Logo bumped to 40px and wordmark to 24px for a stronger header feel
        brand_html = (
            f'<div style="display:flex;align-items:center;gap:12px;'
            f'padding:14px 0 14px 8px;height:64px;">'
            f'{logo_svg(40)}'
            f'<span style="font-size:24px;font-weight:600;color:{COLOR_PRIMARY};'
            f'letter-spacing:-0.4px;line-height:1;">AdoptSense</span>'
            f'{role_badge}'
            f'</div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)

    with nav_col:
        # option_menu gives us a real horizontal nav with active-state underline
        selected = option_menu(
            menu_title=None,
            options=nav_options,
            default_index=default_index,
            orientation="horizontal",
            key=f"nav_menu_{role_label or 'adopter'}",  # unique per role
            styles={
                "container": {
                    "padding": "12px 0",
                    "background-color": "transparent",
                    "border": "none",
                    "margin": "0",
                },
                "nav-link": {
                    "font-size": "14px",
                    "font-weight": "400",
                    "color": COLOR_TEXT_MUTED,
                    "text-align": "center",
                    "margin": "0 12px",
                    "padding": "8px 4px",
                    "background-color": "transparent",
                    "border-bottom": "2px solid transparent",
                    "border-radius": "0",
                    "--hover-color": "transparent",
                },
                "nav-link-selected": {
                    "background-color": "transparent",
                    "color": COLOR_PRIMARY,
                    "font-weight": "500",
                    "border-bottom": f"2px solid {COLOR_PRIMARY}",
                },
            },
        )

    with user_col:
        # Right-aligned avatar + name, vertically centered
        user_html = (
            f'<div style="display:flex;align-items:center;justify-content:flex-end;'
            f'gap:10px;padding:14px 8px 14px 0;height:64px;">'
            f'<div style="background:{COLOR_PRIMARY};color:#FFFFFF;width:36px;'
            f'height:36px;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;font-size:14px;font-weight:500;flex-shrink:0;">'
            f'{initial}</div>'
            f'<span style="font-size:14px;color:#1F2937;font-weight:500;'
            f'white-space:nowrap;">{user_name}</span>'
            f'</div>'
        )
        st.markdown(user_html, unsafe_allow_html=True)

    # Bottom border under the whole strip to make it feel like one nav bar
    st.markdown(
        f'<div style="height:1px;background:{COLOR_BORDER};margin:0 0 24px 0;"></div>',
        unsafe_allow_html=True,
    )

    return selected
