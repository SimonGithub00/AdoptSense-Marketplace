"""
Adopter / Shelter role switcher — rendered as a pill-style toggle.

Uses st.segmented_control (Streamlit 1.32+) which gives a proper toggle look
matching the mockup. Falls back to st.radio if running on older Streamlit.
"""
import streamlit as st


ROLE_ADOPTER = "adopter"
ROLE_SHELTER = "shelter"


def init_role_state():
    if "role" not in st.session_state:
        st.session_state.role = ROLE_ADOPTER


def render_role_switcher():
    """Render the role toggle, right-aligned. Triggers a rerun on change."""
    init_role_state()

    spacer, switcher = st.columns([5, 2])
    with switcher:
        # Try the modern segmented control; fall back to radio on older versions.
        if hasattr(st, "segmented_control"):
            choice = st.segmented_control(
                "Browsing as:",
                options=["Adopter", "Shelter"],
                default="Adopter" if st.session_state.role == ROLE_ADOPTER else "Shelter",
                key="role_segmented_widget",
            )
        else:
            choice = st.radio(
                "Browsing as:",
                options=["Adopter", "Shelter"],
                index=0 if st.session_state.role == ROLE_ADOPTER else 1,
                horizontal=True,
                key="role_radio_widget",
            )

        # segmented_control returns None if user clicks the active option to deselect.
        # Treat None as "no change".
        if choice is None:
            return

        new_role = ROLE_ADOPTER if choice == "Adopter" else ROLE_SHELTER
        if new_role != st.session_state.role:
            st.session_state.role = new_role
            st.session_state.view = "browse"
            st.rerun()


def current_role() -> str:
    init_role_state()
    return st.session_state.role
