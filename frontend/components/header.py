"""
Top navbar — Logo + horizontal nav + user avatar / login, all in one row.
Logo uses the actual PNG from assets/logo/; falls back to inline SVG.
Profile avatar is a clickable button that navigates to the profile view.
"""
import streamlit as st
from streamlit_option_menu import option_menu

from frontend.styles import (
    COLOR_PRIMARY, COLOR_BG_SOFT, COLOR_BORDER, COLOR_TEXT_MUTED,
    logo_img_tag,
)
from frontend.utils import auth


def render_navbar(nav_options: list[str], default_index: int = 0,
                  role_label: str | None = None) -> str:
    """Render the brand navbar and return the selected nav option label."""
    user = auth.current_user()
    display_name = (user.get("shelter_name") or user["username"]) if user else None
    initial = (display_name[:1].upper() if display_name else "?")

    if user and user.get("role") == "shelter_manager":
        col_widths = [2.2, 5.5, 2.2]
    elif user is None:
        col_widths = [2.5, 4.0, 2.0]
    else:
        col_widths = [2.5, 4.5, 2.2]

    brand_col, nav_col, user_col = st.columns(col_widths, gap="medium")

    # ── Brand: actual logo image + wordmark + optional role badge ─────────────
    with brand_col:
        logo_html = logo_img_tag(size=64)
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
            f'{logo_html}'
            f'{wordmark_block}'
            f'</div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)

    # ── Horizontal nav menu ───────────────────────────────────────────────────
    with nav_col:
        empty_icons = [""] * len(nav_options)
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
                "icon": {"display": "none"},
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
                    "white-space": "nowrap",
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

    # ── Right: profile popover OR guest login/register ────────────────────────
    with user_col:
        if user:
            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            is_manager = user.get("role") == "shelter_manager"
            with st.popover(
                f"{display_name} ▾",
                use_container_width=True,
            ):
                if st.button("👤 Profile", key="nav_pop_profile", use_container_width=True):
                    st.session_state.mp_view_before_profile = st.session_state.get("mp_view", "browse")
                    st.session_state.mp_view = "profile"
                    st.rerun()
                if is_manager:
                    if st.button("🔄 Update Index", key="nav_pop_update_index",
                                 use_container_width=True):
                        st.session_state["_trigger_backfill"] = True
                        st.rerun()
                if st.button("🚪 Log out", key="nav_pop_logout", use_container_width=True):
                    auth.logout()
                    st.rerun()
        else:
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

    st.markdown(
        f'<div style="height:1px;background:{COLOR_BORDER};margin:0 0 24px 0;"></div>',
        unsafe_allow_html=True,
    )

    return selected
