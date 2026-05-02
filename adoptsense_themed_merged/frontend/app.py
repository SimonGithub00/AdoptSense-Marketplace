"""
AdoptSense — Streamlit entry point.

Slim orchestrator. Sets up page config, injects brand CSS, renders the
top navbar, and routes to the right view. All domain logic lives in
frontend/utils/* (untouched from Simon's original) — this file only owns
layout and routing.

Navigation per role:
  Guest:           Browse · About
  Adopter:         Browse · Watchlist · Messages · About
  Shelter Manager: My Listings · Create Listing · KPIs · Messages · Browse · Tools

Login flow (B): browse and detail are open to everyone; saving a pet or
messaging a shelter triggers the auth overlay.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from frontend.styles import inject_global_css, COLOR_PRIMARY, COLOR_TEXT_BODY, COLOR_SECONDARY
from frontend.components.header import render_navbar
from frontend.components.auth_overlay import render_auth_overlay, is_overlay_active
from frontend.utils import auth, db
from frontend.utils.matching_platform_ui import (
    render_browse, render_detail, render_my_listings,
    render_create_listing, render_edit_listing, render_kpis,
    render_watchlist, render_chat,
)
from frontend.utils.seed_data import seed_if_needed, backfill_predictions


# ── Page config & global CSS ───────────────────────────────────────────────────
st.set_page_config(
    page_title="AdoptSense — Find your perfect companion",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()


# ── Bootstrap (Simon's original — DB init + seed) ──────────────────────────────
db.init_db()
seed_if_needed()
backfill_predictions()


# ── Session-state defaults ─────────────────────────────────────────────────────
if "mp_view" not in st.session_state:
    st.session_state.mp_view = "browse"


# ── Navigation config ──────────────────────────────────────────────────────────
NAV_TO_VIEW = {
    "Browse": "browse",
    "Watchlist": "watchlist",
    "Messages": "chat",
    "My Listings": "my_listings",
    "Create Listing": "create",
    "KPIs": "kpis",
    "About": "about",
    "Tools": "tools",
}
VIEW_TO_NAV = {v: k for k, v in NAV_TO_VIEW.items()}


def nav_for_role(user: dict | None) -> tuple[list[str], str | None]:
    """Return (nav_options, role_badge_label) based on the current user."""
    if user is None:
        return (["Browse", "About"], None)
    if user.get("role") == "shelter_manager":
        return (
            ["My Listings", "Create Listing", "KPIs", "Messages", "Browse", "Tools"],
            "SHELTER",
        )
    # household / adopter
    return (["Browse", "Watchlist", "Messages", "About"], None)


# ── Hero section (shown above Browse for guests, to give the marketing pitch) ──
def render_guest_hero():
    """Hero for unauthenticated visitors. Helps the pitch demo land cleanly."""
    HERO_IMAGE_URL = (
        "https://images.unsplash.com/photo-1583337130417-3346a1be7dee"
        "?auto=format&fit=crop&w=800&q=80"
    )

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown(f"""
        <h1 style="font-size:42px;font-weight:600;color:{COLOR_PRIMARY};
                   line-height:1.15;margin:0 0 16px;letter-spacing:-1px;">
          Find your perfect companion faster.
        </h1>
        <p style="font-size:16px;color:{COLOR_TEXT_BODY};line-height:1.6;
                  margin:0 0 24px;">
          AI-powered pet adoption that connects rescue animals with loving homes —
          backed by a growing dataset of 15,000+ adoptions, getting smarter with
          every match.
        </p>
        """, unsafe_allow_html=True)
        cta1, cta2, _ = st.columns([1, 1, 2])
        with cta1:
            if st.button("Get Started", type="primary",
                         use_container_width=True, key="hero_get_started"):
                st.session_state.show_auth = "register"
                st.rerun()
        with cta2:
            if st.button("Log In", type="secondary",
                         use_container_width=True, key="hero_login"):
                st.session_state.show_auth = "login"
                st.rerun()

    with right:
        st.markdown(f"""
        <div style="position:relative;display:flex;justify-content:center;
                    align-items:center;min-height:360px;">
          <div style="position:absolute;width:340px;height:340px;
                      background:{COLOR_SECONDARY};border-radius:50%;opacity:0.5;"></div>
          <img src="{HERO_IMAGE_URL}" alt="Pet"
               style="position:relative;z-index:1;width:340px;height:340px;
                      object-fit:cover;border-radius:50%;border:6px solid #FFFFFF;
                      box-shadow:0 10px 40px rgba(30,39,97,0.15);"/>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <h2 style="font-size:22px;font-weight:600;color:{COLOR_PRIMARY};margin:0 0 16px;">
      Available pets
    </h2>
    """, unsafe_allow_html=True)


def render_about():
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>About AdoptSense</h1>",
                unsafe_allow_html=True)
    st.markdown(f"""
    <p style='color:{COLOR_TEXT_BODY};font-size:15px;line-height:1.6;'>
    AdoptSense connects rescue animals with loving homes using AI.
    Backed by 15,000+ adoption outcomes, our XGBoost model predicts adoption
    speed and our Gemini-powered Listing Agent helps shelters create
    studio-quality photos and adoption-optimised descriptions.
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    **Tech stack**

    | Component | Technology |
    |-----------|------------|
    | ML model | XGBoost (5-class adoption speed prediction) |
    | Sentiment | NLTK VADER |
    | Listing Agent | Google Gemini 2.5 Flash |
    | Photo enhancement | rembg + PIL studio backdrop |
    | Frontend | Streamlit + streamlit-option-menu |
    | Database | SQLite |
    | Auth | SHA-256 + salt |

    **Dataset:** Petfinder.my Kaggle Competition · 14,993 labelled listings
    """)


def render_tools():
    """Internal tools (Batch + Single Pet) — manager-only, behind a nav item."""
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>Tools</h1>",
                unsafe_allow_html=True)
    st.caption(
        "Internal utilities for batch and single-pet predictions outside "
        "the marketplace flow."
    )
    tab_batch, tab_single = st.tabs(["📁 Batch Upload (CSV)", "📝 Single Pet"])
    with tab_batch:
        from frontend.utils.tools_legacy import show_csv_upload
        show_csv_upload()
    with tab_single:
        from frontend.utils.tools_legacy import show_manual_form
        show_manual_form()


# ── Auth overlay (modal-style) ─────────────────────────────────────────────────
# When active, show the navbar + the overlay form, and stop. The user can
# cancel out of the overlay or complete login/registration.
if is_overlay_active():
    user = auth.current_user()
    nav_options, role_badge = nav_for_role(user)
    render_navbar(nav_options=nav_options, default_index=0, role_label=role_badge)
    render_auth_overlay()
    st.stop()


# ── Render navbar ──────────────────────────────────────────────────────────────
user = auth.current_user()
is_manager = bool(user and user.get("role") == "shelter_manager")
nav_options, role_badge = nav_for_role(user)

# Default to the nav option matching the current view so reruns don't snap back
current_nav_label = VIEW_TO_NAV.get(st.session_state.mp_view, nav_options[0])
if current_nav_label not in nav_options:
    current_nav_label = nav_options[0]
default_idx = nav_options.index(current_nav_label)

selected = render_navbar(
    nav_options=nav_options,
    default_index=default_idx,
    role_label=role_badge,
)

# When the user clicks a nav option, sync into mp_view and rerun
if selected and selected != current_nav_label:
    st.session_state.mp_view = NAV_TO_VIEW.get(selected, "browse")
    st.session_state.pop("mp_listing_id", None)  # clear stale detail context
    st.rerun()


# ── View routing ──────────────────────────────────────────────────────────────
view = st.session_state.mp_view

if view == "browse":
    if user is None:
        render_guest_hero()
    render_browse(user)

elif view == "detail":
    lid = st.session_state.get("mp_listing_id")
    if lid:
        render_detail(lid, user)
    else:
        st.session_state.mp_view = "browse"
        st.rerun()

elif view == "my_listings":
    if not auth.require_login("manage your listings"):
        st.stop()
    if not is_manager:
        st.error("Only shelter managers can access My Listings.")
    else:
        render_my_listings(user)

elif view == "create":
    if not auth.require_login("create a listing"):
        st.stop()
    if not is_manager:
        st.error("Only shelter managers can create listings.")
    else:
        render_create_listing(user)

elif view == "edit":
    if not auth.require_login("edit listings"):
        st.stop()
    lid = st.session_state.get("mp_listing_id")
    if lid:
        render_edit_listing(lid, user)
    else:
        st.session_state.mp_view = "browse"
        st.rerun()

elif view == "kpis":
    if not auth.require_login("view performance data"):
        st.stop()
    if not is_manager:
        st.error("Only shelter managers can view KPIs.")
    else:
        render_kpis(user)

elif view == "watchlist":
    if not auth.require_login("use your watchlist"):
        st.stop()
    if is_manager:
        st.error("Watchlist is for adopters only.")
    else:
        render_watchlist(user)

elif view == "chat":
    if not auth.require_login("send messages"):
        st.stop()
    render_chat(user)

elif view == "about":
    render_about()

elif view == "tools":
    if not is_manager:
        st.error("Tools are for shelter managers only.")
    else:
        render_tools()

else:
    st.session_state.mp_view = "browse"
    st.rerun()
