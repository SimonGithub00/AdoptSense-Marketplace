"""
AdoptSense — central styling and shared visual constants.
All brand colors, the actual logo, and the global CSS live here.
"""
import base64
from pathlib import Path

import streamlit as st

# Brand palette
COLOR_PRIMARY = "#1E2761"        # Navy
COLOR_PRIMARY_LIGHT = "#2A3878"  # Hover/gradient
COLOR_SECONDARY = "#CADCFC"      # Ice blue
COLOR_BG_PAGE = "#FAFBFD"
COLOR_BG_CARD = "#FFFFFF"
COLOR_BG_SOFT = "#EEF1F8"        # Soft tinted background for AI highlights
COLOR_BORDER = "#E5E7EB"
COLOR_TEXT_MUTED = "#6B7280"
COLOR_TEXT_BODY = "#4B5563"

# Adoption-speed colors (only used inside the shelter manager view)
SPEED_COLORS = {
    0: "#4CAF50",
    1: "#8BC34A",
    2: "#FFC107",
    3: "#FF9800",
    4: "#F44336",
}

_LOGO_DIR = Path(__file__).parent / "assets" / "logo"
_LOGO_PNG = _LOGO_DIR / "AdoptSense Logo_best quality_png.png"
_LOGO_SVG = _LOGO_DIR / "AdoptSense Logo_best quality_svg.svg"


@st.cache_data
def logo_png_b64() -> str | None:
    """Return the logo PNG as a base64 data-URI string, or None."""
    try:
        data = _LOGO_PNG.read_bytes()
        return base64.b64encode(data).decode("ascii")
    except Exception:
        return None


@st.cache_data
def logo_svg_content() -> str | None:
    """Return raw SVG content of the logo, or None."""
    try:
        return _LOGO_SVG.read_text(encoding="utf-8")
    except Exception:
        return None


def logo_img_tag(size: int = 40, css_class: str = "") -> str:
    """Return an <img> or inline <svg> tag for the logo, sized in px."""
    b64 = logo_png_b64()
    if b64:
        cls = f' class="{css_class}"' if css_class else ""
        return (
            f'<img src="data:image/png;base64,{b64}" '
            f'width="{size}" height="{size}" '
            f'style="object-fit:contain;display:block;flex-shrink:0;"{cls} alt="AdoptSense logo"/>'
        )
    # Fallback: inline SVG path drawing
    return logo_svg_fallback(size)


def logo_svg_fallback(size: int = 40) -> str:
    """Minimal inline SVG fallback when logo file is unavailable."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;flex-shrink:0;">'
        f'<path d="M16 26 C16 26, 4 18, 4 11 C4 7, 7 5, 10 5 C13 5, 16 8, 16 11 L16 26 Z" '
        f'fill="{COLOR_PRIMARY}"/>'
        f'<path d="M16 26 C16 26, 28 18, 28 11 C28 7, 25 5, 22 5 C19 5, 16 8, 16 11 L16 26 Z" '
        f'fill="{COLOR_SECONDARY}" stroke="{COLOR_PRIMARY}" stroke-width="1.5"/>'
        f'<circle cx="16" cy="13" r="2.5" fill="#FFFFFF"/>'
        f'<circle cx="13" cy="9" r="1.2" fill="{COLOR_PRIMARY}"/>'
        f'<circle cx="19" cy="9" r="1.2" fill="{COLOR_PRIMARY}"/>'
        f'</svg>'
    )


def logo_svg(size: int = 40) -> str:
    """Return the best available logo as an HTML string (PNG preferred)."""
    return logo_img_tag(size)


def inject_global_css():
    """Inject brand CSS. Call once near the top of app.py."""
    css = f"""
    <style>
    .stApp {{ background: {COLOR_BG_PAGE}; }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    /* Hide Streamlit chrome we don't want */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    section[data-testid="stSidebar"] {{ display: none; }}

    /* Typography */
    h1, h2, h3, h4 {{
        color: {COLOR_PRIMARY};
        letter-spacing: -0.3px;
    }}
    h1 {{ font-weight: 600 !important; }}

    /* Primary buttons */
    .stButton > button[kind="primary"] {{
        background: {COLOR_PRIMARY};
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
        padding: 10px 22px;
        font-weight: 500;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {COLOR_PRIMARY_LIGHT};
        color: #FFFFFF;
        border: none;
    }}
    .stButton > button[kind="secondary"] {{
        background: #FFFFFF;
        color: {COLOR_PRIMARY};
        border: 1px solid {COLOR_PRIMARY};
        border-radius: 10px;
        padding: 10px 22px;
        font-weight: 500;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: {COLOR_BG_SOFT};
        color: {COLOR_PRIMARY};
        border: 1px solid {COLOR_PRIMARY};
    }}

    /* Bordered containers */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 12px;
        border-color: {COLOR_BORDER} !important;
        background: {COLOR_BG_CARD};
    }}

    /* Inputs */
    input[type="text"], input[type="number"], input[type="password"],
    input[type="email"], textarea,
    .stSelectbox > div > div, .stTextInput > div > div {{
        border-radius: 8px !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 24px;
        border-bottom: 1px solid {COLOR_BORDER};
        background: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 8px 4px;
        font-size: 14px;
        color: {COLOR_TEXT_BODY};
        background: transparent;
    }}
    .stTabs [aria-selected="true"] {{
        color: {COLOR_PRIMARY} !important;
        font-weight: 500;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {COLOR_PRIMARY} !important;
        height: 2px !important;
    }}

    /* File uploader */
    [data-testid="stFileUploader"] section {{
        border-radius: 10px;
        border: 1px dashed {COLOR_BORDER};
        background: {COLOR_BG_SOFT};
    }}

    /* Publish success animation */
    @keyframes as_success_pop {{
        0%   {{ transform: scale(0.5); opacity: 0; }}
        60%  {{ transform: scale(1.15); opacity: 1; }}
        80%  {{ transform: scale(0.95); }}
        100% {{ transform: scale(1); }}
    }}
    .as-success-icon {{
        animation: as_success_pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        display: inline-block;
    }}

    /* Confetti dots */
    @keyframes as_confetti_fall {{
        0%   {{ transform: translateY(-20px) rotate(0deg); opacity: 1; }}
        100% {{ transform: translateY(120px) rotate(360deg); opacity: 0; }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
