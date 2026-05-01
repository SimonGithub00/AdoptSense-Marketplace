"""
AdoptSense — Streamlit entry point.

Slim orchestrator. Sets up page config + global CSS, renders the navbar
(logo + horizontal nav + user avatar in one row) and routes to the right
page based on (role, selected nav, current view).
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from frontend.styles import inject_global_css
from frontend.components.header import render_navbar
from frontend.components.role_switcher import (
    render_role_switcher, current_role, ROLE_ADOPTER, ROLE_SHELTER,
)
from frontend.pages_views.home import render_home_page
from frontend.pages_views.pet_detail import render_pet_detail_page
from frontend.pages_views.listing_agent import render_listing_agent_page
from frontend.pages_views.tools import render_tools_page


# Page config & global CSS
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


# Role switcher first so we know which navbar to render
render_role_switcher()
role = current_role()


# Navbar — different nav options per role
if role == ROLE_ADOPTER:
    nav_options = ["Home", "About", "Tools"]
    selected = render_navbar(
        nav_options=nav_options,
        user_name="Nora",
        role_label=None,
    )

    if selected == "Home":
        if st.session_state.view == "pet_detail":
            render_pet_detail_page()
        else:
            render_home_page()
    elif selected == "About":
        st.markdown(
            "AdoptSense connects rescue animals with loving homes using AI. "
            "Backed by 15,000+ adoption outcomes."
        )
    elif selected == "Tools":
        render_tools_page()

else:  # ROLE_SHELTER
    nav_options = ["Dashboard", "My Listings", "Create Listing", "Tools"]
    selected = render_navbar(
        nav_options=nav_options,
        user_name="Patas Amigas",
        role_label="SHELTER",
        default_index=2,  # Land on "Create Listing" by default — that's the demo
    )

    if selected == "Dashboard":
        st.info(
            "Shelter dashboard with KPIs is coming next. For the demo, focus "
            "on **Create Listing** to show the AI Agent in action."
        )
    elif selected == "My Listings":
        st.info("Listing manager — under construction.")
    elif selected == "Create Listing":
        render_listing_agent_page()
    elif selected == "Tools":
        render_tools_page()
