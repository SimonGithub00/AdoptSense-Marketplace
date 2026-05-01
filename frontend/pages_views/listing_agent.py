"""
Shelter view — Create Listing with the AI Agent.

Visual shell for Simon's Listing Agent. The agent itself is called via
`run_listing_agent_stub()` — Simon replaces that function's body. The UI
contract (return-dict keys) is documented in the function's docstring.
"""
import time
import streamlit as st

from frontend.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_BG_SOFT,
    COLOR_BORDER,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
)


# =============================================================================
# INTEGRATION POINT FOR SIMON — replace the body of this function
# =============================================================================
def run_listing_agent_stub(pet_data: dict, uploaded_photos: list) -> dict:
    """Run the AI Listing Agent on the provided pet data and photos.

    THIS IS A STUB — Simon replaces the body with the real agent call
    (LLM + tool use: photo enhancement + XGBoost prediction + iteration).

    The return shape is the contract — UI consumes exactly these keys.

    Args:
        pet_data: dict with 'name', 'breed', 'species', 'age_months',
                  'fee_eur', 'health', 'description'
        uploaded_photos: list of UploadedFile objects

    Returns:
        dict with:
          - 'enhanced_photos': list — enhanced photo data or URLs
          - 'description': str — AI-generated description
          - 'sentiment_score': float — VADER compound -1..+1
          - 'predicted_speed': int — 0..4
          - 'predicted_speed_label': str — "1-7 days"
          - 'previous_speed_label': str | None — pre-agent prediction
          - 'confidence': float — 0..1
          - 'iterations': int
          - 'recommendations': list[str]
    """
    time.sleep(1.2)
    return {
        "enhanced_photos": [],
        "description": (
            f"{pet_data.get('name', 'This pet')} is a playful and friendly "
            f"{pet_data.get('breed', 'companion')} who loves long walks and "
            "meeting new people. Well-trained, knows basic commands, and gets "
            "along great with other dogs. Looking for an active family who can "
            "give plenty of exercise and love."
        ),
        "sentiment_score": 0.42,
        "predicted_speed": 1,
        "predicted_speed_label": "1-7 days",
        "previous_speed_label": "8-30 days",
        "confidence": 0.87,
        "iterations": 3,
        "recommendations": [
            "Add a short video (predicted +12% engagement)",
            "Lower fee to €50 (predicted -2 days adoption time)",
        ],
    }
# =============================================================================


def render_listing_agent_page():
    _render_page_header()

    left, right = st.columns([1, 1], gap="large")

    with left:
        pet_data, uploaded = _render_input_section()
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        run_clicked = st.button(
            "✨ Run AI Agent", type="primary",
            use_container_width=True, key="run_agent_btn",
        )

    with right:
        if run_clicked or st.session_state.get("agent_result"):
            if run_clicked:
                with st.spinner("Agent is optimizing your listing..."):
                    result = run_listing_agent_stub(pet_data, uploaded)
                st.session_state.agent_result = result

            result = st.session_state.agent_result
            _render_agent_panel(result)
            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
            _render_prediction_card(result)
            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
            _render_recommendations_card(result["recommendations"])
        else:
            _render_agent_idle_state()

    if st.session_state.get("agent_result"):
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        _render_publish_section()


def _render_page_header():
    header_html = (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        f'<h1 style="font-size:28px;font-weight:600;color:{COLOR_PRIMARY};margin:0;'
        f'letter-spacing:-0.3px;">Create New Listing</h1>'
        f'<span style="background:linear-gradient(135deg,{COLOR_PRIMARY} 0%,{COLOR_PRIMARY_LIGHT} 100%);'
        f'color:#FFFFFF;padding:4px 12px;border-radius:20px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.5px;">✨ AI ASSISTED</span>'
        f'</div>'
        f'<p style="font-size:14px;color:{COLOR_TEXT_MUTED};margin:0 0 24px;">'
        f'Upload photos and basic info. Our AI agent enhances your listing automatically.</p>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def _render_input_section():
    # Photo upload card
    with st.container(border=True):
        st.markdown(
            f'<div style="font-size:13px;font-weight:500;color:{COLOR_PRIMARY};'
            f'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px;">'
            f'1. Upload Photos</div>',
            unsafe_allow_html=True
        )

        uploaded = st.file_uploader(
            "Upload pet photos",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
            key="agent_photo_upload",
        )

        if st.session_state.get("agent_result"):
            _render_before_after_preview()

        st.markdown(
            f'<div style="background:#F8F9FB;border-radius:8px;padding:12px;'
            f'font-size:12px;color:{COLOR_TEXT_BODY};line-height:1.5;margin-top:12px;">'
            f'<span style="color:{COLOR_PRIMARY};font-weight:500;">AI ethics:</span> '
            f'Only background, lighting, and pose are enhanced. The pet itself is '
            f'never altered. Original photo stays accessible to adopters.</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Basic info card
    with st.container(border=True):
        st.markdown(
            f'<div style="font-size:13px;font-weight:500;color:{COLOR_PRIMARY};'
            f'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:14px;">'
            f'2. Basic Info</div>',
            unsafe_allow_html=True
        )

        c1, c2 = st.columns(2, gap="small")
        with c1:
            name = st.text_input("Pet Name", value="Buddy", key="agent_name")
            age_months = st.number_input("Age (months)", min_value=0, max_value=240,
                                          value=24, key="agent_age")
        with c2:
            species = st.selectbox("Species", ["Dog", "Cat"], key="agent_species")
            fee_eur = st.number_input("Adoption Fee (€)", min_value=0, max_value=500,
                                       value=80, key="agent_fee")

        breed = st.text_input("Breed", value="Border Collie", key="agent_breed")
        health = st.selectbox("Health", ["Healthy", "Minor Issue", "Serious Issue"],
                               key="agent_health")

        default_desc = ""
        desc_label = "Description (optional — agent will generate one if empty)"
        if st.session_state.get("agent_result"):
            default_desc = st.session_state.agent_result["description"]
            desc_label = "Description (✨ AI generated, you can edit)"
        description = st.text_area(desc_label, value=default_desc, height=100,
                                    key="agent_description")

    return {
        "name": name, "breed": breed, "species": species,
        "age_months": age_months, "fee_eur": fee_eur,
        "health": health, "description": description,
    }, uploaded or []


def _render_before_after_preview():
    preview_html = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;'
        f'margin-top:12px;">'
        f'<div>'
        f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};margin-bottom:6px;">ORIGINAL</div>'
        f'<div style="aspect-ratio:1;background:#DCD0C0;border-radius:8px;'
        f'position:relative;display:flex;align-items:center;justify-content:center;'
        f'opacity:0.85;">'
        f'<div style="position:absolute;bottom:6px;left:6px;background:rgba(0,0,0,0.6);'
        f'color:#FFFFFF;padding:2px 6px;border-radius:4px;font-size:9px;">poor lighting</div>'
        f'<span style="color:rgba(255,255,255,0.7);font-size:10px;">photo</span>'
        f'</div></div>'
        f'<div>'
        f'<div style="font-size:11px;color:{COLOR_PRIMARY};font-weight:500;'
        f'margin-bottom:6px;">✨ AI ENHANCED</div>'
        f'<div style="aspect-ratio:1;background:linear-gradient(135deg,#FCE5D8 0%,#F5C9A8 100%);'
        f'border-radius:8px;position:relative;display:flex;align-items:center;'
        f'justify-content:center;border:2px solid {COLOR_PRIMARY};">'
        f'<div style="position:absolute;bottom:6px;right:6px;background:{COLOR_PRIMARY};'
        f'color:#FFFFFF;padding:2px 6px;border-radius:4px;font-size:9px;font-weight:500;">'
        f'studio quality</div>'
        f'<span style="color:rgba(255,255,255,0.8);font-size:10px;">photo</span>'
        f'</div></div></div>'
    )
    st.markdown(preview_html, unsafe_allow_html=True)


def _render_agent_idle_state():
    idle_html = (
        f'<div style="background:#F8F9FB;border:1px dashed {COLOR_BORDER};'
        f'border-radius:12px;padding:40px 24px;text-align:center;min-height:300px;'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;">'
        f'<div style="width:48px;height:48px;background:{COLOR_BG_SOFT};'
        f'border-radius:12px;display:flex;align-items:center;justify-content:center;'
        f'margin-bottom:16px;">'
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{COLOR_PRIMARY}" stroke-width="2">'
        f'<path d="M12 2L2 7l10 5 10-5-10-5z"/>'
        f'<path d="M2 17l10 5 10-5"/>'
        f'<path d="M2 12l10 5 10-5"/></svg></div>'
        f'<div style="font-size:15px;font-weight:500;color:{COLOR_PRIMARY};'
        f'margin-bottom:6px;">AdoptSense AI Agent</div>'
        f'<div style="font-size:13px;color:{COLOR_TEXT_MUTED};max-width:280px;'
        f'line-height:1.5;">Upload photos and click "Run AI Agent" to optimize '
        f'your listing for fastest adoption.</div></div>'
    )
    st.markdown(idle_html, unsafe_allow_html=True)


def _render_agent_panel(result: dict):
    photo_count = len(result.get("enhanced_photos", [])) or 4
    sentiment = result.get("sentiment_score", 0.0)
    speed_label = result.get("predicted_speed_label", "—")
    iterations = result.get("iterations", 0)

    steps = [
        ("✓", "#4CAF50", f"Photos enhanced ({photo_count} of {photo_count})"),
        ("✓", "#4CAF50", f"Description generated (sentiment +{sentiment:.2f})"),
        ("✓", "#4CAF50", f"Predicted adoption speed: {speed_label}"),
        (str(iterations), "rgba(255,255,255,0.2)",
         f"Completed {iterations} optimization iterations"),
    ]

    steps_html = ""
    for badge, bg, label in steps:
        steps_html += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-top:1px solid rgba(255,255,255,0.15);">'
            f'<div style="width:18px;height:18px;background:{bg};border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;font-size:10px;'
            f'flex-shrink:0;">{badge}</div>'
            f'<span style="opacity:0.95;font-size:13px;">{label}</span></div>'
        )

    panel_html = (
        f'<div style="background:linear-gradient(135deg,{COLOR_PRIMARY} 0%,{COLOR_PRIMARY_LIGHT} 100%);'
        f'border-radius:12px;padding:20px;color:#FFFFFF;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">'
        f'<div style="width:36px;height:36px;background:rgba(255,255,255,0.15);'
        f'border-radius:8px;display:flex;align-items:center;justify-content:center;">'
        f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
        f'stroke="#FFFFFF" stroke-width="2">'
        f'<path d="M12 2L2 7l10 5 10-5-10-5z"/>'
        f'<path d="M2 17l10 5 10-5"/>'
        f'<path d="M2 12l10 5 10-5"/></svg></div>'
        f'<div><div style="font-size:14px;font-weight:500;">AdoptSense AI Agent</div>'
        f'<div style="font-size:11px;opacity:0.7;">Optimizing for fastest adoption</div>'
        f'</div></div>'
        f'{steps_html}</div>'
    )
    st.markdown(panel_html, unsafe_allow_html=True)


def _render_prediction_card(result: dict):
    speed_label = result.get("predicted_speed_label", "—")
    previous = result.get("previous_speed_label")
    confidence = result.get("confidence", 0.0)
    predicted_speed = result.get("predicted_speed", 0)

    delta_html = ""
    if previous:
        delta_html = (
            f'<span style="font-size:13px;color:#4CAF50;font-weight:500;">'
            f'↑ from {previous}</span>'
        )

    segments = ""
    for i in range(5):
        color = "#4CAF50" if i <= predicted_speed else COLOR_BORDER
        segments += (
            f'<div style="flex:1;height:6px;background:{color};border-radius:2px;"></div>'
        )

    card_html = (
        f'<div style="background:#FFFFFF;border:1px solid {COLOR_BORDER};'
        f'border-radius:12px;padding:18px;">'
        f'<div style="font-size:12px;color:{COLOR_TEXT_MUTED};margin-bottom:8px;'
        f'letter-spacing:0.3px;">PREDICTED ADOPTION SPEED</div>'
        f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:14px;">'
        f'<span style="font-size:28px;font-weight:600;color:{COLOR_PRIMARY};">{speed_label}</span>'
        f'{delta_html}</div>'
        f'<div style="display:flex;gap:4px;margin-bottom:6px;">{segments}</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:10px;'
        f'color:{COLOR_TEXT_MUTED};">'
        f'<span>Same day</span><span>1-7d</span><span>8-30d</span>'
        f'<span>31-90d</span><span>No adoption</span></div>'
        f'<div style="margin-top:14px;padding-top:14px;border-top:1px solid #F3F4F6;'
        f'font-size:12px;color:{COLOR_TEXT_BODY};">'
        f'Confidence: <span style="color:{COLOR_PRIMARY};font-weight:500;">'
        f'{confidence:.0%}</span> · Based on 15,000+ adoption outcomes</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def _render_recommendations_card(recommendations: list):
    if not recommendations:
        return
    items = ""
    for rec in recommendations:
        items += (
            f'<div style="display:flex;gap:8px;align-items:flex-start;'
            f'font-size:13px;color:{COLOR_PRIMARY};padding:4px 0;">'
            f'<span style="color:#92400E;font-weight:500;">→</span>'
            f'<span>{rec}</span></div>'
        )

    card_html = (
        f'<div style="background:#FFFBEB;border:1px solid #F4D484;border-radius:12px;'
        f'padding:18px;">'
        f'<div style="font-size:12px;font-weight:500;color:#92400E;'
        f'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px;">'
        f'⚡ Agent Recommendations</div>'
        f'{items}</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def _render_publish_section():
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button("📤 Publish Listing", type="primary",
                     use_container_width=True, key="publish_listing_btn"):
            st.balloons()
            st.success("Listing published! Visible to adopters in your area.")
            st.session_state.agent_result = None
