"""
Internal tools page — wraps the legacy Batch Upload and Single Pet Form views.

These were the original entry points of the app and are still useful internally
(e.g. for shelter staff doing data validation), but they are not part of the
adopter-facing marketplace flow.

This page lives behind the "Tools" tab in the top navigation. It does NOT
import the original app.py — it pulls the same logic by re-exposing the
prediction utilities and rebuilding a slim version of the two old tabs.

If Simon decides the legacy code in `frontend/app.py` is what shelter staff
should still use, this page can simply embed it. For now we keep the dependency
contained to `predictions` and `recommendations`, which are the stable utilities.
"""
import streamlit as st
import pandas as pd

from frontend.styles import COLOR_PRIMARY, COLOR_TEXT_MUTED


def render_tools_page():
    """Render the legacy tools (batch upload + single pet form) inside tabs."""
    st.markdown(f"""
    <h1 style="font-size: 26px; font-weight: 600; color: {COLOR_PRIMARY};
               margin: 0 0 4px;">Internal Tools</h1>
    <p style="font-size: 13px; color: {COLOR_TEXT_MUTED}; margin: 0 0 20px;">
      Legacy batch and single-pet prediction tools. Useful for data validation
      and quick checks outside the marketplace flow.
    </p>
    """, unsafe_allow_html=True)

    tab_batch, tab_single = st.tabs(["📁 Batch Upload (CSV)", "📝 Single Pet Form"])

    with tab_batch:
        _render_batch_upload_stub()

    with tab_single:
        _render_single_pet_stub()


def _render_batch_upload_stub():
    """Slim version of the original batch upload."""
    st.markdown("Upload a CSV with multiple pets to get adoption-speed predictions for all of them.")
    uploaded = st.file_uploader("CSV file", type=["csv"], key="tools_batch_upload")

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            st.success(f"Uploaded {len(df)} pets")
            st.dataframe(df.head(10), use_container_width=True)

            if st.button("Run Predictions", type="primary", key="tools_batch_run"):
                with st.spinner("Running model..."):
                    from frontend.utils.predictions import make_prediction
                    results = make_prediction(df)

                if results.get("success"):
                    rows = []
                    for pred in results["predictions"]:
                        rows.append({
                            "Pet": pred["original_data"].get(
                                "Name", f"Pet {pred['pet_index'] + 1}"
                            ),
                            "Predicted Speed": pred["prediction_label"],
                            "Confidence": f"{pred['confidence']*100:.1f}%",
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
                else:
                    st.error(f"Prediction failed: {results.get('error')}")
        except Exception as e:
            st.error(f"Error reading file: {e}")


def _render_single_pet_stub():
    """Pointer to the original single-pet form for now.

    Rather than duplicate the 200-line form here, we point the user at the
    legacy entry. Once Nora's marketplace UI is fully validated we can decide
    whether to retire the original or migrate the form here.
    """
    st.info(
        "The detailed single-pet form is available in the legacy entry point. "
        "Run `streamlit run frontend/app_legacy.py` to access it, or copy the "
        "form code from `app.py.bak` into this view if needed for the demo."
    )
