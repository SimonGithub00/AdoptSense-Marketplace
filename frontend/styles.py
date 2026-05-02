"""
AdoptSense — central styling and shared visual constants.
All brand colors, the logo SVG, and the global CSS live here.
"""
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


def logo_svg(size: int = 40) -> str:
    """Return the AdoptSense heart-paw logo as an inline SVG string."""
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

    /* Hide Streamlit chrome we don't want to show */
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

    /* Tabs (used inside marketplace sub-views) */
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
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
