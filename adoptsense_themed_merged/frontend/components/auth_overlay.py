"""
Branded login / register overlay.

Renders inside a centered card when st.session_state.show_auth is set to
"login" or "register". Uses Simon's `frontend.utils.auth` module for the
actual logic — only the visual presentation is new.
"""
import streamlit as st

from frontend.styles import COLOR_PRIMARY, COLOR_BORDER, COLOR_TEXT_MUTED
from frontend.utils import auth


def is_overlay_active() -> bool:
    return st.session_state.get("show_auth") in ("login", "register")


def render_auth_overlay():
    """Render the auth overlay if active. Returns True if rendered."""
    mode = st.session_state.get("show_auth")
    if mode not in ("login", "register"):
        return False

    # Center the form in the middle 50% of the page
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
        ok, msg = auth.login(username, password)
        if ok:
            st.session_state.pop("show_auth", None)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

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

    with st.form("register_form", clear_on_submit=False):
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        role = st.selectbox(
            "I am a…",
            options=["household", "shelter_manager"],
            format_func=lambda x: ("🏠 Adopter (household)" if x == "household"
                                   else "🏥 Shelter Manager"),
            key="reg_role",
        )
        shelter_name = ""
        if role == "shelter_manager":
            shelter_name = st.text_input(
                "Shelter / Organisation name", key="reg_shelter_name"
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
        else:
            ok, msg = auth.register(
                username, email, password, role,
                shelter_name=shelter_name or None,
            )
            if ok:
                # Auto-login after successful registration
                auth.login(username, password)
                st.session_state.pop("show_auth", None)
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
