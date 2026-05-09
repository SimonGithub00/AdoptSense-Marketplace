"""
Branded login / register overlay.

Renders inside a centered card when st.session_state.show_auth is set to
"login" or "register". Uses Simon's `frontend.utils.auth` module for the
actual logic — only the visual presentation is new.
"""
import json
from pathlib import Path

import streamlit as st

from frontend.styles import COLOR_PRIMARY, COLOR_BORDER, COLOR_TEXT_MUTED
from frontend.utils import auth, db

_LOCATIONS_PATH = Path(__file__).parent.parent / "assets" / "shelter_locations.json"


@st.cache_data
def _load_reg_locations() -> dict:
    try:
        return json.loads(_LOCATIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"countries": [], "cities_by_country": {}}


def is_overlay_active() -> bool:
    return st.session_state.get("show_auth") in ("login", "register")


def render_auth_overlay():
    """Render the auth overlay if active. Returns True if rendered."""
    mode = st.session_state.get("show_auth")
    if mode not in ("login", "register"):
        return False

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            if mode == "login":
                _render_login_form()
            else:
                _render_register_form()
    return True


def _form_header(title: str, subtitle: str):
    st.markdown(
        f'<div style="text-align:center;padding:8px 0 16px;">'
        f'<h2 style="margin:0;color:{COLOR_PRIMARY};font-size:24px;'
        f'font-weight:600;">{title}</h2>'
        f'<p style="margin:6px 0 0;color:{COLOR_TEXT_MUTED};font-size:13px;">'
        f'{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def _render_login_form():
    _form_header("Welcome back", "Log in to message shelters and save favourites.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button(
                "Log In", type="primary", use_container_width=True
            )
        with c2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

    if cancel:
        st.session_state.pop("show_auth", None)
        st.rerun()

    if submitted:
        user = auth.verify_credentials(username, password)
        if user is None:
            st.error("Invalid username or password.")
        else:
            st.session_state.user = user
            st.session_state.pop("show_auth", None)
            st.session_state["_just_logged_in"] = True
            st.success(f"Welcome back, {user['username']}!")
            st.rerun()

    st.markdown(
        f'<div style="text-align:center;margin-top:12px;font-size:13px;'
        f'color:{COLOR_TEXT_MUTED};">No account yet?</div>',
        unsafe_allow_html=True,
    )
    if st.button("Create one", key="switch_to_register", use_container_width=True):
        st.session_state.show_auth = "register"
        st.rerun()


def _render_register_form():
    _form_header(
        "Create your account",
        "Join AdoptSense as an adopter or a shelter.",
    )

    locs = _load_reg_locations()
    countries = locs.get("countries", [])
    cities_by_country = locs.get("cities_by_country", {})

    # Role selector OUTSIDE the form so changing it triggers a rerun and
    # shelter-specific fields appear/disappear without needing to submit first.
    role = st.selectbox(
        "I am a…",
        options=["household", "shelter_manager"],
        format_func=lambda x: ("🏠 Adopter (household)" if x == "household"
                               else "🏥 Shelter Manager"),
        key="reg_role",
    )

    with st.form("register_form", clear_on_submit=False):
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        shelter_name = ""
        reg_phone = ""
        reg_country = None
        reg_city = None
        reg_postal = None
        reg_shelter_address = ""
        if role == "shelter_manager":
            shelter_name = st.text_input(
                "Shelter / Organisation name *", key="reg_shelter_name"
            )
            reg_phone = st.text_input(
                "Phone number *", key="reg_phone", placeholder="+351 912 345 678"
            )
            st.markdown("**Shelter location \\***")
            _reg_country_opts = ["— select —"] + countries
            _rc = st.selectbox("Country *", _reg_country_opts, key="reg_country")
            _reg_city_list = [c["city"] for c in cities_by_country.get(_rc, [])] if _rc != "— select —" else []
            _rci = st.selectbox("City *", ["— select —"] + _reg_city_list, key="reg_city",
                                disabled=(_rc == "— select —"))
            _reg_postal_list = []
            if _rci and _rci != "— select —":
                for _e in cities_by_country.get(_rc, []):
                    if _e["city"] == _rci:
                        _reg_postal_list = _e.get("postal_codes", [])
                        break
            _rcp = st.selectbox("Postal code", ["— any —"] + _reg_postal_list, key="reg_postal",
                                disabled=(_rci == "— select —"))
            reg_shelter_address = st.text_input(
                "Street address", key="reg_shelter_address",
                placeholder="Rua da Esperança 12"
            )
        password = st.text_input(
            "Password (min 6 chars)", type="password", key="reg_password"
        )
        password2 = st.text_input(
            "Confirm password", type="password", key="reg_password2"
        )

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button(
                "Register", type="primary", use_container_width=True
            )
        with c2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

    if cancel:
        st.session_state.pop("show_auth", None)
        st.rerun()

    if submitted:
        if password != password2:
            st.error("Passwords do not match.")
        elif role == "shelter_manager" and not shelter_name.strip():
            st.error("Shelter name is required.")
        elif role == "shelter_manager" and not reg_phone.strip():
            st.error("Phone number is required for shelter managers.")
        elif role == "shelter_manager" and st.session_state.get("reg_country", "— select —") == "— select —":
            st.error("Please select your country.")
        elif role == "shelter_manager" and st.session_state.get("reg_city", "— select —") == "— select —":
            st.error("Please select your city.")
        else:
            ok, msg = auth.register(
                username, email, password, role,
                shelter_name=shelter_name or None,
            )
            if ok:
                # Store extra shelter manager fields
                if role == "shelter_manager":
                    uid = db.get_user_by_username(username.strip())
                    if uid:
                        _rc_val = st.session_state.get("reg_country")
                        _rci_val = st.session_state.get("reg_city")
                        _rcp_val = st.session_state.get("reg_postal")
                        db.update_user(
                            uid["id"],
                            phone=reg_phone.strip(),
                            country=_rc_val if _rc_val != "— select —" else None,
                            city=_rci_val if _rci_val != "— select —" else None,
                            postal_code=_rcp_val if _rcp_val != "— any —" else None,
                            shelter_address=reg_shelter_address.strip() or None,
                        )
                auth.login(username, password)
                st.session_state.pop("show_auth", None)
                st.session_state["_just_logged_in"] = True
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown(
        f'<div style="text-align:center;margin-top:12px;font-size:13px;'
        f'color:{COLOR_TEXT_MUTED};">Already have an account?</div>',
        unsafe_allow_html=True,
    )
    if st.button("Log in", key="switch_to_login", use_container_width=True):
        st.session_state.show_auth = "login"
        st.rerun()
