"""
AdoptSense — Streamlit entry point.

Slim orchestrator. Sets up page config + global CSS, renders the header
and role switcher, then routes to the right page based on (role, view).

Pages live in frontend/pages_views/. Reusable bits in frontend/components/.
Visual constants in frontend/styles.py.
"""
import sys
from pathlib import Path

# Ensure the project root is importable
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from frontend.styles import inject_global_css
from frontend.components.header import render_header
from frontend.components.role_switcher import (
    render_role_switcher, current_role, ROLE_ADOPTER, ROLE_SHELTER,
)
from frontend.pages_views.home import render_home_page
from frontend.pages_views.pet_detail import render_pet_detail_page
from frontend.pages_views.listing_agent import render_listing_agent_page
from frontend.pages_views.tools import render_tools_page


# Page configuration & global CSS
st.set_page_config(
    page_title="AdoptSense — Find your perfect companion",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()


# Session state defaults
if "view" not in st.session_state:
    st.session_state.view = "browse"


# Header (brand bar) + role switcher
role = current_role()
role_badge = "SHELTER" if role == ROLE_SHELTER else None
display_name = "Patas Amigas" if role == ROLE_SHELTER else "Nora"
render_header(user_name=display_name, role_label=role_badge)
render_role_switcher()
role = current_role()  # re-read in case the switcher caused a rerun


# Routing — single tab list per role, no duplicates
if role == ROLE_ADOPTER:
    tab_home, tab_about, tab_tools = st.tabs(["Home", "About", "Tools"])

    with tab_home:
        # Detail view takes over the Home tab when an adopter clicks a pet
        if st.session_state.view == "pet_detail":
            render_pet_detail_page()
        else:
            render_home_page()

    with tab_about:
        st.markdown(
            "AdoptSense connects rescue animals with loving homes using AI. "
            "Backed by 15,000+ adoption outcomes."
        )

    with tab_tools:
        render_tools_page()

else:  # ROLE_SHELTER
    tab_dashboard, tab_listings, tab_create, tab_tools = st.tabs(
        ["Dashboard", "My Listings", "Create Listing", "Tools"]
    )

    with tab_dashboard:
        st.info(
            "Shelter dashboard with KPIs is coming next. For the demo, focus "
            "on **Create Listing** to show the AI Agent in action."
        )

    with tab_listings:
        st.info("Listing manager — under construction.")

    with tab_create:
        render_listing_agent_page()

    with tab_tools:
        render_tools_page()
