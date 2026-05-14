"""
Marketplace UI — AdoptSense.

Public functions called by app.py:
  render_browse(user)
  render_detail(listing_id, user)
  render_my_listings(user)
  render_create_listing(user)
  render_edit_listing(listing_id, user)
  render_kpis(user)
  render_watchlist(user)
  render_chat(user)
  render_profile(user)
  render_shelter_map(user)
"""
import json
import uuid
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_BG_SOFT, COLOR_BORDER,
    COLOR_TEXT_BODY, COLOR_TEXT_MUTED, SPEED_COLORS, logo_img_tag,
)
from frontend.components.pet_card import render_pet_card
from frontend.utils import auth, db, gemini_utils
from frontend.utils.matching_platform import (
    ADOPTION_SPEED_COLORS, ADOPTION_SPEED_EMOJI, ADOPTION_SPEED_LABELS,
    COLOR_MAP, DEWORMED_MAP, FUR_MAP, GENDER_MAP, HEALTH_MAP,
    STERILIZED_MAP, SIZE_MAP, STATE_MAP, TYPE_MAP, VACCINATED_MAP,
    speed_badge_html,
)
from frontend.utils.predictions import make_prediction
from frontend.utils.recommendations import get_adoption_factors

UPLOAD_DIR = db.UPLOAD_DIR
STUDIO_DIR = db.STUDIO_DIR

_LOCATIONS_PATH = Path(__file__).parent.parent / "assets" / "shelter_locations.json"


@st.cache_data
def _load_locations() -> dict:
    try:
        return json.loads(_LOCATIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"shelters": [], "countries": [], "cities_by_country": {}}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _nav(view: str, **kwargs):
    st.session_state.mp_view = view
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _img_bytes(path: str) -> bytes | None:
    try:
        return Path(path).read_bytes()
    except Exception:
        return None


def _save_upload(uploaded, listing_id: int) -> str:
    dest_dir = UPLOAD_DIR / str(listing_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_{uploaded.name}"
    dest = dest_dir / fname
    try:
        uploaded.seek(0)
    except Exception:
        pass
    data = uploaded.read()
    if not data:
        raise IOError(f"Upload {uploaded.name} produced empty bytes — file handle expired")
    dest.write_bytes(data)
    return str(dest)


def _save_upload_bytes(name: str, data: bytes, listing_id: int) -> str:
    dest_dir = UPLOAD_DIR / str(listing_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_{name}"
    dest = dest_dir / fname
    dest.write_bytes(data)
    return str(dest)


def _show_gallery(photos: list[dict], max_cols: int = 3):
    valid = [p for p in photos if _img_bytes(p["photo_path"])]
    if not valid:
        st.caption("No photos available.")
        return
    cols = st.columns(min(len(valid), max_cols))
    for i, p in enumerate(valid):
        data = _img_bytes(p["photo_path"])
        with cols[i % max_cols]:
            st.image(data, width='stretch')
            if p.get("is_studio_ready") and p.get("studio_photo_path"):
                s_bytes = _img_bytes(p["studio_photo_path"])
                if s_bytes:
                    st.download_button(
                        "⬇️ Studio photo",
                        data=s_bytes,
                        file_name=f"studio_{p['id']}.png",
                        mime="image/png",
                        key=f"dl_studio_{p['id']}",
                    )


def _info_box_html(label: str, value: str) -> str:
    return (
        f'<div style="background:#FFFFFF;border:1px solid {COLOR_BORDER};'
        f'border-radius:10px;padding:12px;">'
        f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};margin-bottom:4px;">'
        f'{label}</div>'
        f'<div style="font-size:14px;font-weight:500;color:{COLOR_PRIMARY};">'
        f'{value}</div></div>'
    )


def _factor_card(fac: dict, kind: str = "positive"):
    if kind == "positive":
        bg, border, accent = "#F0F9F2", "#B5D8C0", "#2E7D32"
    else:
        bg, border, accent = "#FDF2F2", "#F5C2C2", "#B71C1C"
    html = (
        f'<div style="background:{bg};border:1px solid {border};border-radius:10px;'
        f'padding:12px 14px;margin-bottom:10px;">'
        f'<div style="font-size:13px;font-weight:600;color:{accent};margin-bottom:4px;">'
        f'{fac["label"]}</div>'
        f'<div style="font-size:12px;color:{COLOR_TEXT_BODY};line-height:1.45;">'
        f'{fac["sentence"]}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Filters ────────────────────────────────────────────────────────────────────

def _render_filters(is_manager: bool) -> dict:
    locs = _load_locations()
    countries = ["All"] + locs.get("countries", [])
    cities_by_country = locs.get("cities_by_country", {})

    _FILTER_KEYS = [
        "f_type", "f_gender", "f_size", "f_age", "f_fee", "f_col",
        "f_vacc", "f_dew", "f_ster", "f_health",
        "f_country", "f_city", "f_postal", "f_shelter", "f_speed",
    ]

    with st.expander("🔍 Filters", expanded=False):
        _reset_col, _ = st.columns([1, 5])
        with _reset_col:
            if st.button("Reset filters", key="f_reset", type="secondary"):
                for _k in _FILTER_KEYS:
                    st.session_state.pop(_k, None)
                st.rerun()

        c1, c2, c3 = st.columns(3)
        f: dict = {}

        with c1:
            t = st.selectbox("Pet type", [0, 1, 2],
                             format_func=lambda x: "All" if x == 0 else TYPE_MAP[x], key="f_type")
            if t:
                f["type"] = t
            g = st.selectbox("Gender", [0, 1, 2, 3],
                             format_func=lambda x: "All" if x == 0 else GENDER_MAP[x], key="f_gender")
            if g:
                f["gender"] = g
            sz = st.selectbox("Maturity size", [0, 1, 2, 3, 4],
                              format_func=lambda x: "All" if x == 0 else SIZE_MAP[x], key="f_size")
            if sz:
                f["maturity_size"] = sz

        with c2:
            age_r = st.slider("Age (months)", 0, 120, (0, 120), key="f_age")
            if age_r != (0, 120):
                f["min_age"] = age_r[0]
                f["max_age"] = age_r[1]
            max_fee = st.number_input("Max fee (€)", 0, 5000, 5000, step=50, key="f_fee")
            if max_fee < 5000:
                f["max_fee"] = max_fee
            col = st.selectbox("Primary color", list(COLOR_MAP.keys()),
                               format_func=lambda x: COLOR_MAP[x], key="f_col")
            if col != 0:
                f["color1"] = col

        with c3:
            vacc = st.selectbox("Vaccinated", [0, 1, 2, 3],
                                format_func=lambda x: "Any" if x == 0 else VACCINATED_MAP[x], key="f_vacc")
            if vacc:
                f["vaccinated"] = vacc
            dew = st.selectbox("Dewormed", [0, 1, 2, 3],
                               format_func=lambda x: "Any" if x == 0 else DEWORMED_MAP[x], key="f_dew")
            if dew:
                f["dewormed"] = dew
            ster = st.selectbox("Sterilized", [0, 1, 2, 3],
                                format_func=lambda x: "Any" if x == 0 else STERILIZED_MAP[x], key="f_ster")
            if ster:
                f["sterilized"] = ster
            hlth = st.selectbox("Health", [0, 1, 2, 3],
                                format_func=lambda x: "Any" if x == 0 else HEALTH_MAP[x], key="f_health")
            if hlth:
                f["health"] = hlth

        # ── Location filter ────────────────────────────────────────────────
        st.markdown("**📍 Location**")
        loc_c1, loc_c2, loc_c3 = st.columns(3)
        with loc_c1:
            sel_country = st.selectbox("Country", countries, key="f_country")
            if sel_country != "All":
                f["country"] = sel_country
        with loc_c2:
            city_options = ["All"]
            if sel_country != "All" and sel_country in cities_by_country:
                city_options += [c["city"] for c in cities_by_country[sel_country]]
            sel_city = st.selectbox("City", city_options, key="f_city")
            if sel_city != "All":
                f["city"] = sel_city
        with loc_c3:
            postal_input = st.text_input("Postal code", key="f_postal", placeholder="e.g. 1100")
            if postal_input.strip():
                f["postal_code"] = postal_input.strip()

        # ── Shelter filter ─────────────────────────────────────────────────
        shelters = db.get_all_shelters()
        s_opts = {0: "All shelters"}
        s_opts.update({s["id"]: s["shelter_name"] or s["username"] for s in shelters})
        sel_s = st.selectbox("From shelter", list(s_opts.keys()),
                             format_func=lambda x: s_opts[x], key="f_shelter")
        if sel_s:
            f["shelter_id"] = sel_s

        if is_manager:
            spd = st.selectbox(
                "Max predicted speed",
                options=[-1, 0, 1, 2, 3, 4],
                format_func=lambda x: "Any" if x == -1
                else f"Speed {x} — {ADOPTION_SPEED_LABELS[x]}",
                key="f_speed"
            )
            if spd >= 0:
                f["max_speed"] = spd
    return f


# ── Engagement tracking & survey ──────────────────────────────────────────────

def _get_survey_thresholds() -> list[int]:
    """Light touch at start, plateau every 100 after 50 actions."""
    early = [10, 30, 50]
    plateau = list(range(100, 2001, 100))
    return early + plateau


def _track_action(user: dict | None):
    """Increment household user's action count; set survey flag when threshold crossed."""
    if not user or user.get("role") != "household":
        return
    new_count = db.increment_action_count(user["id"])
    completed = db.get_completed_survey_thresholds(user["id"])
    for threshold in _get_survey_thresholds():
        if new_count >= threshold and threshold not in completed:
            st.session_state["_survey_threshold"] = threshold
            break


def _maybe_show_survey(user: dict | None) -> bool:
    """Render a full-page darkened modal survey when a threshold has been crossed.
    Returns True if the survey was displayed (caller should stop rendering other content)."""
    threshold = st.session_state.get("_survey_threshold")
    if not threshold or not user:
        return False

    # Dim the page background without a z-index overlay (which would cover widgets).
    # Since render_browse() returns early after this survey, there is nothing else
    # on screen — we just darken the app shell so the card stands out.
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] {
            background: rgba(10, 15, 40, 0.90) !important;
        }
        [data-testid="stHeader"] {
            background: rgba(10, 15, 40, 0.90) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:60px;"></div>', unsafe_allow_html=True)
    _, survey_col, _ = st.columns([1, 3, 1])
    with survey_col:
        with st.container(border=True):
            st.markdown(
                f'<div style="text-align:center;padding:8px 0 4px;">'
                f'<span style="font-size:32px;">🎉</span>'
                f'<h2 style="color:{COLOR_PRIMARY};font-size:20px;font-weight:700;'
                f'margin:8px 0 4px;">You\'ve explored {threshold} pets!</h2>'
                f'<p style="color:{COLOR_TEXT_MUTED};font-size:13px;margin:0 0 16px;">'
                f'Help us improve AdoptSense — takes just 5 seconds.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            score = st.radio(
                "How would you rate your experience so far?",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: "⭐" * x,
                horizontal=True,
                key=f"_survey_score_{threshold}",
                index=4,
            )
            comment = st.text_input(
                "Anything to add? (optional)",
                key=f"_survey_comment_{threshold}",
                placeholder="What do you love or what could be better?",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Submit ✓", key=f"_survey_submit_{threshold}",
                             type="primary", use_container_width=True):
                    db.save_user_survey(
                        user["id"], threshold, score,
                        st.session_state.get(f"_survey_comment_{threshold}", ""),
                    )
                    st.session_state.pop("_survey_threshold", None)
                    st.toast("Thanks for your feedback!", icon="💙")
                    st.rerun()
            with c2:
                if st.button("Skip →", key=f"_survey_skip_{threshold}",
                             use_container_width=True):
                    db.save_user_survey(user["id"], threshold, None, "")
                    st.session_state.pop("_survey_threshold", None)
                    st.rerun()
    return True


# ── Browse ─────────────────────────────────────────────────────────────────────

def render_browse(user: dict | None):
    is_manager = bool(user and user.get("role") == "shelter_manager")
    is_household = bool(user and user.get("role") == "household")

    if is_household:
        if _maybe_show_survey(user):
            return  # everything else is darkened behind the survey modal

    # ── Smart AI Filter (households only) ─────────────────────────────────────
    if is_household and gemini_utils.is_configured():
        if st.session_state.get("_smart_filter_text") and "_smart_ranked" not in st.session_state:
            _all_for_ai = db.get_listings({})
            with gemini_utils.ai_loading("Finding your perfect match…"):
                _ranked = gemini_utils.smart_match_pets(
                    st.session_state["_smart_filter_text"], _all_for_ai
                )
            st.session_state["_smart_ranked"] = _ranked
            st.rerun()

        with st.expander(
            "🔮 Smart AI Filter — describe your ideal pet",
            expanded=bool(st.session_state.get("_smart_filter_text")),
        ):
            _smart_q = st.text_input(
                "Describe what you're looking for",
                placeholder='e.g. "a calm small dog for an apartment, good with children"',
                key="smart_filter_query",
                label_visibility="collapsed",
            )
            _sq_run, _sq_clear = st.columns([2, 1])
            with _sq_run:
                if st.button("🔍 Find best matches", key="smart_filter_btn", use_container_width=True):
                    if _smart_q.strip():
                        st.session_state["_smart_filter_text"] = _smart_q.strip()
                        st.session_state.pop("_smart_ranked", None)
                        st.rerun()
                    else:
                        st.warning("Please describe your ideal pet first.")
            with _sq_clear:
                if st.session_state.get("_smart_filter_text"):
                    if st.button("✕ Clear", key="smart_filter_clear", use_container_width=True):
                        st.session_state.pop("_smart_filter_text", None)
                        st.session_state.pop("_smart_ranked", None)
                        st.rerun()
            if st.session_state.get("_smart_filter_text"):
                st.caption(f'Matching: "{st.session_state["_smart_filter_text"]}"')

    filters = _render_filters(is_manager=is_manager)
    listings = db.get_listings(filters)

    if not listings:
        st.info("No listings match your filters.")
        return

    # Apply AI smart ranking if active
    if is_household and "_smart_ranked" in st.session_state:
        _ranked_list = st.session_state["_smart_ranked"]
        _id_to_ranked = {l["id"]: l for l in _ranked_list}
        _id_to_fetched = {l["id"]: l for l in listings}
        ordered = []
        for ranked_l in _ranked_list:
            lid = ranked_l["id"]
            if lid in _id_to_fetched:
                merged = dict(_id_to_fetched[lid])
                merged["compatibility_percentage"] = ranked_l.get("compatibility_percentage")
                ordered.append(merged)
        for l in listings:
            if l["id"] not in _id_to_ranked:
                ordered.append(l)
        listings = ordered
        st.caption(f"🔮 AI-ranked — {len(listings)} pets sorted by best match")
    else:
        st.caption(f"{len(listings)} pets available")

    # 3-column grid
    cols = st.columns(3, gap="medium")
    for i, listing in enumerate(listings):
        with cols[i % 3]:
            compat = listing.get("compatibility_percentage")
            render_pet_card(listing, show_speed=is_manager, key_prefix="browse",
                            compatibility_pct=compat)


# ── Detail ─────────────────────────────────────────────────────────────────────

def render_detail(listing_id: int, user: dict | None):
    listing = db.get_listing(listing_id)
    if not listing:
        st.error("Listing not found.")
        if st.button("← Back to Browse", key="detail_back_missing"):
            _nav("browse")
        return

    db.increment_views(listing_id)
    _track_action(user)

    if st.button("← Back", key=f"detail_back_{listing_id}"):
        _nav("browse")

    # ── 1st RANK: Key info — prominent at the top ──────────────────────────────
    pet_name = listing.get("pet_name", "—")
    age_months = listing.get("age", 0)
    age_label = (f"{int(age_months / 12)} yr" if age_months >= 12 else f"{int(age_months)} mo")
    type_label = TYPE_MAP.get(listing.get("type", 1), "Pet")
    gender_label = GENDER_MAP.get(listing.get("gender", 1), "")
    state_label = STATE_MAP.get(listing.get("state", 0), "")
    country = listing.get("country") or "Malaysia"
    city = listing.get("city") or state_label

    st.markdown(
        f'<h1 style="font-size:36px;font-weight:600;color:{COLOR_PRIMARY};margin:4px 0 4px;'
        f'letter-spacing:-0.5px;">{pet_name}</h1>'
        f'<div style="font-size:15px;color:{COLOR_TEXT_BODY};margin-bottom:20px;">'
        f'{type_label} · {age_label} · {gender_label} &nbsp;·&nbsp; '
        f'<span style="color:{COLOR_TEXT_MUTED};">📍 {city}, {country}</span></div>',
        unsafe_allow_html=True,
    )

    photos = db.get_photos(listing_id)
    col_photo, col_info = st.columns([1.2, 1], gap="large")

    with col_photo:
        _show_gallery(photos)

    with col_info:
        fee_value = listing.get("fee", 0) or 0
        fee_label = "Free" if fee_value == 0 else f"€{int(fee_value)}"
        vacc_val = VACCINATED_MAP.get(listing.get("vaccinated", 3), "?")
        ster_val = STERILIZED_MAP.get(listing.get("sterilized", 3), "?")
        dew_val = DEWORMED_MAP.get(listing.get("dewormed", 3), "?")
        health_val = HEALTH_MAP.get(listing.get("health", 1), "?")

        # Primary info grid (2x3)
        info_grid = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">'
            f'{_info_box_html("Adoption Fee", fee_label)}'
            f'{_info_box_html("Health", health_val)}'
            f'{_info_box_html("Vaccinated", vacc_val)}'
            f'{_info_box_html("Sterilized", ster_val)}'
            f'{_info_box_html("Dewormed", dew_val)}'
            f'{_info_box_html("Quantity", str(listing.get("quantity", 1)))}'
            f'</div>'
        )
        st.markdown(info_grid, unsafe_allow_html=True)

        # Shelter card
        shelter_name = (listing.get("shelter_name") or listing.get("shelter_username", "Unknown shelter"))
        initials = "".join([w[0] for w in shelter_name.split()[:2]]).upper() or "?"
        shelter_addr = listing.get("shelter_address") or listing.get("shelter_location") or ""
        shelter_html = (
            f'<div style="background:#F8F9FB;border:1px solid {COLOR_BORDER};'
            f'border-radius:12px;padding:14px;margin-bottom:16px;display:flex;'
            f'align-items:center;gap:12px;">'
            f'<div style="width:40px;height:40px;background:{COLOR_PRIMARY};'
            f'color:#FFFFFF;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;font-weight:500;flex-shrink:0;font-size:13px;">'
            f'{initials}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:13px;font-weight:500;color:{COLOR_PRIMARY};">{shelter_name}</div>'
            f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};">Listed {listing.get("created_at", "")[:10]}</div>'
            f'{"<div style=" + chr(34) + "font-size:11px;color:" + COLOR_TEXT_MUTED + ";" + chr(34) + ">" + shelter_addr + "</div>" if shelter_addr else ""}'
            f'</div></div>'
        )
        st.markdown(shelter_html, unsafe_allow_html=True)

    # ── Description ───────────────────────────────────────────────────────────
    st.markdown("---")
    desc = listing.get("description_improved") or listing.get("description") or ""
    _d_hdr_col, _d_tts_col = st.columns([4, 1])
    with _d_hdr_col:
        st.markdown(f"<h3 style='color:{COLOR_PRIMARY};font-weight:600;margin-bottom:8px;'>About {pet_name}</h3>",
                    unsafe_allow_html=True)
    with _d_tts_col:
        if desc and gemini_utils.is_configured():
            _tts_key = f"tts_audio_{listing_id}"
            if st.button("🔊 Listen", key=f"tts_btn_{listing_id}", use_container_width=True):
                with gemini_utils.ai_loading("Generating audio description…"):
                    _tts_ok, _tts_res = gemini_utils.text_to_speech(desc)
                if _tts_ok:
                    st.session_state[_tts_key] = _tts_res
                else:
                    st.warning(f"Audio unavailable: {_tts_res}")
                st.rerun()
            if st.session_state.get(_tts_key):
                st.audio(st.session_state[_tts_key], format="audio/wav")

    if listing.get("description_improved") and listing.get("description"):
        with st.expander("Show original description"):
            st.caption(listing["description"])
    st.markdown(desc if desc else "*No description provided.*")

    # ── Household: save / message ─────────────────────────────────────────────
    if user and user.get("role") == "household":
        st.markdown("---")
        wl_col, msg_col = st.columns(2, gap="small")
        with wl_col:
            in_wl = db.is_in_watchlist(user["id"], listing_id)
            if in_wl:
                if st.button("💔 Remove from Watchlist", use_container_width=True,
                             key=f"detail_unsave_{listing_id}"):
                    db.remove_from_watchlist(user["id"], listing_id)
                    st.rerun()
            else:
                if st.button("❤️ Add to Watchlist", type="primary",
                             use_container_width=True, key=f"detail_save_{listing_id}"):
                    db.add_to_watchlist(user["id"], listing_id)
                    _track_action(user)
                    st.success("Added to watchlist!")
                    st.rerun()
        with msg_col:
            shelter_uid = listing.get("shelter_user_id") or listing.get("shelter_id")
            if st.button("💬 Message Shelter", use_container_width=True,
                         key=f"detail_msg_{listing_id}"):
                _nav("chat", mp_chat_with=shelter_uid)

    elif not user:
        st.markdown("---")
        st.info("Log in to save this pet or message the shelter.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Log In", key="detail_guest_login", use_container_width=True):
                st.session_state.show_auth = "login"
                st.rerun()
        with c2:
            if st.button("Register", type="primary",
                         key="detail_guest_register", use_container_width=True):
                st.session_state.show_auth = "register"
                st.rerun()

    # ── 2nd RANK: Secondary info — at the bottom ──────────────────────────────
    st.markdown("---")
    with st.expander("📋 Full characteristics", expanded=False):
        sec_c1, sec_c2 = st.columns(2)
        with sec_c1:
            st.markdown("**Breed & Appearance**")
            b1 = listing.get("breed1", 0)
            b2 = listing.get("breed2", 0)
            st.markdown(f"- Primary breed ID: `{b1}`")
            if b2:
                st.markdown(f"- Secondary breed ID: `{b2}`")
            st.markdown(f"- Fur length: {FUR_MAP.get(listing.get('fur_length', 0), 'N/A')}")
            st.markdown(f"- Maturity size: {SIZE_MAP.get(listing.get('maturity_size', 0), 'N/A')}")
            c1v = COLOR_MAP.get(listing.get("color1", 0), "None")
            c2v = COLOR_MAP.get(listing.get("color2", 0), "None")
            c3v = COLOR_MAP.get(listing.get("color3", 0), "None")
            st.markdown(f"- Colors: {c1v}" + (f", {c2v}" if c2v != "None" else "") + (f", {c3v}" if c3v != "None" else ""))
        with sec_c2:
            st.markdown("**Listing Details**")
            st.markdown(f"- Region/State: {STATE_MAP.get(listing.get('state', 0), 'N/A')}")
            st.markdown(f"- Country: {listing.get('country', 'Malaysia')}")
            if listing.get("city"):
                st.markdown(f"- City: {listing['city']}")
            if listing.get("postal_code"):
                st.markdown(f"- Postal code: {listing['postal_code']}")
            st.markdown(f"- Photos: {listing.get('photo_amt', 0)}")
            st.markdown(f"- Videos: {listing.get('video_amt', 0)}")
            st.markdown(f"- Listed: {listing.get('created_at', '')[:10]}")
            if listing.get("adopted_at"):
                st.markdown(f"- Adopted: {listing['adopted_at'][:10]}")

    # ── Shelter manager performance panel (no studio in view mode) ────────────
    if (user and user.get("role") == "shelter_manager"
            and user["id"] == listing.get("shelter_id")):
        _render_manager_listing_panel(listing, listing_id, photos)


def _render_manager_listing_panel(listing: dict, listing_id: int, photos: list):
    """KPI + adoption factors for shelter manager — NO photo studio in view mode."""
    st.markdown("---")
    st.markdown(f"<h3 style='color:{COLOR_PRIMARY};font-weight:600;'>📊 Listing Performance</h3>",
                unsafe_allow_html=True)

    speed = listing.get("adoption_speed_pred")
    if speed is not None:
        st.markdown(
            speed_badge_html(speed, listing.get("adoption_speed_confidence") or 0),
            unsafe_allow_html=True,
        )
        st.markdown("")

    kpi = db.get_listing_kpi(listing_id)
    if kpi:
        kc1, kc2, kc3 = st.columns(3)
        kc1.metric("Views", kpi.get("views", 0))
        kc2.metric("Contacts", kpi.get("contacts", 0))
        kc3.metric("LOS (days)", kpi.get("adoption_time_days") or "—")

    pet_dict = {
        "PhotoAmt": listing.get("photo_amt", 0),
        "Fee": listing.get("fee", 0),
        "Age": listing.get("age", 0),
        "Health": listing.get("health", 1),
        "Vaccinated": listing.get("vaccinated", 3),
        "Dewormed": listing.get("dewormed", 3),
        "Sterilized": listing.get("sterilized", 3),
        "MaturitySize": listing.get("maturity_size", 0),
        "Quantity": listing.get("quantity", 1),
        "VideoAmt": listing.get("video_amt", 0),
        "Description": listing.get("description", ""),
    }
    pos_f, neg_f = get_adoption_factors(pet_dict)
    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown("**✅ Helping adoption**")
        for fac in pos_f:
            _factor_card(fac, kind="positive")
        if not pos_f:
            st.caption("No strong positive factors identified.")
    with fc2:
        st.markdown("**⚠️ Hindering adoption**")
        for fac in neg_f:
            _factor_card(fac, kind="negative")
        if not neg_f:
            st.caption("No significant hindering factors.")

    st.markdown("---")
    act1, act2, act3 = st.columns(3)
    with act1:
        if st.button("✏️ Edit Listing", use_container_width=True,
                     key=f"manage_edit_{listing_id}"):
            _nav("edit", mp_listing_id=listing_id)
    with act2:
        if listing.get("status") == "available":
            if st.button("✅ Mark as Adopted", use_container_width=True,
                         key=f"manage_adopt_{listing_id}"):
                db.mark_adopted(listing_id, listing.get("adoption_speed_pred", 2))
                st.success("Marked as adopted!")
                st.rerun()
    with act3:
        if st.button("🗑️ Delete", use_container_width=True, type="secondary",
                     key=f"manage_delete_{listing_id}"):
            st.session_state.confirm_delete = listing_id

    if st.session_state.get("confirm_delete") == listing_id:
        st.warning("Delete this listing? This cannot be undone.")
        y, n = st.columns(2)
        with y:
            if st.button("Yes, delete", key="cdel_y"):
                for p in photos:
                    try:
                        Path(p["photo_path"]).unlink(missing_ok=True)
                    except Exception:
                        pass
                db.delete_listing(listing_id)
                st.session_state.pop("confirm_delete", None)
                _nav("my_listings")
        with n:
            if st.button("Cancel", key="cdel_n"):
                st.session_state.pop("confirm_delete", None)
                st.rerun()


# ── My Listings ────────────────────────────────────────────────────────────────

def render_my_listings(user: dict):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>📋 My Listings</h1>",
                unsafe_allow_html=True)
    listings = db.get_shelter_listings(user["id"])

    if not listings:
        st.info("No listings yet.")
        if st.button("➕ Create First Listing", type="primary"):
            _nav("create")
        return

    active = [l for l in listings if l["status"] == "available"]
    adopted = [l for l in listings if l["status"] == "adopted"]
    rate = len(adopted) / len(listings) * 100 if listings else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(listings))
    c2.metric("Active", len(active))
    c3.metric("Adopted", len(adopted))
    c4.metric("Adoption rate", f"{rate:.1f}%")

    st.markdown("---")
    status_f = st.selectbox("Show", ["All", "Active", "Adopted"], key="ml_sf")
    shown = listings if status_f == "All" else (active if status_f == "Active" else adopted)

    for listing in shown:
        with st.container(border=True):
            lc1, lc2, lc3 = st.columns([4, 1, 1])
            with lc1:
                speed = listing.get("adoption_speed_pred")
                badge = (f" {ADOPTION_SPEED_EMOJI.get(speed, '')} {ADOPTION_SPEED_LABELS.get(speed, '')}"
                         if speed is not None else "")
                st.markdown(f"**{listing['pet_name']}** —{badge}")
                icon = "🟢" if listing["status"] == "available" else "✅"
                st.caption(
                    f"{icon} {listing['status'].title()} · "
                    f"{listing['created_at'][:10]} · "
                    f"Views: {listing.get('views') or 0} · "
                    f"Contacts: {listing.get('contacts') or 0}"
                )
            with lc2:
                if st.button("📋 View", key=f"mlv_{listing['id']}",
                             use_container_width=True):
                    _nav("detail", mp_listing_id=listing["id"])
            with lc3:
                if listing["status"] == "available":
                    if st.button("✅ Adopted", key=f"mla_{listing['id']}",
                                 use_container_width=True):
                        db.mark_adopted(listing["id"], listing.get("adoption_speed_pred", 2))
                        st.rerun()


# ── Create Listing ─────────────────────────────────────────────────────────────

BREED_DATA = [
    (307, 1, "Mixed Breed"), (20, 1, "Beagle"), (44, 1, "Boxer"),
    (60, 1, "Chihuahua"), (65, 1, "Chow Chow"), (75, 1, "Dachshund"),
    (76, 1, "Dalmatian"), (78, 1, "Doberman Pinscher"), (82, 1, "English Bulldog"),
    (100, 1, "French Bulldog"), (103, 1, "German Shepherd Dog"),
    (109, 1, "Golden Retriever"), (111, 1, "Great Dane"), (119, 1, "Husky"),
    (141, 1, "Labrador Retriever"), (147, 1, "Maltese"), (178, 1, "Pomeranian"),
    (179, 1, "Poodle"), (182, 1, "Pug"), (189, 1, "Rottweiler"),
    (192, 1, "Samoyed"), (205, 1, "Shih Tzu"), (206, 1, "Siberian Husky"),
    (240, 1, "Yorkshire Terrier"),
    (265, 2, "Domestic Medium Hair"), (266, 2, "Domestic Short Hair"),
    (264, 2, "Domestic Long Hair"), (285, 2, "Persian"), (292, 2, "Siamese"),
    (247, 2, "Bengal"), (251, 2, "British Shorthair"), (271, 2, "Himalayan"),
    (276, 2, "Maine Coon"), (288, 2, "Ragdoll"), (289, 2, "Russian Blue"),
    (299, 2, "Tabby"), (306, 2, "Tuxedo"),
]


def _render_publish_confirmation():
    """Success screen after publishing — animated, with 3 CTAs."""
    new_listing_id = st.session_state.get("_cl_published_id")
    listing = db.get_listing(new_listing_id) if new_listing_id else None
    pet_name = listing.get("pet_name", "Your pet") if listing else "Your pet"

    b64 = __import__("frontend.styles", fromlist=["logo_png_b64"]).logo_png_b64()
    logo_html = (
        f'<img src="data:image/png;base64,{b64}" width="80" '
        f'style="object-fit:contain;margin-bottom:16px;" alt="AdoptSense"/>'
        if b64 else ""
    )

    st.markdown(
        f"""
        <style>
        @keyframes as_check_pop {{
            0%   {{ transform: scale(0.3) rotate(-10deg); opacity: 0; }}
            60%  {{ transform: scale(1.2) rotate(4deg); opacity: 1; }}
            80%  {{ transform: scale(0.92) rotate(-2deg); }}
            100% {{ transform: scale(1) rotate(0deg); }}
        }}
        .as-pub-success {{ animation: as_check_pop 0.65s cubic-bezier(0.34,1.56,0.64,1) forwards; }}
        </style>
        <div style="text-align:center;padding:56px 24px 40px;">
            {logo_html}
            <div class="as-pub-success" style="font-size:72px;line-height:1;margin-bottom:16px;">✅</div>
            <h1 style="font-size:30px;font-weight:600;color:{COLOR_PRIMARY};margin:0 0 8px;">
                Listing published!
            </h1>
            <p style="font-size:15px;color:{COLOR_TEXT_MUTED};margin:0 0 32px;">
                <strong>{pet_name}</strong> is now visible to adopters. AI predicts adoption chance is enhanced!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button("View Listing", type="primary",
                     use_container_width=True, key="pub_view"):
            _clear_publish_state()
            _nav("detail", mp_listing_id=new_listing_id)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Create Another", type="secondary",
                         use_container_width=True, key="pub_another"):
                _clear_publish_state()
                st.rerun()
        with c2:
            if st.button("Go to My Listings", type="secondary",
                         use_container_width=True, key="pub_my"):
                _clear_publish_state()
                _nav("my_listings")


def _clear_publish_state():
    st.session_state.pop("_cl_just_published", None)
    st.session_state.pop("_cl_published_id", None)
    for k in list(st.session_state.keys()):
        if k.startswith("cl_") and k != "cl_gem_key":
            st.session_state.pop(k, None)


def _render_photo_section(prefix: str, pet_type_key: str):
    """Shared photo upload + studio section for create and edit."""
    st.subheader("📸 Photos")
    _ptab_file, _ptab_cam = st.tabs(["📁 Select from device", "📷 Take photo"])
    with _ptab_file:
        uploaded_files = st.file_uploader(
            "Upload pet photos (JPG/PNG)",
            type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"{prefix}_photos"
        )
    with _ptab_cam:
        # Only render camera_input when user explicitly activates it
        cam_active_key = f"{prefix}_camera_active"
        if not st.session_state.get(cam_active_key):
            if st.button("📷 Start Camera", key=f"{prefix}_camera_start"):
                st.session_state[cam_active_key] = True
                st.rerun()
            st.caption("Click 'Start Camera' to activate the camera. The browser will ask for permission only then.")
        else:
            _cam_photo = st.camera_input("Take a photo of your pet", key=f"{prefix}_camera_photo")
            if st.button("Stop Camera", key=f"{prefix}_camera_stop"):
                st.session_state[cam_active_key] = False
                st.rerun()
            if _cam_photo:
                st.success("📸 Photo captured!")
                return list(uploaded_files or []), _cam_photo

    return list(uploaded_files or []), None


def _render_studio_for_files(all_files: list, prefix: str):
    """Studio (not Bokeh) photo processing for a list of uploaded files."""
    if not all_files:
        return

    for i, uf in enumerate(all_files):
        studio_key = f"{prefix}_studio_{i}"
        studio_fn_key = f"{prefix}_studio_fn_{i}"
        choice_key = f"{prefix}_studio_use_{i}"

        if st.session_state.get(studio_fn_key) != uf.name:
            for k in (studio_key, choice_key):
                st.session_state.pop(k, None)
        st.session_state[studio_fn_key] = uf.name

        try:
            uf.seek(0)
            upload_bytes = uf.read()
            uf.seek(0)
            if not upload_bytes:
                continue
        except Exception:
            continue

        studio_bytes = st.session_state.get(studio_key)

        st.caption(f"📸 **{uf.name}**")
        cols = st.columns(2)
        with cols[0]:
            st.caption("📷 Original")
            st.image(upload_bytes, width='stretch')
        with cols[1]:
            st.caption("🎨 Studio")
            if studio_bytes:
                st.image(studio_bytes, width='stretch')
            else:
                st.markdown(
                    "<div style='background:#F3F4F6;border-radius:8px;height:160px;"
                    "display:flex;align-items:center;justify-content:center;"
                    "color:#9CA3AF;font-size:13px;'>Not generated yet</div>",
                    unsafe_allow_html=True,
                )

        if st.button(
            "🎨 Generate Studio" if not studio_bytes else "🎨 Regenerate Studio",
            key=f"{prefix}_studio_btn_{i}",
            use_container_width=True,
            help="Sharp pet on a professional AI studio backdrop.",
        ):
            with gemini_utils.ai_loading("Creating studio photo…"):
                ok_s, result = gemini_utils.make_studio_ready_bytes(upload_bytes)
            if ok_s:
                st.session_state[studio_key] = result
                st.rerun()
            else:
                st.error(result)

        if studio_bytes:
            st.radio(
                "Which version to publish?",
                ["original", "studio"],
                format_func=lambda x: "📷 Original" if x == "original" else "🎨 Studio",
                key=choice_key,
                horizontal=True,
                index=1,
            )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


def _render_description_section(prefix: str, pet_type: int, pet_name: str, age: int,
                                  gender: int, health: int, vaccinated: int,
                                  sterilized: int, fee: float,
                                  all_files: list,
                                  existing_desc: str = "") -> tuple[str, str]:
    """Voice memo + transcript → description field + AI finalize button.
    Returns (raw_description, improved_description).
    """
    st.subheader("📝 Description")

    if gemini_utils.is_configured():
        _voice_memo = st.audio_input("🎙️ Record a voice memo (optional)", key=f"{prefix}_voice_memo")
        if _voice_memo is not None:
            if st.button("📝 Transcribe memo", key=f"{prefix}_transcribe_btn"):
                with gemini_utils.ai_loading("Transcribing your voice memo…"):
                    _t_ok, _transcript = gemini_utils.transcribe_audio(
                        _voice_memo.read(), _voice_memo.type or "audio/wav"
                    )
                if _t_ok:
                    # Paste directly into description — no intermediate step
                    st.session_state.pop(f"{prefix}_desc", None)
                    st.session_state[f"{prefix}_desc_prefill"] = _transcript
                    st.rerun()
                else:
                    st.warning(f"Transcription failed: {_transcript}")

    _desc_prefill = st.session_state.pop(f"{prefix}_desc_prefill", existing_desc)
    description = st.text_area(
        "Raw description (optional — used as context for AI generation)",
        value=_desc_prefill,
        height=100,
        placeholder="Personality, history, care needs…",
        key=f"{prefix}_desc",
    )

    # AI finalize button
    _gc, _cc = st.columns([3, 1])
    improved_desc_val = st.session_state.get(f"{prefix}_generated_desc", "")
    with _gc:
        if gemini_utils.is_configured():
            st.markdown(
                f'<div style="font-size:12px;color:{COLOR_TEXT_MUTED};margin-bottom:4px;">'
                f'✨ AI descriptions improve adoption chances by up to <strong>46%</strong></div>',
                unsafe_allow_html=True,
            )
            if st.button("✨ Finalize description with AI", key=f"{prefix}_gen_desc_btn",
                         use_container_width=True):
                base = description.strip() or (
                    f"{TYPE_MAP.get(pet_type, 'Pet')} named {pet_name or 'this pet'}"
                )
                first_bytes = None
                if all_files:
                    try:
                        all_files[0].seek(0)
                        first_bytes = all_files[0].read()
                        all_files[0].seek(0)
                    except Exception:
                        pass
                with gemini_utils.ai_loading("Finaling your description with AI…"):
                    ok, result = gemini_utils.improve_description(
                        base,
                        {"type": pet_type, "age": age, "gender": gender,
                         "health": health, "vaccinated": vaccinated,
                         "sterilized": sterilized, "fee": fee},
                        image_bytes=first_bytes,
                    )
                if ok:
                    st.session_state[f"{prefix}_generated_desc"] = result
                    st.session_state.pop(f"{prefix}_gen_desc_area", None)
                    st.rerun()
                else:
                    st.warning(result)
        else:
            st.caption("🔑 Configure a Gemini API key to enable AI description finalization.")
    with _cc:
        if st.session_state.get(f"{prefix}_generated_desc"):
            if st.button("✕ Clear AI", key=f"{prefix}_gen_desc_clear", use_container_width=True):
                st.session_state.pop(f"{prefix}_generated_desc", None)
                st.session_state.pop(f"{prefix}_gen_desc_area", None)
                st.rerun()

    if st.session_state.get(f"{prefix}_generated_desc"):
        st.success("✨ AI description ready — review and edit before publishing:")
        improved_desc_val = st.text_area(
            "AI description",
            value=st.session_state.get(f"{prefix}_generated_desc", ""),
            height=120, key=f"{prefix}_gen_desc_area", label_visibility="collapsed",
        )

    return description, improved_desc_val


def render_create_listing(user: dict):
    if st.session_state.get("_cl_just_published"):
        _render_publish_confirmation()
        return

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

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Basic Info")
        pet_name = st.text_input("Pet Name *", key="cl_name")
        pet_type = st.selectbox("Type", [1, 2], key="cl_type",
                                format_func=lambda x: "🐶 Dog" if x == 1 else "🐱 Cat")
        age = st.slider("Age (months)", 0, 120, 12, key="cl_age")
        gender = st.selectbox("Gender", [1, 2, 3], key="cl_gender",
                              format_func=lambda x: GENDER_MAP[x])
        quantity = st.number_input("Quantity", 1, 20, 1, key="cl_qty")

        st.subheader("Health")
        health = st.selectbox("Health", [1, 2, 3], key="cl_health",
                              format_func=lambda x: HEALTH_MAP[x])
        vaccinated = st.selectbox("Vaccinated", [1, 2, 3], key="cl_vacc",
                                  format_func=lambda x: VACCINATED_MAP[x])
        dewormed = st.selectbox("Dewormed", [1, 2, 3], key="cl_dew",
                                format_func=lambda x: DEWORMED_MAP[x])
        sterilized = st.selectbox("Sterilized", [1, 2, 3], key="cl_ster",
                                  format_func=lambda x: STERILIZED_MAP[x])

    with col2:
        st.subheader("Physical")
        maturity_size = st.selectbox("Maturity size", [0, 1, 2, 3, 4], key="cl_size",
                                     format_func=lambda x: SIZE_MAP[x])
        fur_length = st.selectbox("Fur length", [0, 1, 2, 3], key="cl_fur",
                                  format_func=lambda x: FUR_MAP[x])
        c_opts = list(COLOR_MAP.keys())[1:]
        color1 = st.selectbox("Primary color", c_opts, key="cl_col1",
                              format_func=lambda x: COLOR_MAP[x])
        color2 = st.selectbox("Secondary color", [0] + c_opts, key="cl_col2",
                              format_func=lambda x: COLOR_MAP[x])
        color3 = st.selectbox("Tertiary color", [0] + c_opts, key="cl_col3",
                              format_func=lambda x: COLOR_MAP[x])

        st.subheader("Listing")
        fee = st.number_input("Adoption fee (€)", 0, 5000, 0, step=10, key="cl_fee")
        _locs_cl = _load_locations()
        _cbc_cl = _locs_cl.get("cities_by_country", {})
        _countries_cl = _locs_cl.get("countries", [])
        cl_country = st.selectbox("Country", ["— select —"] + _countries_cl, key="cl_country")
        _cl_city_list = [c["city"] for c in _cbc_cl.get(cl_country, [])] if cl_country != "— select —" else []
        cl_city = st.selectbox("City", ["— select —"] + _cl_city_list, key="cl_city",
                               disabled=(cl_country == "— select —"))
        _cl_postal_list = []
        if cl_city and cl_city != "— select —":
            for _e in _cbc_cl.get(cl_country, []):
                if _e["city"] == cl_city:
                    _cl_postal_list = _e.get("postal_codes", [])
                    break
        cl_postal = st.selectbox("Postal code", ["— any —"] + _cl_postal_list, key="cl_postal",
                                 disabled=(cl_city == "— select —"))

        breed_opts = [(bid, bname) for bid, btype, bname in BREED_DATA if btype == pet_type]
        breed_ids = [b[0] for b in breed_opts]
        breed_names = [b[1] for b in breed_opts]
        b1_name = st.selectbox("Primary breed", breed_names, key=f"cl_breed1_{pet_type}")
        breed1 = breed_ids[breed_names.index(b1_name)] if b1_name in breed_names else breed_ids[0]
        b2_name = st.selectbox("Secondary breed", ["None"] + breed_names,
                               key=f"cl_breed2_{pet_type}")
        breed2 = (0 if b2_name == "None"
                  else (breed_ids[breed_names.index(b2_name)] if b2_name in breed_names else 0))

    if not gemini_utils.is_configured():
        with st.expander("🔑 Configure Gemini API Key"):
            api_key = st.text_input("Gemini API Key", type="password", key="cl_gem_key")
            if api_key:
                gemini_utils.set_api_key(api_key)
                st.success("Key set for this session.")

    st.markdown("---")

    # Photo section with camera fix
    _ptab_file, _ptab_cam = st.tabs(["📁 Select from device", "📷 Take photo"])
    with _ptab_file:
        uploaded_files = st.file_uploader(
            "Upload pet photos (JPG/PNG)",
            type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="cl_photos"
        )
    with _ptab_cam:
        cam_active_key = "cl_camera_active"
        if not st.session_state.get(cam_active_key):
            if st.button("📷 Start Camera", key="cl_camera_start"):
                st.session_state[cam_active_key] = True
                st.rerun()
            st.caption("Click 'Start Camera' — the browser will ask for camera permission only then.")
            _cam_photo = None
        else:
            _cam_photo = st.camera_input("Take a photo of your pet", key="cl_camera_photo")
            if st.button("Stop Camera", key="cl_camera_stop"):
                st.session_state[cam_active_key] = False
                st.rerun()
            if _cam_photo:
                st.success("📸 Photo captured — will be used as the first photo.")

    all_files = list(uploaded_files or [])
    if _cam_photo:
        all_files = [_cam_photo] + all_files

    # Studio processing (no Bokeh)
    if all_files:
        _render_studio_for_files(all_files, "cl")

    st.markdown("---")
    st.subheader("🎬 Videos")
    uploaded_videos = st.file_uploader(
        "Upload pet videos (MP4/MOV/AVI/WEBM)",
        type=["mp4", "mov", "avi", "webm"],
        accept_multiple_files=True,
        key="cl_videos",
    )
    if uploaded_videos:
        st.caption(f"{len(uploaded_videos)} video(s) ready to upload.")

    st.markdown("---")
    st.subheader("📝 Description")

    # Voice memo — transcript appends to existing text
    if gemini_utils.is_configured():
        _voice_memo = st.audio_input("🎙️ Record a voice memo (optional)", key="cl_voice_memo")
        if _voice_memo is not None:
            if st.button("📝 Transcribe memo", key="cl_transcribe_btn"):
                _raw_mime = _voice_memo.type or "audio/wav"
                # Strip codec parameters (e.g. "audio/webm;codecs=opus" → "audio/webm")
                _mime = _raw_mime.split(";")[0].strip()
                with gemini_utils.ai_loading("Transcribing your voice memo…"):
                    _t_ok, _transcript = gemini_utils.transcribe_audio(
                        _voice_memo.read(), _mime
                    )
                if _t_ok:
                    _existing = st.session_state.get("cl_desc", "")
                    _sep = "\n\n" if _existing.strip() else ""
                    st.session_state["_cl_desc_draft"] = _existing + _sep + _transcript
                    st.rerun()
                else:
                    st.warning(f"Transcription failed: {_transcript}")

    # Flush any pending draft BEFORE the textarea is instantiated
    if "_cl_desc_draft" in st.session_state:
        st.session_state["cl_desc"] = st.session_state.pop("_cl_desc_draft")

    description = st.text_area(
        "Description",
        height=140,
        placeholder="Personality, history, care needs… (or use voice memo / AI below)",
        key="cl_desc",
    )

    _gc, _cc = st.columns([3, 1])
    with _gc:
        if gemini_utils.is_configured():
            st.markdown(
                f'<div style="font-size:12px;color:{COLOR_TEXT_MUTED};margin-bottom:4px;">'
                f'✨ AI descriptions improve adoption chances by up to <strong>46%</strong></div>',
                unsafe_allow_html=True,
            )
            if st.button("✨ Finalize description with AI", key="cl_gen_desc_btn",
                         use_container_width=True):
                base = st.session_state.get("cl_desc", "").strip() or (
                    f"{TYPE_MAP.get(pet_type, 'Pet')} named {pet_name or 'this pet'}"
                )
                first_bytes = None
                if all_files:
                    try:
                        all_files[0].seek(0)
                        first_bytes = all_files[0].read()
                        all_files[0].seek(0)
                    except Exception:
                        pass
                with gemini_utils.ai_loading("Crafting an optimised adoption description…"):
                    ok, result = gemini_utils.improve_description(
                        base,
                        {"type": pet_type, "age": age, "gender": gender,
                         "health": health, "vaccinated": vaccinated,
                         "sterilized": sterilized, "fee": fee},
                        image_bytes=first_bytes,
                    )
                if ok:
                    st.session_state["_cl_desc_draft"] = result
                    st.session_state["cl_desc_is_ai"] = True
                    st.rerun()
                else:
                    st.warning(result)
        else:
            st.caption("🔑 Configure a Gemini API key below to enable AI description generation.")
    with _cc:
        if st.session_state.get("cl_desc_is_ai"):
            if st.button("✕ Clear AI", key="cl_gen_desc_clear", use_container_width=True):
                st.session_state.pop("cl_desc_is_ai", None)
                st.rerun()

    if st.session_state.get("cl_desc_is_ai"):
        st.success("✨ AI-enhanced description — edit above if needed.")

    st.markdown("---")
    if st.button("🚀 Publish Listing", type="primary", key="cl_publish"):
        if not pet_name.strip():
            st.error("Pet name is required.")
            return

        _cl_country_val = cl_country if cl_country != "— select —" else None
        _cl_city_val = cl_city if cl_city != "— select —" else None
        _cl_postal_val = cl_postal if cl_postal != "— any —" else None

        pet_df = pd.DataFrame([{
            "Type": pet_type, "Name": pet_name, "Age": age,
            "Breed1": breed1, "Breed2": breed2, "Gender": gender,
            "Color1": color1, "Color2": color2, "Color3": color3,
            "MaturitySize": maturity_size, "FurLength": fur_length,
            "Vaccinated": vaccinated, "Dewormed": dewormed, "Sterilized": sterilized,
            "Health": health, "Quantity": quantity, "Fee": fee, "State": 41326,
            "PhotoAmt": len(all_files), "VideoAmt": len(uploaded_videos or []),
            "Description": description,
        }])

        speed = conf = None
        with st.spinner("Predicting adoption speed…"):
            pred = make_prediction(pet_df)
        if pred.get("success"):
            p0 = pred["predictions"][0]
            speed, conf = p0["prediction"], p0["confidence"]

        description = st.session_state.get("cl_desc", "")
        improved_desc = description if st.session_state.get("cl_desc_is_ai") else None

        lid = db.create_listing(
            shelter_id=user["id"], pet_name=pet_name.strip(), pet_type=pet_type,
            age=age, breed1=breed1, breed2=breed2, gender=gender,
            color1=color1, color2=color2, color3=color3,
            maturity_size=maturity_size, fur_length=fur_length,
            vaccinated=vaccinated, dewormed=dewormed, sterilized=sterilized,
            health=health, quantity=quantity, fee=fee,
            country=_cl_country_val, city=_cl_city_val, postal_code=_cl_postal_val,
            video_amt=len(uploaded_videos or []), description=description,
            description_improved=improved_desc,
            adoption_speed_pred=speed, adoption_speed_confidence=conf,
        )

        for i, uf in enumerate(all_files):
            choice = st.session_state.get(f"cl_studio_use_{i}", "original")
            studio_b = st.session_state.get(f"cl_studio_{i}")

            if choice == "studio" and studio_b:
                dest_dir = UPLOAD_DIR / str(lid)
                dest_dir.mkdir(parents=True, exist_ok=True)
                stem = uf.name.rsplit(".", 1)[0]
                dest = dest_dir / f"{uuid.uuid4().hex}_{stem}_studio.png"
                dest.write_bytes(studio_b)
                db.add_photo(lid, str(dest))
            else:
                try:
                    uf.seek(0)
                    raw = uf.read()
                    if not raw:
                        st.error(f"Could not save {uf.name} — upload buffer empty.")
                        continue
                    dest = _save_upload_bytes(uf.name, raw, lid)
                    db.add_photo(lid, dest)
                except Exception as exc:
                    st.error(f"Failed to save {uf.name}: {exc}")
                    continue

        for vf in (uploaded_videos or []):
            try:
                vf.seek(0)
                vdata = vf.read()
                if vdata:
                    vdest_dir = UPLOAD_DIR / str(lid)
                    vdest_dir.mkdir(parents=True, exist_ok=True)
                    vdest = vdest_dir / f"{uuid.uuid4().hex}_{vf.name}"
                    vdest.write_bytes(vdata)
                    db.add_video(lid, str(vdest))
            except Exception:
                pass

        st.session_state["_cl_published_id"] = lid
        st.session_state["_cl_just_published"] = True
        st.rerun()


# ── Edit Listing — full form matching Create ───────────────────────────────────

def render_edit_listing(listing_id: int, user: dict):
    listing = db.get_listing(listing_id)
    if not listing or listing.get("shelter_id") != user["id"]:
        st.error("Not found or access denied.")
        return

    header_html = (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        f'<h1 style="font-size:28px;font-weight:600;color:{COLOR_PRIMARY};margin:0;">✏️ Edit — {listing["pet_name"]}</h1>'
        f'<span style="background:linear-gradient(135deg,{COLOR_PRIMARY} 0%,{COLOR_PRIMARY_LIGHT} 100%);'
        f'color:#FFFFFF;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:500;">✨ AI ASSISTED</span>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
    if st.button("← Back", key="el_back"):
        _nav("detail", mp_listing_id=listing_id)

    pet_type = int(listing.get("type", 1))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Basic Info")
        pet_name = st.text_input("Pet Name *", value=listing["pet_name"], key="el_name")
        pet_type_sel = st.selectbox("Type", [1, 2], key="el_type",
                                    index=pet_type - 1,
                                    format_func=lambda x: "🐶 Dog" if x == 1 else "🐱 Cat")
        age = st.slider("Age (months)", 0, 120, int(listing.get("age") or 0), key="el_age")
        gender = st.selectbox("Gender", [1, 2, 3], key="el_gender",
                              index=max(0, int(listing.get("gender") or 1) - 1),
                              format_func=lambda x: GENDER_MAP[x])
        quantity = st.number_input("Quantity", 1, 20, int(listing.get("quantity") or 1), key="el_qty")

        st.subheader("Health")
        health = st.selectbox("Health", [1, 2, 3], key="el_health",
                              index=max(0, int(listing.get("health") or 1) - 1),
                              format_func=lambda x: HEALTH_MAP[x])
        vaccinated = st.selectbox("Vaccinated", [1, 2, 3], key="el_vacc",
                                  index=max(0, int(listing.get("vaccinated") or 3) - 1),
                                  format_func=lambda x: VACCINATED_MAP[x])
        dewormed = st.selectbox("Dewormed", [1, 2, 3], key="el_dew",
                                index=max(0, int(listing.get("dewormed") or 3) - 1),
                                format_func=lambda x: DEWORMED_MAP[x])
        sterilized = st.selectbox("Sterilized", [1, 2, 3], key="el_ster",
                                  index=max(0, int(listing.get("sterilized") or 3) - 1),
                                  format_func=lambda x: STERILIZED_MAP[x])

    with col2:
        st.subheader("Physical")
        maturity_size = st.selectbox("Maturity size", [0, 1, 2, 3, 4], key="el_size",
                                     index=int(listing.get("maturity_size") or 0),
                                     format_func=lambda x: SIZE_MAP[x])
        fur_length = st.selectbox("Fur length", [0, 1, 2, 3], key="el_fur",
                                  index=int(listing.get("fur_length") or 0),
                                  format_func=lambda x: FUR_MAP[x])
        c_opts = list(COLOR_MAP.keys())[1:]

        def _color_idx(val, opts):
            return opts.index(val) if val in opts else 0

        color1 = st.selectbox("Primary color", c_opts, key="el_col1",
                              index=_color_idx(int(listing.get("color1") or 1), c_opts),
                              format_func=lambda x: COLOR_MAP[x])
        color2 = st.selectbox("Secondary color", [0] + c_opts, key="el_col2",
                              index=_color_idx(int(listing.get("color2") or 0), [0] + c_opts),
                              format_func=lambda x: COLOR_MAP[x])
        color3 = st.selectbox("Tertiary color", [0] + c_opts, key="el_col3",
                              index=_color_idx(int(listing.get("color3") or 0), [0] + c_opts),
                              format_func=lambda x: COLOR_MAP[x])

        st.subheader("Listing")
        fee = st.number_input("Adoption fee (€)", 0, 5000, int(listing.get("fee") or 0),
                              step=10, key="el_fee")
        _locs_el = _load_locations()
        _cbc_el = _locs_el.get("cities_by_country", {})
        _countries_el = _locs_el.get("countries", [])
        _el_country_default = listing.get("country") or "— select —"
        _el_country_opts = ["— select —"] + _countries_el
        _el_country_idx = _el_country_opts.index(_el_country_default) if _el_country_default in _el_country_opts else 0
        el_country = st.selectbox("Country", _el_country_opts, key="el_country", index=_el_country_idx)
        _el_city_list = [c["city"] for c in _cbc_el.get(el_country, [])] if el_country != "— select —" else []
        _el_city_default = listing.get("city") or "— select —"
        _el_city_opts = ["— select —"] + _el_city_list
        _el_city_idx = _el_city_opts.index(_el_city_default) if _el_city_default in _el_city_opts else 0
        el_city = st.selectbox("City", _el_city_opts, key="el_city", index=_el_city_idx,
                               disabled=(el_country == "— select —"))
        _el_postal_list = []
        if el_city and el_city != "— select —":
            for _e in _cbc_el.get(el_country, []):
                if _e["city"] == el_city:
                    _el_postal_list = _e.get("postal_codes", [])
                    break
        _el_postal_default = listing.get("postal_code") or "— any —"
        _el_postal_opts = ["— any —"] + _el_postal_list
        _el_postal_idx = _el_postal_opts.index(_el_postal_default) if _el_postal_default in _el_postal_opts else 0
        el_postal = st.selectbox("Postal code", _el_postal_opts, key="el_postal",
                                 index=_el_postal_idx, disabled=(el_city == "— select —"))

        breed_opts = [(bid, bname) for bid, btype, bname in BREED_DATA if btype == pet_type_sel]
        breed_ids = [b[0] for b in breed_opts]
        breed_names = [b[1] for b in breed_opts]
        cur_b1 = int(listing.get("breed1") or breed_ids[0])
        b1_idx = breed_ids.index(cur_b1) if cur_b1 in breed_ids else 0
        b1_name = st.selectbox("Primary breed", breed_names, key=f"el_breed1_{pet_type_sel}",
                               index=b1_idx)
        breed1 = breed_ids[breed_names.index(b1_name)] if b1_name in breed_names else breed_ids[0]
        cur_b2 = int(listing.get("breed2") or 0)
        b2_opts = ["None"] + breed_names
        b2_val = breed_names[breed_ids.index(cur_b2)] if cur_b2 in breed_ids else "None"
        b2_name = st.selectbox("Secondary breed", b2_opts,
                               key=f"el_breed2_{pet_type_sel}",
                               index=b2_opts.index(b2_val))
        breed2 = (0 if b2_name == "None"
                  else (breed_ids[breed_names.index(b2_name)] if b2_name in breed_names else 0))

    if not gemini_utils.is_configured():
        with st.expander("🔑 Configure Gemini API Key"):
            ak = st.text_input("Gemini API Key", type="password", key="el_gem_key")
            if ak:
                gemini_utils.set_api_key(ak)
                st.success("Key set.")

    st.markdown("---")
    st.subheader("📸 Existing Photos + Studio")
    photos = db.get_photos(listing_id)

    if photos:
        for p in photos:
            img_b = _img_bytes(p["photo_path"])
            if not img_b:
                continue
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                st.image(img_b, width=120)
            with pc2:
                if p.get("is_studio_ready"):
                    st.success("✅ Studio-ready")
                    s_b = _img_bytes(p.get("studio_photo_path") or "")
                    if s_b:
                        st.download_button(
                            "⬇️ Download Studio photo", data=s_b,
                            file_name=Path(p["studio_photo_path"]).name,
                            mime="image/png", key=f"dl_ed_s_{p['id']}"
                        )
                else:
                    ed_pending_key = f"ed_studio_pending_{p['id']}"
                    ed_choice_key = f"ed_studio_use_{p['id']}"
                    ed_pending = st.session_state.get(ed_pending_key)
                    if ed_pending:
                        eb1, eb2 = st.columns(2)
                        with eb1:
                            st.caption("📷 Original")
                            st.image(img_b, width='stretch')
                        with eb2:
                            st.caption("✨ Studio")
                            st.image(ed_pending, width='stretch')
                        st.radio("Keep which?", ["studio", "original"],
                                 format_func=lambda x: "✨ Studio" if x == "studio" else "📷 Original",
                                 key=ed_choice_key, horizontal=True, index=0)
                        if st.button("✅ Confirm", key=f"ed_confirm_{p['id']}"):
                            if st.session_state.get(ed_choice_key, "studio") == "studio":
                                sp = STUDIO_DIR / str(listing_id) / f"studio_{p['id']}.png"
                                sp.parent.mkdir(parents=True, exist_ok=True)
                                sp.write_bytes(ed_pending)
                                ok_stk, sticker_bytes = gemini_utils.make_sticker(img_b)
                                if ok_stk and sticker_bytes:
                                    stk_p = STUDIO_DIR / str(listing_id) / f"sticker_{p['id']}.png"
                                    stk_p.write_bytes(sticker_bytes)
                                db.update_photo_studio(p["id"], str(sp))
                            st.session_state.pop(ed_pending_key, None)
                            st.session_state.pop(ed_choice_key, None)
                            st.rerun()
                    else:
                        if st.button("✨ Make Studio Ready", key=f"ed_studio_{p['id']}"):
                            with gemini_utils.ai_loading("Creating studio photo…"):
                                ok_ed, result = gemini_utils.make_studio_ready_bytes(img_b)
                            if ok_ed:
                                st.session_state[ed_pending_key] = result
                                st.rerun()
                            else:
                                st.error(result)
    else:
        st.caption("No photos uploaded yet.")

    st.subheader("📸 Add more photos")
    new_photos = st.file_uploader("Upload additional photos", type=["jpg", "jpeg", "png"],
                                  accept_multiple_files=True, key="el_photos")

    st.subheader("🎬 Videos")
    existing_videos = db.get_videos(listing_id)
    if existing_videos:
        st.caption(f"{len(existing_videos)} video(s) already uploaded.")
    new_videos = st.file_uploader(
        "Upload additional videos (MP4/MOV/AVI/WEBM)",
        type=["mp4", "mov", "avi", "webm"],
        accept_multiple_files=True,
        key="el_videos",
    )
    if new_videos:
        st.caption(f"{len(new_videos)} new video(s) to add.")

    st.markdown("---")
    st.subheader("📝 Description")
    # Pre-populate on first visit to this listing's edit page
    _el_desc_init_key = f"el_desc_init_{listing_id}"
    if _el_desc_init_key not in st.session_state:
        st.session_state["el_desc"] = (listing.get("description_improved")
                                       or listing.get("description") or "")
        st.session_state[_el_desc_init_key] = True

    # Voice memo — transcript appends to existing text
    if gemini_utils.is_configured():
        _voice_memo_el = st.audio_input("🎙️ Record a voice memo (optional)", key="el_voice_memo")
        if _voice_memo_el is not None:
            if st.button("📝 Transcribe memo", key="el_transcribe_btn"):
                _raw_mime_el = _voice_memo_el.type or "audio/wav"
                _mime_el = _raw_mime_el.split(";")[0].strip()
                with gemini_utils.ai_loading("Transcribing your voice memo…"):
                    _t_ok, _transcript = gemini_utils.transcribe_audio(
                        _voice_memo_el.read(), _mime_el
                    )
                if _t_ok:
                    _existing_el = st.session_state.get("el_desc", "")
                    _sep_el = "\n\n" if _existing_el.strip() else ""
                    st.session_state["_el_desc_draft"] = _existing_el + _sep_el + _transcript
                    st.rerun()
                else:
                    st.warning(f"Transcription failed: {_transcript}")

    # Flush any pending draft BEFORE the textarea is instantiated
    if "_el_desc_draft" in st.session_state:
        st.session_state["el_desc"] = st.session_state.pop("_el_desc_draft")

    description = st.text_area(
        "Description",
        height=140, key="el_desc",
        placeholder="Personality, history, care needs… (or use voice memo / AI below)",
    )

    _gc_el, _cc_el = st.columns([3, 1])
    with _gc_el:
        if gemini_utils.is_configured():
            st.markdown(
                f'<div style="font-size:12px;color:{COLOR_TEXT_MUTED};margin-bottom:4px;">'
                f'✨ AI descriptions improve adoption chances by up to <strong>46%</strong></div>',
                unsafe_allow_html=True,
            )
            if st.button("✨ Finalize description with AI", key="el_regen",
                         use_container_width=True):
                first_img = _img_bytes(photos[0]["photo_path"]) if photos else None
                with gemini_utils.ai_loading("Crafting an optimised description…"):
                    ok, res = gemini_utils.improve_description(
                        st.session_state.get("el_desc", "").strip() or listing["pet_name"],
                        {"type": listing["type"], "age": age, "gender": gender,
                         "health": health, "vaccinated": vaccinated,
                         "sterilized": sterilized, "fee": fee},
                        image_bytes=first_img,
                    )
                if ok:
                    st.session_state["_el_desc_draft"] = res
                    st.session_state["el_desc_is_ai"] = True
                    st.rerun()
                else:
                    st.warning(res)

    with _cc_el:
        if st.session_state.get("el_desc_is_ai"):
            if st.button("✕ Clear AI", key="el_desc_clear_ai", use_container_width=True):
                st.session_state.pop("el_desc_is_ai", None)
                st.rerun()

    if st.session_state.get("el_desc_is_ai"):
        st.success("✨ AI-enhanced description — edit above if needed.")

    st.markdown("---")
    if st.button("💾 Save Changes", type="primary", key="el_save"):
        _el_country_val = el_country if el_country != "— select —" else None
        _el_city_val = el_city if el_city != "— select —" else None
        _el_postal_val = el_postal if el_postal != "— any —" else None
        description = st.session_state.get("el_desc", "")
        updates = {
            "pet_name": pet_name.strip(),
            "type": pet_type_sel,
            "age": age, "fee": fee,
            "gender": gender, "quantity": quantity,
            "health": health, "vaccinated": vaccinated,
            "sterilized": sterilized, "dewormed": dewormed,
            "maturity_size": maturity_size, "fur_length": fur_length,
            "color1": color1, "color2": color2, "color3": color3,
            "breed1": breed1, "breed2": breed2,
            "country": _el_country_val, "city": _el_city_val, "postal_code": _el_postal_val,
            "description": description,
        }
        if st.session_state.get("el_desc_is_ai"):
            updates["description_improved"] = description
        db.update_listing(listing_id, **updates)
        for uf in (new_photos or []):
            dest = _save_upload(uf, listing_id)
            db.add_photo(listing_id, dest)
        for vf in (new_videos or []):
            try:
                vf.seek(0)
                vdata = vf.read()
                if vdata:
                    vdest_dir = UPLOAD_DIR / str(listing_id)
                    vdest_dir.mkdir(parents=True, exist_ok=True)
                    vdest = vdest_dir / f"{uuid.uuid4().hex}_{vf.name}"
                    vdest.write_bytes(vdata)
                    db.add_video(listing_id, str(vdest))
            except Exception:
                pass
        total_videos = len(db.get_videos(listing_id))
        db.update_listing(listing_id, video_amt=total_videos)
        st.success("Saved!")
        _nav("detail", mp_listing_id=listing_id)


# ── KPI Dashboard — comprehensive ─────────────────────────────────────────────

def render_kpis(user: dict):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>📊 Performance Dashboard</h1>",
                unsafe_allow_html=True)
    kpis = db.get_shelter_kpis(user["id"])
    avg_sat = db.get_shelter_avg_satisfaction(user["id"])

    # ── Tier-1 KPI row ────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total listings", kpis["total"],
               help="All listings ever created by this shelter")
    k2.metric("Active", kpis["active"],
               help="Currently available listings")
    k3.metric("Adopted", kpis["adopted"],
               help="Listings marked as adopted")
    k4.metric("Adoption rate", f"{kpis['adoption_rate']:.1f}%",
               help="adopted / total × 100")

    k5, k6, k7, k8 = st.columns(4)
    avg_los = kpis["avg_los_days"]
    avg_spd = kpis["avg_adoption_speed"]
    k5.metric("Avg LOS (days)", f"{avg_los:.0f}" if avg_los else "—",
               help="Average Length of Stay: days from listing to adoption")
    k6.metric("Long-stay rate", f"{kpis['long_stay_rate']:.1f}%",
               help="% of active listings predicted Speed 4 (>100 days unadopted). Target: <10%")
    k7.metric("Inquiries / active listing", f"{kpis['inquiries_per_active']:.1f}",
               help="Total contacts ÷ active listing count")
    k8.metric("Avg adoption speed", f"{avg_spd:.1f}" if avg_spd else "—",
               help="Average actual adoption speed class (0=same day, 4=no adoption)")

    k9, k10, k11, k12 = st.columns(4)
    k9.metric("Total views", kpis["total_views"],
               help="Cumulative page views across all listings")
    k10.metric("Total contacts", kpis["total_contacts"],
                help="Messages sent to this shelter")
    k11.metric("Avg adoption fee (€)", f"€{kpis['avg_fee']:.0f}",
                help="Average fee across all listings")
    satisfaction_label = f"{avg_sat:.1f} / 5" if avg_sat else "No data yet"
    k12.metric("Post-adoption satisfaction", satisfaction_label,
                help="Post-Adoption Satisfaction Score (1–5 Likert scale, from adopter surveys)")

    k13, k14, k15, k16 = st.columns(4)
    k13.metric("Photo coverage", f"{kpis['photo_coverage_rate']:.1f}%",
                help="% of listings with at least 1 photo. Target: 100%")
    k14.metric("Avg photos / listing", f"{kpis['avg_photo_count']:.1f}",
                help="Average number of photos per listing")
    k15.metric("Description quality", f"{kpis['desc_quality_rate']:.1f}%",
                help="% of listings with a description longer than 10 words")
    k16.metric("Dogs | Cats", f"{kpis['dog_count']} | {kpis['cat_count']}",
                help="Number of dog vs. cat listings")

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    t_time, t_speed, t_species, t_health, t_welfare, t_all = st.tabs([
        "📈 Over Time", "🎯 Speed Dist.", "🐾 Species", "💊 Health & Care", "🏥 Welfare KPIs", "📋 All Listings"
    ])

    ls = kpis["listings"]

    with t_time:
        if ls:
            df = pd.DataFrame(ls)
            df["month"] = pd.to_datetime(df["created_at"]).dt.to_period("M").astype(str)
            grp = df.groupby("month").agg(
                total=("id", "count"),
                adopted=("status", lambda x: (x == "adopted").sum()),
            ).reset_index()
            fig = go.Figure()
            fig.add_bar(x=grp["month"], y=grp["total"], name="Total", marker_color=COLOR_PRIMARY)
            fig.add_bar(x=grp["month"], y=grp["adopted"], name="Adopted", marker_color="#4CAF50")
            fig.update_layout(
                title="Listings created & adopted per month",
                barmode="overlay", height=320,
                xaxis_title="Month", yaxis_title="Count",
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Views over time
            if any(r.get("views") for r in ls):
                df_kpi = pd.DataFrame([{
                    "month": pd.to_datetime(r["created_at"]).strftime("%Y-%m"),
                    "views": r.get("views") or 0,
                    "contacts": r.get("contacts") or 0,
                } for r in ls])
                grp2 = df_kpi.groupby("month")[["views", "contacts"]].sum().reset_index()
                fig2 = go.Figure()
                fig2.add_scatter(x=grp2["month"], y=grp2["views"], name="Views",
                                  mode="lines+markers", line_color=COLOR_PRIMARY)
                fig2.add_scatter(x=grp2["month"], y=grp2["contacts"], name="Contacts",
                                  mode="lines+markers", line_color="#FF9800")
                fig2.update_layout(title="Views & Contacts over time", height=280)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data yet.")

    with t_speed:
        speed_dist = kpis["speed_dist"]
        if speed_dist:
            labels = [f"Speed {k}: {ADOPTION_SPEED_LABELS[k]}" for k in sorted(speed_dist)]
            values = [speed_dist[k] for k in sorted(speed_dist)]
            colors = [ADOPTION_SPEED_COLORS.get(k, "#999") for k in sorted(speed_dist)]
            fig = go.Figure(go.Pie(
                labels=labels, values=values, marker_colors=colors,
                hole=0.4,
            ))
            fig.update_layout(title="Predicted adoption speed distribution", height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No speed predictions yet.")

    with t_species:
        if kpis["dog_ages"] or kpis["cat_ages"]:
            col_d, col_c = st.columns(2)
            with col_d:
                if kpis["dog_ages"]:
                    fig_d = px.histogram(
                        x=kpis["dog_ages"], nbins=12,
                        title=f"Dog age distribution (n={len(kpis['dog_ages'])})",
                        labels={"x": "Age (months)"},
                        color_discrete_sequence=[COLOR_PRIMARY],
                    )
                    fig_d.update_layout(height=280)
                    st.plotly_chart(fig_d, use_container_width=True)
                else:
                    st.info("No dog listings.")
            with col_c:
                if kpis["cat_ages"]:
                    fig_c = px.histogram(
                        x=kpis["cat_ages"], nbins=12,
                        title=f"Cat age distribution (n={len(kpis['cat_ages'])})",
                        labels={"x": "Age (months)"},
                        color_discrete_sequence=["#FF9800"],
                    )
                    fig_c.update_layout(height=280)
                    st.plotly_chart(fig_c, use_container_width=True)
                else:
                    st.info("No cat listings.")
        else:
            st.info("No species data yet.")

    with t_health:
        c_h, c_care = st.columns(2)
        with c_h:
            health_dist = kpis["health_dist"]
            if health_dist:
                hlabels = [HEALTH_MAP.get(k, str(k)) for k in sorted(health_dist)]
                hvals = [health_dist[k] for k in sorted(health_dist)]
                fig_h = go.Figure(go.Bar(x=hlabels, y=hvals, marker_color=COLOR_PRIMARY))
                fig_h.update_layout(title="Health distribution", height=280, yaxis_title="Count")
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("No health data.")
        with c_care:
            care_labels = ["Vaccinated", "Sterilized", "Dewormed"]
            care_vals = [kpis["vacc_rate"], kpis["ster_rate"], kpis["dew_rate"]]
            fig_care = go.Figure(go.Bar(
                x=care_labels, y=care_vals,
                marker_color=["#4CAF50", "#2196F3", "#FF9800"],
                text=[f"{v:.1f}%" for v in care_vals], textposition="outside",
            ))
            fig_care.update_layout(
                title="Care coverage % (active listings)",
                height=280, yaxis_range=[0, 110], yaxis_title="%",
            )
            st.plotly_chart(fig_care, use_container_width=True)

    with t_welfare:
        st.markdown("**Welfare KPIs** — track the health of your shelter programme")
        w1, w2, w3 = st.columns(3)
        w1.metric("Long-stay / unadopted >100d rate", f"{kpis['long_stay_rate']:.1f}%",
                   help="% active listings predicted speed 4 (no adoption). Welfare threshold: <10%")
        w2.metric("Photo coverage", f"{kpis['photo_coverage_rate']:.1f}%",
                   help="Listings with at least 1 photo. Target: 100%")
        w3.metric("Description quality", f"{kpis['desc_quality_rate']:.1f}%",
                   help="Listings with >10 words in description. Target: 100%")

        st.markdown("---")
        st.markdown("**12-Month Reinsertion Rate**")
        st.info(
            "Reinsertion rate = animals returned/reinserted within 12 months ÷ completed adoptions × 100. "
            "Target: <5% (welfare-critical). Data collection pending — requires a return/reinsertion tracking workflow. "
            "Enable by marking a listing as 'reinserted' when a returned animal is re-listed.",
            icon="📋",
        )

        st.markdown("---")
        st.markdown("**Post-Adoption Satisfaction Surveys**")
        if avg_sat:
            stars = "⭐" * round(avg_sat)
            st.metric("Average Satisfaction", f"{avg_sat:.2f} / 5.0", help="1–5 Likert scale from adopter surveys")
            st.markdown(stars)
        else:
            st.info("No surveys received yet. Adopt more pets and encourage adopters to rate their experience!", icon="📊")

    with t_all:
        if ls:
            rows = []
            for l in ls:
                spd = l.get("adoption_speed_pred")
                rows.append({
                    "ID": l["id"],
                    "Name": l["pet_name"],
                    "Type": TYPE_MAP.get(l.get("type", 1), "?"),
                    "Status": l["status"].title(),
                    "Speed": (f"{ADOPTION_SPEED_EMOJI.get(spd, '')} {ADOPTION_SPEED_LABELS.get(spd, '—')}"
                              if spd is not None else "—"),
                    "Views": l.get("views") or 0,
                    "Contacts": l.get("contacts") or 0,
                    "LOS (days)": l.get("adoption_time_days") or "—",
                    "Fee (€)": l.get("fee") or 0,
                    "Photos": l.get("photo_amt") or 0,
                    "Created": l["created_at"][:10],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No listings yet.")


# ── Watchlist ──────────────────────────────────────────────────────────────────

def render_watchlist(user: dict):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>❤️ My Watchlist</h1>",
                unsafe_allow_html=True)
    listings = db.get_watchlist(user["id"])
    if not listings:
        st.info("Your watchlist is empty. Browse pets and click ❤️ to save them!")
        return

    for listing in listings:
        with st.container(border=True):
            wc1, wc2, wc3, wc4 = st.columns([3, 1, 1, 1])
            with wc1:
                st.markdown(f"**{listing['pet_name']}**")
                sh = listing.get("shelter_name") or listing.get("shelter_username", "")
                st.caption(f"🏥 {sh} · Saved {listing['saved_at'][:10]}")
            with wc2:
                if st.button("📋 Details", key=f"wld_{listing['id']}",
                             use_container_width=True):
                    _nav("detail", mp_listing_id=listing["id"])
            with wc3:
                s_uid = listing.get("shelter_id")
                if st.button("💬 Message", key=f"wlm_{listing['id']}",
                             use_container_width=True):
                    _nav("chat", mp_chat_with=s_uid)
            with wc4:
                if st.button("🗑️ Remove", key=f"wlr_{listing['id']}",
                             use_container_width=True):
                    db.remove_from_watchlist(user["id"], listing["id"])
                    st.rerun()


# ── Chat ───────────────────────────────────────────────────────────────────────

def render_chat(user: dict):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>💬 Messages</h1>",
                unsafe_allow_html=True)
    conversations = db.get_user_conversations(user["id"])
    other_id = st.session_state.get("mp_chat_with")

    cl, cr = st.columns([1, 2])

    with cl:
        st.markdown("**Conversations**")
        if not conversations:
            st.caption("No conversations yet.")
        for conv in conversations:
            label = conv.get("shelter_name") or conv.get("other_username", "?")
            unread = conv.get("unread_count", 0)
            btn_lbl = f"{'🔴 ' if unread else ''}{label}"
            if st.button(btn_lbl, key=f"conv_{conv['other_id']}",
                         use_container_width=True):
                st.session_state.mp_chat_with = conv["other_id"]
                st.rerun()

    with cr:
        if not other_id:
            st.info("Select a conversation to start chatting.")
            return

        other = db.get_user_by_id(other_id)
        other_name = (other.get("shelter_name") or other["username"]) if other else "Unknown"
        st.markdown(f"**{other_name}**")

        messages = db.get_conversation(user["id"], other_id)
        db.mark_messages_read(user["id"], other_id)

        with st.container(height=350):
            if not messages:
                st.caption("No messages yet. Say hello!")
            for msg in messages:
                is_me = msg["sender_id"] == user["id"]
                align = "right" if is_me else "left"
                bg = COLOR_PRIMARY if is_me else "#f0f0f0"
                fg = "white" if is_me else "#222"
                name = "You" if is_me else msg.get("sender_name", other_name)
                ts = msg["created_at"][11:16]
                st.markdown(
                    f"<div style='text-align:{align};margin:4px 0;'>"
                    f"<span style='font-size:0.75em;color:#888;'>{name} · {ts}</span><br>"
                    f"<span style='background:{bg};color:{fg};padding:6px 12px;"
                    f"border-radius:12px;display:inline-block;max-width:80%;text-align:left;'>"
                    f"{msg['content']}</span></div>",
                    unsafe_allow_html=True,
                )

        send_n_key = f"chat_send_n_{other_id}"
        send_count = st.session_state.get(send_n_key, 0)
        chat_key = f"chat_input_{other_id}_{send_count}"
        ic, bc = st.columns([5, 1])
        with ic:
            st.text_input("Message", key=chat_key, label_visibility="collapsed",
                          placeholder="Type a message…")
        with bc:
            if st.button("Send ▶", key=f"chat_send_{other_id}"):
                content = st.session_state.get(chat_key, "").strip()
                if content:
                    db.send_message(user["id"], other_id, content)
                    _track_action(user)
                    st.session_state[send_n_key] = send_count + 1
                    st.rerun()


# ── Profile ────────────────────────────────────────────────────────────────────

def render_profile(user: dict):
    fresh = db.get_user_by_id(user["id"]) or user
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>👤 My Profile</h1>",
                unsafe_allow_html=True)
    _back_view = st.session_state.get("mp_view_before_profile", "browse")
    if st.button("← Back", key="profile_back"):
        _nav(_back_view)

    is_admin_user = fresh.get("role") == "admin"
    is_manager = fresh.get("role") == "shelter_manager"

    # Admin: simplified profile with password change only
    if is_admin_user:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:16px;padding:16px;'
            f'background:#F0F2FA;border:1px solid {COLOR_BORDER};border-radius:12px;'
            f'margin-bottom:20px;">'
            f'<div style="width:56px;height:56px;background:{COLOR_PRIMARY};color:#FFF;'
            f'border-radius:50%;display:flex;align-items:center;justify-content:center;'
            f'font-size:22px;font-weight:700;">A</div>'
            f'<div>'
            f'<div style="font-size:20px;font-weight:600;color:{COLOR_PRIMARY};">Admin</div>'
            f'<div style="font-size:12px;color:{COLOR_TEXT_MUTED};">'
            f'🛡️ Platform Administrator · {fresh["email"]}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("**Change password**")
        with st.form("admin_profile_pw_form"):
            cur_pw = st.text_input("Current password", type="password", key="adm_profile_cur_pw")
            new_pw = st.text_input("New password (min 6 chars)", type="password", key="adm_profile_new_pw")
            new_pw2 = st.text_input("Confirm new password", type="password", key="adm_profile_new_pw2")
            submitted_pw = st.form_submit_button("Change password", type="primary")
        if submitted_pw:
            if new_pw != new_pw2:
                st.error("Passwords do not match.")
            else:
                from frontend.utils.auth import change_password as _change_password
                ok, msg = _change_password(fresh["id"], cur_pw, new_pw)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
        return

    logo_b64 = __import__("frontend.styles", fromlist=["logo_png_b64"]).logo_png_b64()
    logo_html = (f'<img src="data:image/png;base64,{logo_b64}" width="64" '
                 f'style="object-fit:contain;" alt="AdoptSense"/>' if logo_b64 else "")
    initial = (fresh.get("shelter_name") or fresh["username"])[:1].upper()

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:20px;padding:20px;'
        f'background:#F8F9FB;border:1px solid {COLOR_BORDER};border-radius:14px;margin-bottom:24px;">'
        f'<div style="width:72px;height:72px;background:{COLOR_PRIMARY};color:#FFF;'
        f'border-radius:50%;display:flex;align-items:center;justify-content:center;'
        f'font-size:28px;font-weight:600;flex-shrink:0;">{initial}</div>'
        f'<div>'
        f'<div style="font-size:22px;font-weight:600;color:{COLOR_PRIMARY};">'
        f'{fresh.get("shelter_name") or fresh["username"]}</div>'
        f'<div style="font-size:13px;color:{COLOR_TEXT_MUTED};">@{fresh["username"]} · '
        f'{"🏥 Shelter Manager" if is_manager else "🏠 Adopter"}</div>'
        f'<div style="font-size:12px;color:{COLOR_TEXT_MUTED};">Member since {fresh["created_at"][:10]}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tab_view, tab_edit = st.tabs(["📋 Profile", "✏️ Edit Profile"])

    with tab_view:
        # Missing field indicators for shelter managers
        if is_manager:
            missing = []
            if not fresh.get("phone"):
                missing.append("phone number")
            if not fresh.get("country") or not fresh.get("city"):
                missing.append("shelter location (country/city)")
            if not fresh.get("shelter_address"):
                missing.append("shelter address")
            if missing:
                st.warning(f"⚠️ Missing info: **{', '.join(missing)}** — update in the Edit tab to appear on the Shelter Map.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Contact**")
            st.markdown(f"- Email: {fresh.get('email', '—')}")
            _phone_disp = fresh.get("phone") or "—"
            st.markdown(f"- Phone: {'⚠️ ' if not fresh.get('phone') and is_manager else ''}{_phone_disp}")
            st.markdown(f"- Website: {fresh.get('website') or '—'}")
            _loc_parts = [p for p in [fresh.get("city"), fresh.get("country")] if p]
            st.markdown(f"- Location: {', '.join(_loc_parts) if _loc_parts else (fresh.get('location') or '—')}")
        with c2:
            st.markdown("**About**")
            st.markdown(fresh.get("bio") or "*No bio set yet.*")
            if is_manager:
                st.markdown("**Shelter**")
                st.markdown(f"- Shelter name: {fresh.get('shelter_name') or '—'}")
                _addr_disp = fresh.get("shelter_address") or "—"
                st.markdown(f"- Address: {'⚠️ ' if not fresh.get('shelter_address') else ''}{_addr_disp}")
                if fresh.get("postal_code"):
                    st.markdown(f"- Postal code: {fresh['postal_code']}")
                st.markdown(f"- Description: {fresh.get('shelter_description') or '—'}")

    with tab_edit:
        _pe_locs = _load_locations()
        _pe_cbc = _pe_locs.get("cities_by_country", {})
        _pe_countries = _pe_locs.get("countries", [])

        with st.form("profile_edit_form"):
            st.subheader("Personal Info")
            new_email = st.text_input("Email", value=fresh.get("email", ""), key="pe_email")
            new_phone = st.text_input(
                "Phone" + (" *" if is_manager else ""),
                value=fresh.get("phone") or "", key="pe_phone",
                placeholder="+351 912 345 678",
            )
            new_website = st.text_input("Website", value=fresh.get("website") or "",
                                         key="pe_website", placeholder="https://yourwebsite.com")
            new_bio = st.text_area("Bio", value=fresh.get("bio") or "", height=80, key="pe_bio",
                                    placeholder="Tell adopters about yourself…")

            if is_manager:
                st.subheader("Shelter Location *")
                _pe_country_default = fresh.get("country") or "— select —"
                _pe_country_opts = ["— select —"] + _pe_countries
                _pe_country_idx = _pe_country_opts.index(_pe_country_default) if _pe_country_default in _pe_country_opts else 0
                pe_country = st.selectbox("Country *", _pe_country_opts,
                                          index=_pe_country_idx, key="pe_country")
                _pe_city_list = [c["city"] for c in _pe_cbc.get(pe_country, [])] if pe_country != "— select —" else []
                _pe_city_default = fresh.get("city") or "— select —"
                _pe_city_opts = ["— select —"] + _pe_city_list
                _pe_city_idx = _pe_city_opts.index(_pe_city_default) if _pe_city_default in _pe_city_opts else 0
                pe_city = st.selectbox("City *", _pe_city_opts,
                                       index=_pe_city_idx, key="pe_city",
                                       disabled=(pe_country == "— select —"))
                _pe_postal_list = []
                if pe_city and pe_city != "— select —":
                    for _e in _pe_cbc.get(pe_country, []):
                        if _e["city"] == pe_city:
                            _pe_postal_list = _e.get("postal_codes", [])
                            break
                _pe_postal_default = fresh.get("postal_code") or "— any —"
                _pe_postal_opts = ["— any —"] + _pe_postal_list
                _pe_postal_idx = _pe_postal_opts.index(_pe_postal_default) if _pe_postal_default in _pe_postal_opts else 0
                pe_postal = st.selectbox("Postal code", _pe_postal_opts,
                                         index=_pe_postal_idx, key="pe_postal",
                                         disabled=(pe_city == "— select —"))

                st.subheader("Shelter Info")
                new_shelter_name = st.text_input("Shelter name",
                                                   value=fresh.get("shelter_name") or "",
                                                   key="pe_shelter_name")
                new_shelter_address = st.text_input("Street address",
                                                      value=fresh.get("shelter_address") or "",
                                                      key="pe_shelter_address",
                                                      placeholder="Rua da Esperança 12")
                new_shelter_desc = st.text_area("Shelter description",
                                                  value=fresh.get("shelter_description") or "",
                                                  height=80, key="pe_shelter_desc",
                                                  placeholder="About your shelter, mission, capacity…")

            submitted = st.form_submit_button("💾 Save Profile", type="primary",
                                              use_container_width=True)

        if submitted:
            updates: dict = {
                "email": new_email.strip(),
                "phone": new_phone.strip(),
                "website": new_website.strip(),
                "bio": new_bio.strip(),
            }
            if is_manager:
                updates["shelter_name"] = new_shelter_name.strip()
                updates["shelter_address"] = new_shelter_address.strip()
                updates["shelter_description"] = new_shelter_desc.strip()
                updates["country"] = pe_country if pe_country != "— select —" else None
                updates["city"] = pe_city if pe_city != "— select —" else None
                updates["postal_code"] = pe_postal if pe_postal != "— any —" else None

            if db.update_user(user["id"], **updates):
                refreshed = db.get_user_by_id(user["id"])
                if refreshed:
                    st.session_state.user = refreshed
                st.success("Profile updated!")
                st.rerun()
            else:
                st.error("Failed to update profile.")


# ── Shelter Map ────────────────────────────────────────────────────────────────

# Approximate city centre coordinates for map centering
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "Kabul": (34.5553, 69.2075), "Tirana": (41.3275, 19.8187), "Algiers": (36.7372, 3.0865),
    "Buenos Aires": (-34.6037, -58.3816), "Yerevan": (40.1792, 44.4991),
    "Sydney": (-33.8688, 151.2093), "Melbourne": (-37.8136, 144.9631),
    "Brisbane": (-27.4698, 153.0251), "Perth": (-31.9505, 115.8605),
    "Adelaide": (-34.9285, 138.6007), "Wien": (48.2082, 16.3738),
    "Graz": (47.0707, 15.4395), "Baku": (40.4093, 49.8671),
    "Dhaka": (23.8103, 90.4125), "Minsk": (53.9045, 27.5615),
    "Brussels": (50.8503, 4.3517), "Antwerp": (51.2194, 4.4025),
    "La Paz": (-16.5000, -68.1193), "Sarajevo": (43.8476, 18.3564),
    "São Paulo": (-23.5505, -46.6333), "Rio de Janeiro": (-22.9068, -43.1729),
    "Brasília": (-15.7942, -47.8822), "Sofia": (42.6977, 23.3219),
    "Phnom Penh": (11.5564, 104.9282), "Toronto": (43.6532, -79.3832),
    "Vancouver": (49.2827, -123.1207), "Montreal": (45.5017, -73.5673),
    "Calgary": (51.0447, -114.0719), "Ottawa": (45.4215, -75.6972),
    "Santiago": (-33.4489, -70.6693), "Beijing": (39.9042, 116.4074),
    "Shanghai": (31.2304, 121.4737), "Guangzhou": (23.1291, 113.2644),
    "Shenzhen": (22.5431, 114.0579), "Bogotá": (4.7110, -74.0721),
    "Medellín": (6.2442, -75.5812), "Zagreb": (45.8150, 15.9819),
    "Prague": (50.0755, 14.4378), "Brno": (49.1951, 16.6068),
    "Copenhagen": (55.6761, 12.5683), "Quito": (-0.1807, -78.4678),
    "Cairo": (30.0444, 31.2357), "Alexandria": (31.2001, 29.9187),
    "Tallinn": (59.4370, 24.7536), "Addis Ababa": (9.0320, 38.7423),
    "Helsinki": (60.1699, 24.9384), "Paris": (48.8566, 2.3522),
    "Lyon": (45.7640, 4.8357), "Marseille": (43.2965, 5.3698),
    "Tbilisi": (41.6938, 44.8015), "Berlin": (52.5200, 13.4050),
    "München": (48.1351, 11.5820), "Hamburg": (53.5753, 10.0153),
    "Frankfurt": (50.1109, 8.6821), "Köln": (50.9333, 6.9500),
    "Accra": (5.6037, -0.1870), "Athens": (37.9838, 23.7275),
    "Thessaloniki": (40.6401, 22.9444), "Guatemala City": (14.6349, -90.5069),
    "Budapest": (47.4979, 19.0402), "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090), "Bangalore": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867), "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639), "Jakarta": (-6.2088, 106.8456),
    "Surabaya": (-7.2575, 112.7521), "Bandung": (-6.9175, 107.6191),
    "Tehran": (35.6892, 51.3890), "Baghdad": (33.3152, 44.3661),
    "Dublin": (53.3498, -6.2603), "Tel Aviv": (32.0853, 34.7818),
    "Jerusalem": (31.7683, 35.2137), "Roma": (41.9028, 12.4964),
    "Milano": (45.4654, 9.1859), "Napoli": (40.8518, 14.2681),
    "Tokyo": (35.6762, 139.6503), "Osaka": (34.6937, 135.5023),
    "Kyoto": (35.0116, 135.7681), "Yokohama": (35.4437, 139.6380),
    "Amman": (31.9454, 35.9284), "Nur-Sultan (Astana)": (51.1811, 71.4460),
    "Almaty": (43.2220, 76.8512), "Nairobi": (-1.2921, 36.8219),
    "Seoul": (37.5665, 126.9780), "Busan": (35.1796, 129.0756),
    "Pristina": (42.6629, 21.1655), "Kuwait City": (29.3759, 47.9774),
    "Riga": (56.9496, 24.1052), "Beirut": (33.8938, 35.5018),
    "Vilnius": (54.6872, 25.2797), "Luxembourg City": (49.6117, 6.1319),
    "Kuala Lumpur": (3.1390, 101.6869), "Johor Bahru": (1.4927, 103.7414),
    "Penang": (5.4141, 100.3288), "Petaling Jaya": (3.1073, 101.6067),
    "Shah Alam": (3.0733, 101.5185), "Ipoh": (4.5975, 101.0901),
    "Kota Kinabalu": (5.9804, 116.0735), "Kuching": (1.5535, 110.3593),
    "Mexico City": (19.4326, -99.1332), "Guadalajara": (20.6597, -103.3496),
    "Monterrey": (25.6866, -100.3161), "Chișinău": (47.0105, 28.8638),
    "Podgorica": (42.4304, 19.2594), "Casablanca": (33.5731, -7.5898),
    "Rabat": (33.9716, -6.8498), "Yangon": (16.8661, 96.1951),
    "Amsterdam": (52.3676, 4.9041), "Rotterdam": (51.9244, 4.4777),
    "Den Haag": (52.0705, 4.3007), "Auckland": (-36.8485, 174.7633),
    "Wellington": (-41.2866, 174.7756), "Lagos": (6.5244, 3.3792),
    "Abuja": (9.0765, 7.3986), "Skopje": (41.9981, 21.4254),
    "Oslo": (59.9139, 10.7522), "Bergen": (60.3913, 5.3221),
    "Karachi": (24.8607, 67.0011), "Lahore": (31.5204, 74.3587),
    "Islamabad": (33.6844, 73.0479), "Lima": (-12.0464, -77.0428),
    "Manila": (14.5995, 120.9842), "Quezon City": (14.6760, 121.0437),
    "Warsaw": (52.2297, 21.0122), "Kraków": (50.0647, 19.9450),
    "Lisboa": (38.7169, -9.1399), "Porto": (41.1579, -8.6291),
    "Braga": (41.5454, -8.4265), "Coimbra": (40.2033, -8.4103),
    "Faro": (37.0194, -7.9304), "Bucharest": (44.4268, 26.1025),
    "Cluj-Napoca": (46.7712, 23.6236), "Moscow": (55.7558, 37.6173),
    "Saint Petersburg": (59.9311, 30.3609), "Riyadh": (24.6877, 46.7219),
    "Jeddah": (21.4858, 39.1925), "Dakar": (14.6928, -17.4467),
    "Belgrade": (44.8176, 20.4569), "Singapore": (1.3521, 103.8198),
    "Bratislava": (48.1486, 17.1077), "Ljubljana": (46.0569, 14.5058),
    "Johannesburg": (-26.2041, 28.0473), "Cape Town": (-33.9249, 18.4241),
    "Durban": (-29.8587, 31.0218), "Madrid": (40.4168, -3.7038),
    "Barcelona": (41.3851, 2.1734), "Valencia": (39.4699, -0.3763),
    "Sevilla": (37.3886, -5.9823), "Colombo": (6.9271, 79.8612),
    "Stockholm": (59.3293, 18.0686), "Gothenburg": (57.7089, 11.9746),
    "Zürich": (47.3769, 8.5417), "Genève": (46.2044, 6.1432),
    "Basel": (47.5596, 7.5886), "Bern": (46.9480, 7.4474),
    "Taipei": (25.0330, 121.5654), "Bangkok": (13.7563, 100.5018),
    "Chiang Mai": (18.7883, 98.9853), "Tunis": (36.8065, 10.1815),
    "Istanbul": (41.0082, 28.9784), "Ankara": (39.9334, 32.8597),
    "Kyiv": (50.4501, 30.5234), "Kharkiv": (49.9935, 36.2304),
    "Dubai": (25.2048, 55.2708), "Abu Dhabi": (24.4539, 54.3773),
    "London": (51.5074, -0.1278), "Birmingham": (52.4862, -1.8904),
    "Manchester": (53.4808, -2.2426), "Glasgow": (55.8642, -4.2518),
    "New York City": (40.7128, -74.0060), "Los Angeles": (34.0522, -118.2437),
    "Chicago": (41.8781, -87.6298), "Houston": (29.7604, -95.3698),
    "Philadelphia": (39.9526, -75.1652), "San Francisco": (37.7749, -122.4194),
    "Seattle": (47.6062, -122.3321), "Miami": (25.7617, -80.1918),
    "Boston": (42.3601, -71.0589), "Atlanta": (33.7490, -84.3880),
    "Montevideo": (-34.9011, -56.1645), "Tashkent": (41.2995, 69.2401),
    "Caracas": (10.4806, -66.9036), "Hanoi": (21.0285, 105.8542),
    "Ho Chi Minh City": (10.8231, 106.6297), "Harare": (-17.8252, 31.0335),
}


def render_shelter_map(user: dict | None):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>🗺️ Find Shelters Near You</h1>",
                unsafe_allow_html=True)

    locs = _load_locations()
    countries = ["All"] + locs.get("countries", [])
    cities_by_country = locs.get("cities_by_country", {})
    db_shelters = db.get_all_shelters()

    # ── Location pickers + reset ───────────────────────────────────────────────
    _sm_reset_col, col_c, col_ci, col_p = st.columns([0.8, 2, 2, 1.5])
    with _sm_reset_col:
        st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
        if st.button("↺ Reset", key="sm_reset", use_container_width=True, type="secondary"):
            for _k in ("sm_country", "sm_city", "sm_postal"):
                st.session_state.pop(_k, None)
            st.rerun()
    with col_c:
        sel_country = st.selectbox("Country", countries, key="sm_country")
    with col_ci:
        city_list = []
        if sel_country != "All" and sel_country in cities_by_country:
            city_list = [c["city"] for c in cities_by_country[sel_country]]
        city_opts = ["All cities"] + city_list
        sel_city = st.selectbox("City", city_opts, key="sm_city",
                                disabled=(sel_country == "All"))
    with col_p:
        postal_list = []
        if sel_city not in ("All cities", "All") and sel_country in cities_by_country:
            for entry in cities_by_country[sel_country]:
                if entry["city"] == sel_city:
                    postal_list = entry.get("postal_codes", [])
                    break
        postal_opts = ["— any —"] + postal_list
        sel_postal = st.selectbox("Postal code", postal_opts, key="sm_postal",
                                  disabled=(sel_city in ("All cities", "All")))

    # ── Build shelter markers (resolve coords from _CITY_COORDS if needed) ────
    map_rows = []
    for s in db_shelters:
        city = s.get("city") or ""
        coords = _CITY_COORDS.get(city) if city else None
        if coords:
            map_rows.append({
                "name": s.get("shelter_name") or s.get("username", ""),
                "city": city,
                "country": s.get("country") or "",
                "phone": s.get("phone") or "",
                "lat": coords[0],
                "lon": coords[1],
                "type": "Registered shelter",
            })

    # Apply filters to marker list
    filtered_rows = list(map_rows)
    if sel_country != "All":
        filtered_rows = [r for r in filtered_rows if r["country"] == sel_country]
    if sel_city not in ("All cities", "All"):
        filtered_rows = [r for r in filtered_rows if r["city"] == sel_city]

    # ── Determine map centre + zoom ────────────────────────────────────────────
    if sel_city not in ("All cities", "All") and _CITY_COORDS.get(sel_city):
        centre_lat, centre_lon = _CITY_COORDS[sel_city]
        zoom = 11
    elif sel_country != "All" and sel_country in cities_by_country and cities_by_country[sel_country]:
        first_city = cities_by_country[sel_country][0]["city"]
        c = _CITY_COORDS.get(first_city)
        centre_lat, centre_lon = (c if c else (20.0, 10.0))
        zoom = 5
    elif filtered_rows:
        centre_lat = sum(r["lat"] for r in filtered_rows) / len(filtered_rows)
        centre_lon = sum(r["lon"] for r in filtered_rows) / len(filtered_rows)
        zoom = 4
    else:
        # Default: show Malaysia (where seeded data is)
        centre_lat, centre_lon, zoom = 4.2105, 108.9758, 5

    # Build display dataframe — registered shelters as primary, fill with city dots if empty
    if filtered_rows:
        df_map = pd.DataFrame(filtered_rows)
    elif sel_country != "All" and sel_country in cities_by_country:
        # Show city reference dots for the selected country
        city_dots = []
        for entry in cities_by_country[sel_country]:
            c = _CITY_COORDS.get(entry["city"])
            if c:
                city_dots.append({"name": entry["city"], "city": entry["city"],
                                   "country": sel_country, "phone": "",
                                   "lat": c[0], "lon": c[1], "type": "City"})
        df_map = pd.DataFrame(city_dots) if city_dots else pd.DataFrame()
    else:
        # World default: show all shelters with known coords
        df_map = pd.DataFrame(map_rows) if map_rows else pd.DataFrame()

    # ── Map ────────────────────────────────────────────────────────────────────
    if not df_map.empty:
        color_col = "type" if "type" in df_map.columns else None
        fig = px.scatter_mapbox(
            df_map, lat="lat", lon="lon",
            hover_name="name",
            hover_data={c: (c in df_map.columns and c not in ("lat", "lon"))
                        for c in ("city", "country", "phone", "type")},
            color=color_col,
            color_discrete_map={"Registered shelter": COLOR_PRIMARY, "City": "#AABBCC"},
            zoom=zoom, height=500,
            center={"lat": centre_lat, "lon": centre_lon},
        )
        fig.update_traces(marker={"size": 12, "opacity": 0.85})
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            legend={"title": "", "bgcolor": "rgba(255,255,255,0.8)",
                    "bordercolor": "#E5E7EB", "borderwidth": 1},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Always show a base map even without markers
        fig = go.Figure(go.Scattermapbox())
        fig.update_layout(
            mapbox={"style": "open-street-map",
                    "center": {"lat": centre_lat, "lon": centre_lon},
                    "zoom": zoom},
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("No registered shelters found for this location yet.")

    # ── Registered shelters list ───────────────────────────────────────────────
    st.markdown("---")

    # Filter shelter list
    filtered_shelters = db_shelters
    if sel_country != "All":
        filtered_shelters = [s for s in filtered_shelters if s.get("country") == sel_country]
    if sel_city not in ("All cities", "All"):
        filtered_shelters = [s for s in filtered_shelters if s.get("city") == sel_city]

    count_label = (f"{len(filtered_shelters)} shelter{'s' if len(filtered_shelters) != 1 else ''} "
                   f"registered on AdoptSense")
    st.subheader(f"🏥 {count_label}")

    if filtered_shelters:
        for s in filtered_shelters:
            s_name = s.get("shelter_name") or s.get("username", "Unknown shelter")
            s_addr = s.get("shelter_address") or s.get("location") or ""
            s_city = s.get("city") or ""
            s_country = s.get("country") or ""
            s_phone = s.get("phone") or ""
            loc_parts = [p for p in [s_city, s_country] if p]
            with st.container(border=True):
                sc1, sc2 = st.columns([4, 1])
                with sc1:
                    st.markdown(f"**{s_name}**")
                    if loc_parts:
                        st.caption(f"📍 {', '.join(loc_parts)}"
                                   + (f"  ·  {s_addr}" if s_addr else ""))
                    if s_phone:
                        st.caption(f"📞 {s_phone}")
                with sc2:
                    if user and user.get("role") == "household":
                        if st.button("💬 Chat", key=f"sm_chat_{s['id']}",
                                     use_container_width=True):
                            _nav("chat", mp_chat_with=s["id"])
                    elif not user:
                        if st.button("🔑 Log in", key=f"sm_login_{s['id']}",
                                     use_container_width=True, type="secondary"):
                            st.session_state.show_auth = "login"
                            st.rerun()
    else:
        st.caption("No registered shelters found for the selected location.")
