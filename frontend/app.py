"""
AdoptSense — Streamlit entry point.

Routes between brand navbar and Simon's marketplace views. All domain
logic stays in frontend/utils/* (Simon's modules, untouched).

Login flow B: browse + detail open to all; save / message triggers auth.
"""
import base64
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from frontend.styles import (
    inject_global_css, COLOR_PRIMARY, COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED, COLOR_SECONDARY, COLOR_BG_PAGE,
)
from frontend.components.header import render_navbar
from frontend.components.auth_overlay import render_auth_overlay, is_overlay_active
from frontend.components.pet_card import render_pet_card
from frontend.utils import auth, db
from frontend.utils.matching_platform_ui import (
    render_browse, render_detail, render_my_listings,
    render_create_listing, render_edit_listing, render_kpis,
    render_watchlist, render_chat, render_profile, render_shelter_map,
)
from frontend.utils.admin_ui import render_admin_dashboard
from frontend.utils.seed_data import seed_if_needed, backfill_predictions, create_admin_if_needed


# ── Page config & global CSS ──────────────────────────────────────────────────
st.set_page_config(
    page_title="AdoptSense — Find your perfect companion",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()


# ── Bootstrap ────────────────────────────────────────────────────────────────
db.init_db()
seed_if_needed()
create_admin_if_needed()
backfill_predictions()

# ── Update Index trigger (from header dropdown) ───────────────────────────────
if st.session_state.pop("_trigger_backfill", False):
    with st.spinner("Updating prediction index…"):
        backfill_predictions()
    st.success("Prediction index updated!")


# ── Session-state defaults ────────────────────────────────────────────────────
if "mp_view" not in st.session_state:
    st.session_state.mp_view = "browse"

# After-login redirect: role-based landing page.
if st.session_state.pop("_just_logged_in", False):
    cur_user_check = auth.current_user()
    if cur_user_check:
        _role = cur_user_check.get("role")
        if _role == "shelter_manager":
            st.session_state.mp_view = "my_listings"
        elif _role == "admin":
            st.session_state.mp_view = "admin_dashboard"
        else:
            st.session_state.mp_view = "browse"


# ── Navigation config ─────────────────────────────────────────────────────────
NAV_TO_VIEW = {
    "Browse": "browse",
    "Watchlist": "watchlist",
    "Messages": "chat",
    "My Listings": "my_listings",
    "Create Listing": "create",
    "KPIs": "kpis",
    "Shelter Map": "shelter_map",
    "About": "about",
    "Tools": "tools",
    "Dashboard": "admin_dashboard",
}
VIEW_TO_NAV = {v: k for k, v in NAV_TO_VIEW.items()}


def nav_for_role(user: dict | None) -> tuple[list[str], str | None]:
    if user is None:
        return (["Browse", "About"], None)
    if user.get("role") == "admin":
        return (["Dashboard", "Browse", "Tools"], "ADMIN")
    unread = db.get_unread_count(user["id"])
    msg_label = f"Messages ({unread})" if unread else "Messages"
    if user.get("role") == "shelter_manager":
        return (
            ["My Listings", "Create Listing", "KPIs", msg_label, "Browse", "Tools"],
            "SHELTER",
        )
    wl_count = len(db.get_watchlist(user["id"]))
    wl_label = f"Watchlist ({wl_count})" if wl_count else "Watchlist"
    return (["Browse", wl_label, msg_label, "Shelter Map", "About"], None)


# ── Hero image: local file with Unsplash fallback ─────────────────────────────
@st.cache_data
def _hero_src() -> str:
    _FALLBACK = (
        "https://images.unsplash.com/photo-1583337130417-3346a1be7dee"
        "?auto=format&fit=crop&w=800&q=80"
    )
    assets_dir = Path(__file__).parent / "assets"
    for filename in ("hero.jpeg", "hero.jpg", "hero.png"):
        path = assets_dir / filename
        if path.exists():
            mime = "image/png" if filename.endswith(".png") else "image/jpeg"
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{data}"
    return _FALLBACK


# ── Hero section for guests ───────────────────────────────────────────────────
def render_guest_hero():
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
        hero_uri = _hero_src()
        st.markdown(f"""
        <div style="position:relative;display:flex;justify-content:center;
                    align-items:center;min-height:380px;">
          <div style="position:absolute;width:360px;height:360px;
                      background:{COLOR_SECONDARY};border-radius:50%;opacity:0.5;"></div>
          <img src="{hero_uri}" alt="Pet"
               style="position:relative;z-index:1;width:360px;height:360px;
                      object-fit:cover;border-radius:50%;border:6px solid #FFFFFF;
                      box-shadow:0 10px 40px rgba(30,39,97,0.15);"/>
        </div>
        """, unsafe_allow_html=True)


def render_guest_pet_teaser():
    """3 pets + register-CTA card for unauthenticated visitors."""
    listings = db.get_listings(limit=3)
    if not listings:
        return

    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <h2 style="font-size:22px;font-weight:600;color:{COLOR_PRIMARY};margin:0 0 16px;">
      Available pets
    </h2>
    """, unsafe_allow_html=True)

    cols = st.columns(3, gap="medium")
    for idx, listing in enumerate(listings[:3]):
        with cols[idx]:
            render_pet_card(listing, show_speed=False, key_prefix="guest_teaser")

    total_count = len(db.get_listings(limit=200))
    remaining = max(0, total_count - 3)

    st.markdown(f"""
    <div style="position:relative;margin-top:-32px;height:120px;
                background:linear-gradient(180deg,
                  rgba(250,251,253,0) 0%,
                  rgba(250,251,253,0.6) 40%,
                  {COLOR_BG_PAGE} 100%);
                pointer-events:none;"></div>
    """, unsafe_allow_html=True)

    cta_html = (
        f'<div style="background:#FFFFFF;border:1px solid #E5E7EB;'
        f'border-radius:14px;padding:32px 24px;text-align:center;'
        f'margin:8px 0 24px;box-shadow:0 4px 16px rgba(30,39,97,0.06);">'
        f'<h3 style="margin:0 0 8px;font-size:22px;color:{COLOR_PRIMARY};'
        f'font-weight:600;">'
        f'{remaining}+ more pets are looking for a home.</h3>'
        f'<p style="margin:0 0 18px;font-size:14px;color:{COLOR_TEXT_MUTED};">'
        f'Register to browse all listings, save favourites, and message shelters.</p>'
        f'</div>'
    )
    st.markdown(cta_html, unsafe_allow_html=True)

    cta_col1, cta_col2, cta_col3 = st.columns([1, 1, 1])
    with cta_col2:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Log In", type="secondary",
                         use_container_width=True, key="teaser_login"):
                st.session_state.show_auth = "login"
                st.rerun()
        with c2:
            if st.button("Register", type="primary",
                         use_container_width=True, key="teaser_register"):
                st.session_state.show_auth = "register"
                st.rerun()
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)


def render_about():
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>About AdoptSense</h1>",
                unsafe_allow_html=True)
    st.markdown(f"""
    <p style='color:{COLOR_TEXT_BODY};font-size:15px;line-height:1.6;'>
    AdoptSense connects rescue animals with loving homes using AI. Backed by
    15,000+ adoption outcomes, our XGBoost model predicts adoption speed and our
    Gemini-powered Listing Agent helps shelters create studio-quality photos and
    adoption-optimised descriptions.
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


# ── Auth overlay ──────────────────────────────────────────────────────────────
if is_overlay_active():
    user = auth.current_user()
    nav_options, role_badge = nav_for_role(user)
    render_navbar(nav_options=nav_options, default_index=0, role_label=role_badge)
    render_auth_overlay()
    st.stop()


# ── Render navbar ─────────────────────────────────────────────────────────────
user = auth.current_user()
is_manager = bool(user and user.get("role") == "shelter_manager")
nav_options, role_badge = nav_for_role(user)

# "profile" is not a nav item — keep whichever tab was active before
_view_for_nav = st.session_state.mp_view
if _view_for_nav == "profile":
    _view_for_nav = st.session_state.get("mp_view_before_profile", "browse")
_base_nav_label = VIEW_TO_NAV.get(_view_for_nav, nav_options[0])
# Nav options may have count suffixes like "Messages (3)" or "Watchlist (2)"
# Find the matching option regardless of suffix
current_nav_label = _base_nav_label
if current_nav_label not in nav_options:
    for opt in nav_options:
        if re.sub(r'\s*\(\d+\)\s*$', '', opt) == _base_nav_label:
            current_nav_label = opt
            break
    else:
        current_nav_label = nav_options[0]
default_idx = nav_options.index(current_nav_label)

selected = render_navbar(
    nav_options=nav_options,
    default_index=default_idx,
    role_label=role_badge,
)


# ── Sync user-initiated nav clicks → mp_view ──────────────────────────────────
# option_menu always returns a label (the one at default_index) even when
# the user did nothing. We can only detect a real click when the returned
# label differs from current_nav_label, which is what we passed in as the
# default. State-driven view changes (e.g. _nav("detail", ...)) set mp_view
# directly and the navbar follows on the next rerun.
#
# To go back from a sub-view (Detail/Edit) to its parent list, users can
# click the "← Back" button rendered inside the sub-view itself. We do NOT
# try to detect this via the navbar — see git history for why that approach
# was buggy (option_menu can't tell apart "user clicked" from "default
# returned", and it bounced users out of detail views immediately).
if selected and selected != current_nav_label:
    # Strip count suffix e.g. "Messages (3)" → "Messages"
    _selected_base = re.sub(r'\s*\(\d+\)\s*$', '', selected)
    target_view = NAV_TO_VIEW.get(_selected_base, "browse")
    if target_view not in ("detail", "edit"):
        st.session_state.pop("mp_listing_id", None)
    if target_view != "chat":
        st.session_state.pop("mp_chat_with", None)
    st.session_state.mp_view = target_view
    st.rerun()


# ── View routing ─────────────────────────────────────────────────────────────
view = st.session_state.mp_view

if view == "browse":
    if user is None:
        render_guest_hero()
        render_guest_pet_teaser()
    else:
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

elif view == "profile":
    if not auth.require_login("view your profile"):
        st.stop()
    render_profile(user)

elif view == "shelter_map":
    render_shelter_map(user)

elif view == "about":
    render_about()

elif view == "tools":
    if not is_manager and not (user and user.get("role") == "admin"):
        st.error("Tools are for shelter managers only.")
    else:
        render_tools()

elif view == "admin_dashboard":
    if not user or user.get("role") != "admin":
        st.error("This page is for the admin account only.")
    else:
        render_admin_dashboard(user)

else:
    st.session_state.mp_view = "browse"
    st.rerun()
