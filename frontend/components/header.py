"""
Top header — logo + wordmark on the left, optional role badge, user avatar on right.

The header uses class `.as-header-bar` (defined in styles.py) which has
a rounded top-only border, designed to sit visually flush against the
tab list below it. Together they form a single header strip.
"""
import streamlit as st

from frontend.styles import (
    COLOR_PRIMARY,
    COLOR_BG_SOFT,
    logo_svg,
)


def render_header(user_name: str = "Nora", role_label: str | None = None):
    initial = user_name[:1].upper() if user_name else "?"

    role_badge = ""
    if role_label:
        role_badge = (
            f'<span style="font-size:11px;background:{COLOR_BG_SOFT};'
            f'color:{COLOR_PRIMARY};padding:3px 8px;border-radius:4px;'
            f'font-weight:500;margin-left:10px;letter-spacing:0.5px;">'
            f'{role_label}</span>'
        )

    header_html = (
        f'<div class="as-header-bar">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'{logo_svg(32)}'
        f'<span style="font-size:20px;font-weight:600;color:{COLOR_PRIMARY};'
        f'letter-spacing:-0.3px;line-height:1;">AdoptSense</span>'
        f'{role_badge}'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div style="background:{COLOR_PRIMARY};color:#FFFFFF;width:32px;'
        f'height:32px;border-radius:50%;display:flex;align-items:center;'
        f'justify-content:center;font-size:13px;font-weight:500;">{initial}</div>'
        f'<span style="font-size:14px;color:#1F2937;font-weight:500;">{user_name}</span>'
        f'</div>'
        f'</div>'
    )

    st.markdown(header_html, unsafe_allow_html=True)
