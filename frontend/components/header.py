"""
Top navbar — Logo + horizontal nav + user avatar / login, all in one row.

Uses streamlit-option-menu for the horizontal nav so it actually looks like a
real top navigation strip rather than Streamlit's default tab bar.

Returns the selected nav option string so app.py can route accordingly.
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

    brand_col, nav_col, user_col = st.columns([2.5, 4, 1.8], gap="medium")

    # ── Brand (logo + wordmark + optional role badge) ──────────────────────
    with brand_col:
        role_badge = ""
        if role_label and user:
            role_badge = (
                f'<span style="font-size:11px;background:{COLOR_BG_SOFT};'
                f'color:{COLOR_PRIMARY};padding:4px 10px;border-radius:4px;'
                f'font-weight:500;margin-left:10px;letter-spacing:0.5px;">'
                f'{role_label}</span>'
            )
        brand_html = (
            f'<div style="display:flex;align-items:center;gap:12px;'
            f'padding:14px 0 14px 8px;height:64px;">'
            f'{logo_svg(40)}'
            f'<span style="font-size:24px;font-weight:600;color:{COLOR_PRIMARY};'
            f'letter-spacing:-0.4px;line-height:1;">AdoptSense</span>'
            f'{role_badge}</div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)

    # ── Horizontal nav menu ─────────────────────────────────────────────────
    with nav_col:
        # Unique key per role to force a fresh menu after a role switch
        menu_key = f"nav_menu_{(role_label or 'guest').lower().replace(' ', '_')}"
        selected = option_menu(
            menu_title=None,
            options=nav_options,
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
                "nav-link": {
                    "font-size": "14px",
                    "font-weight": "400",
                    "color": COLOR_TEXT_MUTED,
                    "text-align": "center",
                    "margin": "0 8px",
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

    # ── Right side: avatar + name (logged in) OR login/register (guest) ─────
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
            # Logout button on its own row directly under the user info
            if st.button("Log out", key="navbar_logout", use_container_width=True):
                auth.logout()
                st.rerun()
        else:
            # Two compact CTAs for login / register
            st.markdown(
                '<div style="height:14px;"></div>', unsafe_allow_html=True
            )
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
