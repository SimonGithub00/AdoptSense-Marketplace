"""
Adopter / Shelter role switcher.
Persisted in st.session_state["role"]. Uses st.radio for max compatibility.
"""
import streamlit as st


ROLE_ADOPTER = "adopter"
ROLE_SHELTER = "shelter"


def init_role_state():
    if "role" not in st.session_state:
        st.session_state.role = ROLE_ADOPTER


def render_role_switcher():
    """Render the role toggle, right-aligned."""
    init_role_state()

    spacer, switcher = st.columns([5, 2])
    with switcher:
        choice = st.radio(
            "Browsing as:",
            options=["Adopter", "Shelter"],
            index=0 if st.session_state.role == ROLE_ADOPTER else 1,
            horizontal=True,
            key="role_radio_widget",
        )
        new_role = ROLE_ADOPTER if choice == "Adopter" else ROLE_SHELTER
        if new_role != st.session_state.role:
            st.session_state.role = new_role
            # Reset view when switching roles so we don't end up on a stale page
            st.session_state.view = "browse"
            st.rerun()


def current_role() -> str:
    init_role_state()
    return st.session_state.role
