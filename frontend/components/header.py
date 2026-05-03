"""
Top navbar — Logo + horizontal nav + user avatar / login, all in one row.

Fixes vs v1:
- option_menu icons removed (the strange play-arrow glyphs)
- nav-link white-space:nowrap so Shelter nav doesn't wrap into 2 lines
- guest CTA buttons are compact and don't break across lines
"""
import streamlit as st
from streamlit_option_menu import option_menu

from frontend.styles import COLOR_PRIMARY, COLOR_BG_SOFT, COLOR_BORDER, COLOR_TEXT_MUTED, logo_svg
from frontend.utils import auth


def render_navbar(nav_options: list[str], default_index: int = 0,
                  role_label: str | None = None) -> str:
    """Render the brand navbar and return the selected nav option label."""
    user = auth.current_user()
    display_name = (user.get("shelter_name") or user["username"]) if user else None
    initial = (display_name[:1].upper() if display_name else "?")

    # Wider nav column for shelter (more options); narrower for guest
    if user and user.get("role") == "shelter_manager":
        col_widths = [2.2, 5.5, 2.0]
    elif user is None:
        col_widths = [2.5, 4.0, 2.0]
    else:
        col_widths = [2.5, 4.5, 2.0]

    brand_col, nav_col, user_col = st.columns(col_widths, gap="medium")

    # ── Brand: logo + wordmark + optional role badge ────────────────────────
    with brand_col:
        # Render the wordmark + (optional) badge as a vertical stack so the
        # badge can sit right under the wordmark instead of being clipped at
        # the right edge of a narrow column.
        if role_label and user:
            wordmark_block = (
                f'<div style="display:flex;flex-direction:column;'
                f'justify-content:center;line-height:1;">'
                f'<span style="font-size:24px;font-weight:600;color:{COLOR_PRIMARY};'
                f'letter-spacing:-0.4px;white-space:nowrap;">AdoptSense</span>'
                f'<span style="font-size:10px;background:{COLOR_BG_SOFT};'
                f'color:{COLOR_PRIMARY};padding:2px 8px;border-radius:3px;'
                f'font-weight:600;letter-spacing:0.6px;margin-top:6px;'
                f'align-self:flex-start;">{role_label}</span>'
                f'</div>'
            )
        else:
            wordmark_block = (
                f'<span style="font-size:24px;font-weight:600;color:{COLOR_PRIMARY};'
                f'letter-spacing:-0.4px;line-height:1;white-space:nowrap;">AdoptSense</span>'
            )
        brand_html = (
            f'<div style="display:flex;align-items:center;gap:12px;'
            f'padding:10px 0 10px 8px;min-height:64px;overflow:visible;">'
            f'{logo_svg(40)}'
            f'{wordmark_block}'
            f'</div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)

    # ── Horizontal nav menu ─────────────────────────────────────────────────
    with nav_col:
        # Use empty icons list so option_menu doesn't add the default arrow icons.
        # Length must match nav_options.
        empty_icons = [""] * len(nav_options)
        # IMPORTANT: include default_index in the key so option_menu re-initializes
        # whenever the routed view changes. Without this, option_menu's internal
        # widget state remembers the previous selection (e.g. "Watchlist") and
        # returns it on a rerun where we wanted "Browse" — which then trips
        # the sync block in app.py and bounces the user back to the old view.
        # Tying the key to default_index forces a fresh widget per view.
        role_part = (role_label or "guest").lower().replace(" ", "_")
        menu_key = f"nav_menu_{role_part}_{default_index}"
        selected = option_menu(
            menu_title=None,
            options=nav_options,
            icons=empty_icons,
            default_index=default_index,
            orientation="horizontal",
            key=menu_key,
            styles={
                "container": {
                    "padding": "12px 0",
                    "background-color": "transparent",
                    "border": "none",
                    "margin": "0",
                },
                "icon": {"display": "none"},  # hard-hide any leftover icon space
                "nav-link": {
                    "font-size": "14px",
                    "font-weight": "400",
                    "color": COLOR_TEXT_MUTED,
                    "text-align": "center",
                    "margin": "0 6px",
                    "padding": "8px 6px",
                    "background-color": "transparent",
                    "border-bottom": "2px solid transparent",
                    "border-radius": "0",
                    "white-space": "nowrap",  # prevents 2-line wrapping
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

    # ── Right: avatar + name (logged in) OR login/register (guest) ──────────
    with user_col:
        if user:
            user_html = (
                f'<div style="display:flex;align-items:center;justify-content:flex-end;'
                f'gap:10px;padding:14px 8px 14px 0;height:64px;">'
                f'<div style="background:{COLOR_PRIMARY};color:#FFFFFF;width:36px;'
                f'height:36px;border-radius:50%;display:flex;align-items:center;'
                f'justify-content:center;font-size:14px;font-weight:500;flex-shrink:0;">'
                f'{initial}</div>'
                f'<span style="font-size:14px;color:#1F2937;font-weight:500;'
                f'white-space:nowrap;">{display_name}</span>'
                f'</div>'
            )
            st.markdown(user_html, unsafe_allow_html=True)
            if st.button("Log out", key="navbar_logout", use_container_width=True):
                auth.logout()
                st.rerun()
        else:
            # Compact CTA row — Register on the right (primary), Log In secondary
            st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
            login_col, reg_col = st.columns(2, gap="small")
            with login_col:
                if st.button("Log In", key="navbar_login",
                             type="secondary", use_container_width=True):
                    st.session_state.show_auth = "login"
                    st.rerun()
            with reg_col:
                if st.button("Register", key="navbar_register",
                             type="primary", use_container_width=True):
                    st.session_state.show_auth = "register"
                    st.rerun()

    # Bottom border under the whole strip
    st.markdown(
        f'<div style="height:1px;background:{COLOR_BORDER};margin:0 0 24px 0;"></div>',
        unsafe_allow_html=True,
    )

    return selected
