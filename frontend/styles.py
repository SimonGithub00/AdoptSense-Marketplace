"""
AdoptSense — central styling and shared visual constants.
"""
import streamlit as st


# Brand colors
COLOR_PRIMARY = "#1E2761"
COLOR_PRIMARY_LIGHT = "#2A3878"
COLOR_SECONDARY = "#CADCFC"
COLOR_BG_PAGE = "#FAFBFD"
COLOR_BG_CARD = "#FFFFFF"
COLOR_BG_SOFT = "#EEF1F8"
COLOR_BORDER = "#E5E7EB"
COLOR_TEXT_MUTED = "#6B7280"
COLOR_TEXT_BODY = "#4B5563"


def logo_svg(size: int = 40) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;flex-shrink:0;">'
        f'<path d="M16 26 C16 26, 4 18, 4 11 C4 7, 7 5, 10 5 C13 5, 16 8, 16 11 L16 26 Z" fill="{COLOR_PRIMARY}"/>'
        f'<path d="M16 26 C16 26, 28 18, 28 11 C28 7, 25 5, 22 5 C19 5, 16 8, 16 11 L16 26 Z" '
        f'fill="{COLOR_SECONDARY}" stroke="{COLOR_PRIMARY}" stroke-width="1.5"/>'
        f'<circle cx="16" cy="13" r="2.5" fill="#FFFFFF"/>'
        f'<circle cx="13" cy="9" r="1.2" fill="{COLOR_PRIMARY}"/>'
        f'<circle cx="19" cy="9" r="1.2" fill="{COLOR_PRIMARY}"/>'
        f'</svg>'
    )


def inject_global_css():
    """Inject the global CSS theme. Call once near the top of app.py."""
    css = f"""
    <style>
    .stApp {{ background: {COLOR_BG_PAGE}; }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    h1, h2, h3, h4 {{
        color: {COLOR_PRIMARY};
        letter-spacing: -0.3px;
    }}
    h1 {{ font-weight: 600 !important; }}

    /* Primary button */
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

    /* Secondary button */
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

    /* ----- Tabs styled to live INSIDE the header card ----- */
    /* This is the trick: we negative-margin the tab list up so it visually
       attaches to the header bar, and give it a transparent background. */
    .stTabs {{
        background: transparent;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 32px;
        border-bottom: 1px solid {COLOR_BORDER};
        background: transparent;
        padding: 0 24px;
        margin-top: -8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 12px 4px;
        font-size: 14px;
        color: {COLOR_TEXT_MUTED};
        background: transparent;
        font-weight: 400;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {COLOR_PRIMARY};
    }}
    .stTabs [aria-selected="true"] {{
        color: {COLOR_PRIMARY} !important;
        font-weight: 500;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {COLOR_PRIMARY} !important;
        height: 2px !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: 24px;
    }}

    /* Bordered containers */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 12px;
        border-color: {COLOR_BORDER} !important;
        background: {COLOR_BG_CARD};
    }}

    /* Inputs */
    input[type="text"], input[type="number"], textarea,
    .stSelectbox > div > div, .stTextInput > div > div {{
        border-radius: 8px !important;
    }}

    /* Make the header bar sit closer to its tab list (no double-border feel) */
    .as-header-bar {{
        background: #FFFFFF;
        padding: 14px 24px;
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px 12px 0 0;
        border-bottom: none;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
