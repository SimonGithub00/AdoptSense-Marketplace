"""
Marketplace UI — themed version.

Keeps ALL of Simon's original function signatures, DB calls, and Gemini calls
intact. Only the visual markup (cards, layout, badges, hero blocks) is new.

This module is called from frontend/app.py via direct function imports —
NOT via the original `show_matching_platform()` entry point. The old
top-level navigation has moved up into the brand navbar (frontend/components/header.py).

Public functions (called by app.py):
  - render_browse(user)
  - render_detail(listing_id, user)
  - render_my_listings(user)
  - render_create_listing(user)
  - render_edit_listing(listing_id, user)
  - render_kpis(user)
  - render_watchlist(user)
  - render_chat(user)
"""
import uuid
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_BG_SOFT, COLOR_BORDER,
    COLOR_TEXT_BODY, COLOR_TEXT_MUTED, SPEED_COLORS,
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


# ── Internal helpers (carried over from Simon's original) ──────────────────────

def _nav(view: str, **kwargs):
    """Navigate to a marketplace view and rerun."""
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
    """Save an UploadedFile to disk. Robust against re-read corruption.

    Streamlit's UploadedFile.read() can return a corrupt buffer when called
    after previous reads on the same object across reruns (Windows + GC
    timing). We seek-and-read defensively, and bail with a clear error
    rather than writing zero bytes silently.
    """
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
    """Save raw bytes (no UploadedFile) to the uploads dir."""
    dest_dir = UPLOAD_DIR / str(listing_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_{name}"
    dest = dest_dir / fname
    dest.write_bytes(data)
    return str(dest)


def _show_gallery(photos: list[dict], max_cols: int = 3):
    """Photo gallery used on the detail page (carried over from Simon's original)."""
    valid = [p for p in photos if _img_bytes(p["photo_path"])]
    if not valid:
        st.caption("No photos available.")
        return
    cols = st.columns(min(len(valid), max_cols))
    for i, p in enumerate(valid):
        data = _img_bytes(p["photo_path"])
        with cols[i % max_cols]:
            st.image(data, use_container_width=True)
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


# ── Filters (carried from Simon's original, slight CSS polish) ─────────────────

def _render_filters(is_manager: bool) -> dict:
    with st.expander("🔍 Filters", expanded=False):
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
            max_fee = st.number_input("Max fee", 0, 5000, 5000, step=50, key="f_fee")
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

        shelters = db.get_all_shelters()
        s_opts = {0: "All shelters"}
        s_opts.update({s["id"]: s["shelter_name"] or s["username"] for s in shelters})
        sel_s = st.selectbox("From shelter", list(s_opts.keys()),
                             format_func=lambda x: s_opts[x], key="f_shelter")
        if sel_s:
            f["shelter_id"] = sel_s

        if is_manager:
            spd = st.selectbox(
                "Max predicted speed (performance filter)",
                options=[-1, 0, 1, 2, 3, 4],
                format_func=lambda x: "Any" if x == -1
                else f"Speed {x} — {ADOPTION_SPEED_LABELS[x]}",
                key="f_speed"
            )
            if spd >= 0:
                f["max_speed"] = spd
    return f


# ── Browse ─────────────────────────────────────────────────────────────────────

def render_browse(user: dict | None):
    """Adopter browse page — themed pet card grid + filters."""
    is_manager = bool(user and user.get("role") == "shelter_manager")
    filters = _render_filters(is_manager=is_manager)
    listings = db.get_listings(filters)

    if not listings:
        st.info("No listings match your filters.")
        return

    st.caption(f"{len(listings)} pets available")

    # 3-column grid of branded pet cards
    cols = st.columns(3, gap="medium")
    for i, listing in enumerate(listings):
        with cols[i % 3]:
            render_pet_card(listing, show_speed=is_manager, key_prefix="browse")


# ── Detail ─────────────────────────────────────────────────────────────────────

def render_detail(listing_id: int, user: dict | None):
    """Pet detail page — themed layout, all of Simon's logic preserved."""
    listing = db.get_listing(listing_id)
    if not listing:
        st.error("Listing not found.")
        if st.button("← Back to Browse", key="detail_back_missing"):
            _nav("browse")
        return

    db.increment_views(listing_id)

    if st.button("← Back to Browse", key=f"detail_back_{listing_id}"):
        _nav("browse")

    # ── Header: pet name + meta ───────────────────────────────────────────────
    pet_name = listing.get("pet_name", "—")
    age_months = listing.get("age", 0)
    age_label = (f"{int(age_months / 12)} years" if age_months >= 12
                 else f"{int(age_months)} months")
    type_label = TYPE_MAP.get(listing.get("type", 1), "Pet").split()[0]
    gender_label = GENDER_MAP.get(listing.get("gender", 1), "")
    state_label = STATE_MAP.get(listing.get("state", 0), "")

    header_html = (
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
        f'margin:8px 0;">'
        f'<h1 style="font-size:36px;font-weight:600;color:{COLOR_PRIMARY};margin:0;'
        f'letter-spacing:-0.5px;">{pet_name}</h1>'
        f'<span style="font-size:14px;color:{COLOR_TEXT_MUTED};">📍 {state_label}</span>'
        f'</div>'
        f'<div style="font-size:15px;color:{COLOR_TEXT_BODY};margin-bottom:24px;">'
        f'{type_label} · {age_label} · {gender_label}</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    photos = db.get_photos(listing_id)
    col_photo, col_info = st.columns([1.2, 1], gap="large")

    with col_photo:
        _show_gallery(photos)

    with col_info:
        # Quick info grid (2x2)
        info_grid_html = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;'
            f'margin-bottom:20px;">'
            f'{_info_box_html("Health", HEALTH_MAP.get(listing.get("health", 1), "?"))}'
            f'{_info_box_html("Adoption Fee", "Free" if listing.get("fee", 0) == 0 else f"€{int(listing.get(chr(34)+chr(102)+chr(101)+chr(101)+chr(34), 0))}")}'
            f'{_info_box_html("Vaccinated", VACCINATED_MAP.get(listing.get("vaccinated", 3), "?"))}'
            f'{_info_box_html("Sterilized", STERILIZED_MAP.get(listing.get("sterilized", 3), "?"))}'
            f'</div>'
        )
        # Note: f-string above is slightly awkward because of nested quoting; rewrite cleaner:
        fee_value = listing.get("fee", 0) or 0
        fee_label = "Free" if fee_value == 0 else f"€{int(fee_value)}"
        info_grid_html = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;'
            f'margin-bottom:20px;">'
            f'{_info_box_html("Health", HEALTH_MAP.get(listing.get("health", 1), "?"))}'
            f'{_info_box_html("Adoption Fee", fee_label)}'
            f'{_info_box_html("Vaccinated", VACCINATED_MAP.get(listing.get("vaccinated", 3), "?"))}'
            f'{_info_box_html("Sterilized", STERILIZED_MAP.get(listing.get("sterilized", 3), "?"))}'
            f'</div>'
        )
        st.markdown(info_grid_html, unsafe_allow_html=True)

        # Shelter card
        shelter_name = (listing.get("shelter_name")
                        or listing.get("shelter_username", "Unknown shelter"))
        initials = "".join([w[0] for w in shelter_name.split()[:2]]).upper() or "?"
        shelter_html = (
            f'<div style="background:#F8F9FB;border:1px solid {COLOR_BORDER};'
            f'border-radius:12px;padding:14px;margin-bottom:20px;display:flex;'
            f'align-items:center;gap:12px;">'
            f'<div style="width:40px;height:40px;background:{COLOR_PRIMARY};'
            f'color:#FFFFFF;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;font-weight:500;flex-shrink:0;font-size:13px;">'
            f'{initials}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:13px;font-weight:500;color:{COLOR_PRIMARY};">'
            f'{shelter_name}</div>'
            f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};">'
            f'Listed {listing.get("created_at", "")[:10]}</div>'
            f'</div></div>'
        )
        st.markdown(shelter_html, unsafe_allow_html=True)

    # ── Description ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"<h3 style='color:{COLOR_PRIMARY};font-weight:600;'>About {pet_name}</h3>",
                unsafe_allow_html=True)
    desc = listing.get("description_improved") or listing.get("description") or ""
    if listing.get("description_improved") and listing.get("description"):
        with st.expander("Show original description"):
            st.caption(listing["description"])
    st.markdown(desc if desc else "*No description provided.*")

    # ── Household actions: save / message ────────────────────────────────────
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
                    st.success("Added to watchlist!")
                    st.rerun()
        with msg_col:
            shelter_uid = listing.get("shelter_user_id") or listing.get("shelter_id")
            if st.button("💬 Message Shelter", use_container_width=True,
                         key=f"detail_msg_{listing_id}"):
                _nav("chat", mp_chat_with=shelter_uid, mp_chat_listing=listing_id)

    elif not user:
        st.markdown("---")
        st.info("Log in to save this pet to your watchlist or message the shelter.")
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

    # ── Shelter manager: own-listing performance + photo studio ──────────────
    if (user and user.get("role") == "shelter_manager"
            and user["id"] == listing.get("shelter_id")):
        _render_manager_listing_panel(listing, listing_id, photos)


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
    """Render a single adoption-factor card with green (helping) or red (hindering) tint."""
    if kind == "positive":
        bg = "#F0F9F2"          # light green
        border = "#B5D8C0"
        accent = "#2E7D32"      # darker green for label
    else:
        bg = "#FDF2F2"          # light red/rose
        border = "#F5C2C2"
        accent = "#B71C1C"      # darker red for label
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


def _render_manager_listing_panel(listing: dict, listing_id: int, photos: list):
    """The shelter-manager-only block on the detail page (KPIs, factors, photo studio)."""
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
            st.caption("No significant hindering factors. Great profile!")

    # Photo studio (carried from Simon's original — every Gemini call preserved)
    if photos:
        st.markdown("---")
        st.markdown(f"<h3 style='color:{COLOR_PRIMARY};font-weight:600;'>📸 Photo Studio</h3>",
                    unsafe_allow_html=True)
        for p in photos:
            img_b = _img_bytes(p["photo_path"])
            if not img_b:
                continue
            pending_key = f"studio_pending_{p['id']}"
            choice_key = f"studio_use_{p['id']}"
            pending_bytes = st.session_state.get(pending_key)

            if pending_bytes:
                st.caption(f"🖼️ Photo {p['id']} — compare and choose:")
                ba1, ba2 = st.columns(2)
                with ba1:
                    st.caption("📷 Original")
                    st.image(img_b, use_container_width=True)
                with ba2:
                    st.caption("✨ Studio version")
                    st.image(pending_bytes, use_container_width=True)
                st.radio(
                    "Keep which version?",
                    ["studio", "original"],
                    format_func=lambda x: "✨ Studio version" if x == "studio" else "📷 Keep original",
                    key=choice_key, horizontal=True, index=0,
                )
                if st.button("✅ Confirm choice", key=f"det_confirm_{p['id']}"):
                    choice = st.session_state.get(choice_key, "studio")
                    if choice == "studio":
                        sp = STUDIO_DIR / str(listing_id) / f"studio_{p['id']}.png"
                        stk_p = STUDIO_DIR / str(listing_id) / f"sticker_{p['id']}.png"
                        sp.parent.mkdir(parents=True, exist_ok=True)
                        sp.write_bytes(pending_bytes)
                        ok_stk, sticker_bytes = gemini_utils.make_sticker(img_b)
                        if ok_stk and sticker_bytes:
                            stk_p.write_bytes(sticker_bytes)
                        db.update_photo_studio(p["id"], str(sp))
                    st.session_state.pop(pending_key, None)
                    st.session_state.pop(choice_key, None)
                    st.rerun()
            else:
                sc1, sc2 = st.columns([1, 3])
                with sc1:
                    st.image(img_b, width=100)
                with sc2:
                    if p.get("is_studio_ready"):
                        st.success("✅ Studio-ready")
                        s_b = _img_bytes(p.get("studio_photo_path") or "")
                        if s_b:
                            st.download_button(
                                "⬇️ Studio photo", data=s_b,
                                file_name=f"studio_{p['id']}.png", mime="image/png",
                                key=f"det_dl_s_{p['id']}",
                            )
                        if p.get("studio_photo_path"):
                            stk_path = str(p["studio_photo_path"]).replace(
                                f"studio_{p['id']}", f"sticker_{p['id']}"
                            )
                            stk_b = _img_bytes(stk_path)
                            if stk_b:
                                st.download_button(
                                    "⬇️ Sticker (transparent bg)", data=stk_b,
                                    file_name=f"sticker_{p['id']}.png", mime="image/png",
                                    key=f"det_dl_tk_{p['id']}",
                                )
                    else:
                        if st.button("✨ Make Studio Ready", key=f"det_studio_{p['id']}"):
                            with st.status("Creating studio photo…", expanded=True) as status:
                                status.write("🎨 Asking Gemini for the best backdrop colour…")
                                gem_ok, bg_color = gemini_utils.get_studio_bg_color(img_b)
                                if not gem_ok:
                                    status.write("⚠️ Gemini colour suggestion unavailable — using default.")
                                status.write("✂️ Removing background and compositing…")
                                ok_s, result = gemini_utils.make_studio_ready_bytes(img_b, bg_color)
                                if ok_s:
                                    st.session_state[pending_key] = result
                                    status.update(label="✅ Studio photo ready!", state="complete")
                                else:
                                    status.update(label="❌ Processing failed", state="error")
                            if ok_s:
                                st.rerun()
                            else:
                                st.error(result)

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


# ── My Listings (carried from Simon, header restyled) ──────────────────────────

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


# ── Create Listing (Simon's original form + themed Listing Agent panel) ────────

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
    """Saved-confirmation screen shown after a successful publish.

    Three CTAs: view the new listing, create another, go to My Listings.
    All cleanups happen when the user picks one of the actions.
    """
    new_listing_id = st.session_state.get("_cl_published_id")
    listing = db.get_listing(new_listing_id) if new_listing_id else None
    pet_name = listing.get("pet_name", "Your pet") if listing else "Your pet"

    st.markdown(
        f'<div style="text-align:center;padding:48px 24px;">'
        f'<div style="font-size:64px;margin-bottom:12px;">✅</div>'
        f'<h1 style="font-size:32px;font-weight:600;color:{COLOR_PRIMARY};'
        f'margin:0 0 8px;letter-spacing:-0.5px;">Listing published!</h1>'
        f'<p style="font-size:15px;color:{COLOR_TEXT_MUTED};margin:0 0 32px;">'
        f'<strong>{pet_name}</strong> is now visible to adopters. '
        f'You can review or edit it at any time.</p>'
        f'</div>',
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
    """Clear all create-listing form state and the post-publish flag."""
    st.session_state.pop("_cl_just_published", None)
    st.session_state.pop("_cl_published_id", None)
    st.session_state.pop("cl_generated_desc", None)
    for k in list(st.session_state.keys()):
        if k.startswith("cl_") and k != "cl_gem_key":
            st.session_state.pop(k, None)


def render_create_listing(user: dict):
    """Create-listing page — Simon's logic, themed AI ASSISTED header.

    If we just published a listing, show a Saved-confirmation screen first.
    """
    if st.session_state.get("_cl_just_published"):
        _render_publish_confirmation()
        return

    # Branded header with AI ASSISTED pill
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
        fee = st.number_input("Adoption fee", 0, 5000, 0, step=10, key="cl_fee")
        state_opts = list(STATE_MAP.keys())
        state = st.selectbox("State", state_opts, key="cl_state",
                             format_func=lambda x: STATE_MAP[x])
        video_amt = st.number_input("Videos", 0, 10, 0, key="cl_video")

        breed_opts = [(bid, bname) for bid, btype, bname in BREED_DATA if btype == pet_type]
        breed_ids = [b[0] for b in breed_opts]
        breed_names = [b[1] for b in breed_opts]
        b1_name = st.selectbox("Primary breed", breed_names, key=f"cl_breed1_{pet_type}")
        breed1 = breed_ids[breed_names.index(b1_name)] if b1_name in breed_names else breed_ids[0]
        b2_name = st.selectbox("Secondary breed", ["None"] + breed_names,
                               key=f"cl_breed2_{pet_type}")
        breed2 = (0 if b2_name == "None"
                  else (breed_ids[breed_names.index(b2_name)] if b2_name in breed_names else 0))

    st.markdown("---")
    st.subheader("📸 Photos")
    uploaded_files = st.file_uploader(
        "Upload pet photos (JPG/PNG)",
        type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="cl_photos"
    )

    # Photo enhancement loop.
    # Two AI paths per upload: Quick Studio (local rembg) and AI Studio
    # (Gemini 2.5 Flash Image). Each is independent — running one does
    # NOT replace the other. User picks at publish time which to use.
    #
    # IMPORTANT: read each upload's bytes ONCE per iteration and reuse the
    # cached bytes. Calling uf.read() multiple times (even with seek(0)
    # between calls) is unreliable across Streamlit reruns on some
    # platforms — manifests as "OSError: broken data stream" from PIL.
    if uploaded_files:
        for i, uf in enumerate(uploaded_files):
            bokeh_key = f"cl_bokeh_{i}"         # Bokeh (sharp pet on blurred BG) bytes
            studio_key = f"cl_studio_{i}"       # Studio (sharp pet on backdrop) bytes
            studio_fn_key = f"cl_studio_fn_{i}"
            choice_key = f"cl_studio_use_{i}"   # values: original / bokeh / studio

            # When the file at this slot changes, clear all derived versions
            if st.session_state.get(studio_fn_key) != uf.name:
                for k in (bokeh_key, studio_key, choice_key):
                    st.session_state.pop(k, None)
            st.session_state[studio_fn_key] = uf.name

            # Read the upload bytes ONCE
            try:
                uf.seek(0)
                upload_bytes = uf.read()
                uf.seek(0)
                if not upload_bytes:
                    st.warning(f"Could not read {uf.name} — skipping.")
                    continue
            except Exception as exc:
                st.warning(f"Could not read {uf.name}: {exc}")
                continue

            bokeh_bytes = st.session_state.get(bokeh_key)
            studio_bytes = st.session_state.get(studio_key)

            st.caption(f"📸 **{uf.name}**")

            # ── Preview row: 3 columns side by side ────────────────────────
            cols = st.columns(3)
            with cols[0]:
                st.caption("📷 Original")
                st.image(upload_bytes, use_container_width=True)
            with cols[1]:
                st.caption("🌸 Bokeh")
                if bokeh_bytes:
                    st.image(bokeh_bytes, use_container_width=True)
                else:
                    st.markdown(
                        "<div style='background:#F3F4F6;border-radius:8px;"
                        "height:160px;display:flex;align-items:center;"
                        "justify-content:center;color:#9CA3AF;font-size:13px;'>"
                        "Not generated yet</div>",
                        unsafe_allow_html=True,
                    )
            with cols[2]:
                st.caption("🎨 Studio")
                if studio_bytes:
                    st.image(studio_bytes, use_container_width=True)
                else:
                    st.markdown(
                        "<div style='background:#F3F4F6;border-radius:8px;"
                        "height:160px;display:flex;align-items:center;"
                        "justify-content:center;color:#9CA3AF;font-size:13px;'>"
                        "Not generated yet</div>",
                        unsafe_allow_html=True,
                    )

            # ── Action buttons row: Bokeh + Studio generate ────────────────
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button(
                    "🌸 Generate Bokeh" if not bokeh_bytes else "🌸 Regenerate Bokeh",
                    key=f"cl_bokeh_btn_{i}",
                    use_container_width=True,
                    help="Sharp pet on a blurred version of the original background — like a portrait shot. Best when the original setting is nice.",
                ):
                    ok_b = False
                    with st.status("Creating Bokeh photo…", expanded=True) as status:
                        status.write("✂️ Removing background…")
                        status.write("📷 Blurring original scene…")
                        ok_b, result = gemini_utils.make_bokeh_bytes(upload_bytes)
                        if ok_b:
                            st.session_state[bokeh_key] = result
                            status.update(label="✅ Bokeh ready!", state="complete")
                        else:
                            status.update(label="❌ Processing failed", state="error")
                    if ok_b:
                        st.rerun()
                    else:
                        st.error(result)
            with bc2:
                if st.button(
                    "🎨 Generate Studio" if not studio_bytes else "🎨 Regenerate Studio",
                    key=f"cl_studio_btn_{i}",
                    use_container_width=True,
                    help="Sharp pet on a clean studio backdrop — colour chosen by Gemini to flatter the pet. Best when the original background is unflattering.",
                ):
                    ok_s = False
                    with st.status("Creating Studio photo…", expanded=True) as status:
                        status.write("🎨 Asking Gemini for the best backdrop colour…")
                        gem_ok, bg_color = gemini_utils.get_studio_bg_color(upload_bytes)
                        if not gem_ok:
                            status.write("⚠️ Colour suggestion unavailable — using default.")
                        status.write("✂️ Removing background and compositing…")
                        ok_s, result = gemini_utils.make_studio_ready_bytes(upload_bytes, bg_color)
                        if ok_s:
                            st.session_state[studio_key] = result
                            status.update(label="✅ Studio ready!", state="complete")
                        else:
                            status.update(label="❌ Processing failed", state="error")
                    if ok_s:
                        st.rerun()
                    else:
                        st.error(result)

            # ── Choice radio ──────────────────────────────────────────────
            if bokeh_bytes or studio_bytes:
                options = ["original"]
                option_labels = {"original": "📷 Original photo"}
                if bokeh_bytes:
                    options.append("bokeh")
                    option_labels["bokeh"] = "🌸 Bokeh version"
                if studio_bytes:
                    options.append("studio")
                    option_labels["studio"] = "🎨 Studio version"

                # Default to Bokeh > Studio > Original (Bokeh tends to look more natural)
                current = st.session_state.get(choice_key)
                if current not in options:
                    if "bokeh" in options:
                        st.session_state[choice_key] = "bokeh"
                    elif "studio" in options:
                        st.session_state[choice_key] = "studio"
                    else:
                        st.session_state[choice_key] = "original"

                st.radio(
                    "Which version to publish?",
                    options,
                    format_func=lambda x: option_labels[x],
                    key=choice_key,
                    horizontal=True,
                )
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📝 Description")
    description = st.text_area(
        "Raw description (optional — used as context for AI generation)",
        height=100, placeholder="Personality, history, care needs…", key="cl_desc"
    )

    _gc, _cc = st.columns([3, 1])
    with _gc:
        if gemini_utils.is_configured():
            if st.button("🤖 Generate AI Description", key="cl_gen_desc_btn",
                         use_container_width=True):
                base = description.strip() or (
                    f"{TYPE_MAP.get(pet_type, 'Pet')} named {pet_name or 'this pet'}"
                )
                first_bytes = None
                if uploaded_files:
                    first_bytes = uploaded_files[0].read()
                    uploaded_files[0].seek(0)
                with st.spinner("Generating description with Gemini AI…"):
                    ok, result = gemini_utils.improve_description(
                        base,
                        {"type": pet_type, "age": age, "gender": gender,
                         "health": health, "vaccinated": vaccinated,
                         "sterilized": sterilized, "fee": fee},
                        image_bytes=first_bytes,
                    )
                if ok:
                    st.session_state["cl_generated_desc"] = result
                    st.session_state.pop("cl_gen_desc_area", None)
                    st.rerun()
                else:
                    st.warning(result)
        else:
            st.caption("🔑 Configure a Gemini API key below to enable AI description generation.")
    with _cc:
        if st.session_state.get("cl_generated_desc"):
            if st.button("✕ Clear AI", key="cl_gen_desc_clear", use_container_width=True):
                st.session_state.pop("cl_generated_desc", None)
                st.session_state.pop("cl_gen_desc_area", None)
                st.rerun()

    if st.session_state.get("cl_generated_desc"):
        st.success("✨ AI description generated — review and edit before publishing:")
        st.text_area(
            "AI description",
            value=st.session_state.get("cl_generated_desc", ""),
            height=120, key="cl_gen_desc_area", label_visibility="collapsed",
        )

    if not gemini_utils.is_configured():
        with st.expander("🔑 Configure Gemini API Key"):
            api_key = st.text_input("Gemini API Key", type="password", key="cl_gem_key")
            if api_key:
                gemini_utils.set_api_key(api_key)
                st.success("Key set for this session.")

    st.markdown("---")
    if st.button("🚀 Publish Listing", type="primary", key="cl_publish"):
        if not pet_name.strip():
            st.error("Pet name is required.")
            return

        pet_df = pd.DataFrame([{
            "Type": pet_type, "Name": pet_name, "Age": age,
            "Breed1": breed1, "Breed2": breed2, "Gender": gender,
            "Color1": color1, "Color2": color2, "Color3": color3,
            "MaturitySize": maturity_size, "FurLength": fur_length,
            "Vaccinated": vaccinated, "Dewormed": dewormed, "Sterilized": sterilized,
            "Health": health, "Quantity": quantity, "Fee": fee, "State": state,
            "PhotoAmt": len(uploaded_files), "VideoAmt": video_amt,
            "Description": description,
        }])

        speed = conf = None
        with st.spinner("Predicting adoption speed…"):
            pred = make_prediction(pet_df)
        if pred.get("success"):
            p0 = pred["predictions"][0]
            speed, conf = p0["prediction"], p0["confidence"]

        improved_desc = st.session_state.get("cl_gen_desc_area", "").strip() or None

        lid = db.create_listing(
            shelter_id=user["id"], pet_name=pet_name.strip(), pet_type=pet_type,
            age=age, breed1=breed1, breed2=breed2, gender=gender,
            color1=color1, color2=color2, color3=color3,
            maturity_size=maturity_size, fur_length=fur_length,
            vaccinated=vaccinated, dewormed=dewormed, sterilized=sterilized,
            health=health, quantity=quantity, fee=fee, state=state,
            video_amt=video_amt, description=description,
            description_improved=improved_desc,
            adoption_speed_pred=speed, adoption_speed_confidence=conf,
        )

        for i, uf in enumerate(uploaded_files):
            choice = st.session_state.get(f"cl_studio_use_{i}", "original")
            bokeh_b = st.session_state.get(f"cl_bokeh_{i}")
            studio_b = st.session_state.get(f"cl_studio_{i}")

            if choice == "bokeh" and bokeh_b:
                dest_dir = UPLOAD_DIR / str(lid)
                dest_dir.mkdir(parents=True, exist_ok=True)
                stem = uf.name.rsplit(".", 1)[0]
                dest = dest_dir / f"{uuid.uuid4().hex}_{stem}_bokeh.png"
                dest.write_bytes(bokeh_b)
                db.add_photo(lid, str(dest))
            elif choice == "studio" and studio_b:
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

        # Show a clear "Saved" confirmation screen instead of jumping straight to detail.
        # User can choose: view the new listing, create another, or go to My Listings.
        st.session_state["_cl_published_id"] = lid
        st.session_state["_cl_just_published"] = True
        st.rerun()


# ── Edit Listing (carried from Simon, header restyled) ─────────────────────────

def render_edit_listing(listing_id: int, user: dict):
    listing = db.get_listing(listing_id)
    if not listing or listing.get("shelter_id") != user["id"]:
        st.error("Not found or access denied.")
        return

    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>✏️ Edit — {listing['pet_name']}</h1>",
                unsafe_allow_html=True)
    if st.button("← Back", key="el_back"):
        _nav("detail", mp_listing_id=listing_id)

    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet Name", value=listing["pet_name"], key="el_name")
        age = st.slider("Age (months)", 0, 120, int(listing["age"] or 0), key="el_age")
        fee = st.number_input("Fee", 0, 5000, int(listing["fee"] or 0), step=10, key="el_fee")
        health = st.selectbox("Health", [1, 2, 3], key="el_health",
                              index=max(0, int(listing["health"] or 1) - 1),
                              format_func=lambda x: HEALTH_MAP[x])
        vaccinated = st.selectbox("Vaccinated", [1, 2, 3], key="el_vacc",
                                  index=max(0, int(listing["vaccinated"] or 3) - 1),
                                  format_func=lambda x: VACCINATED_MAP[x])
        sterilized = st.selectbox("Sterilized", [1, 2, 3], key="el_ster",
                                  index=max(0, int(listing["sterilized"] or 3) - 1),
                                  format_func=lambda x: STERILIZED_MAP[x])
        dewormed = st.selectbox("Dewormed", [1, 2, 3], key="el_dew",
                                index=max(0, int(listing["dewormed"] or 3) - 1),
                                format_func=lambda x: DEWORMED_MAP[x])
    with col2:
        description = st.text_area("Description", value=listing.get("description") or "",
                                   height=120, key="el_desc")
        description_improved = st.text_area(
            "Improved description (edit or leave blank to keep existing)",
            value=st.session_state.pop("el_regen_staged", listing.get("description_improved") or ""),
            height=120, key="el_imp_desc",
        )

    st.markdown("---")
    st.subheader("📸 Studio-Ready Photos")
    photos = db.get_photos(listing_id)

    if not gemini_utils.is_configured():
        with st.expander("🔑 Configure Gemini API Key"):
            ak = st.text_input("Gemini API Key", type="password", key="el_gem_key")
            if ak:
                gemini_utils.set_api_key(ak)
                st.success("Key set.")

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
                        fname = Path(p["studio_photo_path"]).name
                        st.download_button(
                            "⬇️ Download Studio photo", data=s_b, file_name=fname,
                            mime="image/png", key=f"dl_ed_s_{p['id']}"
                        )
                    if p.get("studio_photo_path"):
                        stk_path = str(p["studio_photo_path"]).replace(
                            f"studio_{p['id']}", f"sticker_{p['id']}"
                        )
                        stk_b = _img_bytes(stk_path)
                        if stk_b:
                            st.download_button(
                                "⬇️ Download Sticker (transparent bg)",
                                data=stk_b, file_name=f"sticker_{p['id']}.png",
                                mime="image/png", key=f"dl_ed_tk_{p['id']}",
                            )
                else:
                    ed_pending_key = f"studio_pending_{p['id']}"
                    ed_choice_key = f"studio_use_{p['id']}"
                    ed_pending = st.session_state.get(ed_pending_key)
                    if ed_pending:
                        st.caption("Compare and choose:")
                        eb1, eb2 = st.columns(2)
                        with eb1:
                            st.caption("📷 Original")
                            st.image(img_b, use_container_width=True)
                        with eb2:
                            st.caption("✨ Studio version")
                            st.image(ed_pending, use_container_width=True)
                        st.radio(
                            "Keep which version?",
                            ["studio", "original"],
                            format_func=lambda x: "✨ Studio version" if x == "studio" else "📷 Keep original",
                            key=ed_choice_key, horizontal=True, index=0,
                        )
                        if st.button("✅ Confirm", key=f"ed_confirm_{p['id']}"):
                            ed_choice = st.session_state.get(ed_choice_key, "studio")
                            if ed_choice == "studio":
                                sp = STUDIO_DIR / str(listing_id) / f"studio_{p['id']}.png"
                                stk_p = STUDIO_DIR / str(listing_id) / f"sticker_{p['id']}.png"
                                sp.parent.mkdir(parents=True, exist_ok=True)
                                sp.write_bytes(ed_pending)
                                ok_stk, sticker_bytes = gemini_utils.make_sticker(img_b)
                                if ok_stk and sticker_bytes:
                                    stk_p.write_bytes(sticker_bytes)
                                db.update_photo_studio(p["id"], str(sp))
                            st.session_state.pop(ed_pending_key, None)
                            st.session_state.pop(ed_choice_key, None)
                            st.rerun()
                    else:
                        if st.button("✨ Make Studio Ready", key=f"ed_studio_{p['id']}"):
                            with st.status("Creating studio photo…", expanded=True) as status:
                                status.write("🎨 Asking Gemini for the best backdrop colour…")
                                gem_ok, bg_color = gemini_utils.get_studio_bg_color(img_b)
                                if not gem_ok:
                                    status.write("⚠️ Gemini colour suggestion unavailable.")
                                status.write("✂️ Removing background and compositing…")
                                ok_ed, result = gemini_utils.make_studio_ready_bytes(img_b, bg_color)
                                if ok_ed:
                                    st.session_state[ed_pending_key] = result
                                    status.update(label="✅ Studio photo ready!", state="complete")
                                else:
                                    status.update(label="❌ Processing failed", state="error")
                            if ok_ed:
                                st.rerun()
                            else:
                                st.error(result)
    else:
        st.caption("No photos uploaded for this listing.")

    st.subheader("📸 Add more photos")
    new_photos = st.file_uploader("Upload additional photos", type=["jpg", "jpeg", "png"],
                                  accept_multiple_files=True, key="el_photos")

    if gemini_utils.is_configured() and description.strip():
        if st.button("🤖 Regenerate improved description with Gemini", key="el_regen"):
            first_img = _img_bytes(photos[0]["photo_path"]) if photos else None
            with st.spinner("Improving description…"):
                ok, res = gemini_utils.improve_description(
                    description,
                    {"type": listing["type"], "age": listing["age"],
                     "gender": listing["gender"], "health": health,
                     "vaccinated": vaccinated, "sterilized": sterilized, "fee": fee},
                    image_bytes=first_img,
                )
            if ok:
                st.session_state["el_regen_staged"] = res
                st.session_state.pop("el_imp_desc", None)
                st.rerun()
            else:
                st.warning(res)

    st.markdown("---")
    if st.button("💾 Save Changes", type="primary", key="el_save"):
        updates = {
            "pet_name": pet_name.strip(), "age": age, "fee": fee,
            "health": health, "vaccinated": vaccinated,
            "sterilized": sterilized, "dewormed": dewormed,
            "description": description,
        }
        imp = st.session_state.get("el_imp_desc", description_improved)
        if imp and imp.strip():
            updates["description_improved"] = imp.strip()
        db.update_listing(listing_id, **updates)
        for uf in new_photos:
            dest = _save_upload(uf, listing_id)
            db.add_photo(listing_id, dest)
        st.success("Saved!")
        _nav("detail", mp_listing_id=listing_id)


# ── KPI Dashboard (carried from Simon, header restyled) ────────────────────────

def render_kpis(user: dict):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>📊 Performance Dashboard</h1>",
                unsafe_allow_html=True)
    kpis = db.get_shelter_kpis(user["id"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total listings", kpis["total"])
    c2.metric("Active", kpis["active"])
    c3.metric("Adopted", kpis["adopted"])
    c4.metric("Adoption rate", f"{kpis['adoption_rate']:.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    avg_spd = kpis["avg_adoption_speed"]
    avg_los = kpis["avg_los_days"]
    c5.metric("Avg speed", f"{avg_spd:.1f}" if avg_spd is not None else "—")
    c6.metric("Avg LOS (days)", f"{avg_los:.0f}" if avg_los is not None else "—")
    c7.metric("Total views", kpis["total_views"])
    c8.metric("Contact rate", f"{kpis['contact_rate']:.1f}%")

    st.markdown("---")
    t1, t2, t3 = st.tabs(["📈 Listings over time", "🎯 Speed distribution", "📋 All listings"])

    with t1:
        ls = kpis["listings"]
        if ls:
            df = pd.DataFrame(ls)
            df["month"] = pd.to_datetime(df["created_at"]).dt.to_period("M").astype(str)
            grp = df.groupby("month").size().reset_index(name="count")
            fig = go.Figure(go.Bar(x=grp["month"], y=grp["count"],
                                    marker_color=COLOR_PRIMARY))
            fig.update_layout(title="Listings created per month", height=300,
                              xaxis_title="Month", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    with t2:
        speeds = [l["adoption_speed_pred"] for l in kpis["listings"]
                  if l.get("adoption_speed_pred") is not None]
        if speeds:
            fig = px.histogram(x=speeds, nbins=5, title="Predicted speed distribution",
                               labels={"x": "Speed", "count": "Pets"},
                               color_discrete_sequence=[COLOR_PRIMARY_LIGHT])
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No predictions yet.")

    with t3:
        if kpis["listings"]:
            rows = []
            for l in kpis["listings"]:
                spd = l.get("adoption_speed_pred")
                rows.append({
                    "Name": l["pet_name"],
                    "Status": l["status"].title(),
                    "Speed": (f"{ADOPTION_SPEED_EMOJI.get(spd, '')} {ADOPTION_SPEED_LABELS.get(spd, '—')}"
                              if spd is not None else "—"),
                    "Views": l.get("views") or 0,
                    "Contacts": l.get("contacts") or 0,
                    "LOS (days)": l.get("adoption_time_days") or "—",
                    "Created": l["created_at"][:10],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Watchlist (carried from Simon, header restyled) ────────────────────────────

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
                    _nav("chat", mp_chat_with=s_uid, mp_chat_listing=listing["id"])
            with wc4:
                if st.button("🗑️ Remove", key=f"wlr_{listing['id']}",
                             use_container_width=True):
                    db.remove_from_watchlist(user["id"], listing["id"])
                    st.rerun()


# ── Chat (carried from Simon, header restyled) ─────────────────────────────────

def render_chat(user: dict):
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY};'>💬 Messages</h1>",
                unsafe_allow_html=True)
    conversations = db.get_user_conversations(user["id"])
    other_id = st.session_state.get("mp_chat_with")
    listing_id = st.session_state.get("mp_chat_listing")

    cl, cr = st.columns([1, 2])

    with cl:
        st.markdown("**Conversations**")
        if not conversations:
            st.caption("No conversations yet.")
        for conv in conversations:
            label = conv.get("other_username", "?")
            if conv.get("pet_name"):
                label += f" · {conv['pet_name']}"
            unread = conv.get("unread_count", 0)
            btn_lbl = f"{'🔴 ' if unread else ''}{label}"
            if st.button(btn_lbl,
                         key=f"conv_{conv['other_id']}_{conv.get('listing_id', 0)}",
                         use_container_width=True):
                st.session_state.mp_chat_with = conv["other_id"]
                st.session_state.mp_chat_listing = conv.get("listing_id")
                st.rerun()

    with cr:
        if not other_id:
            st.info("Select a conversation to start chatting.")
            return

        other = db.get_user_by_id(other_id)
        other_name = other["username"] if other else "Unknown"

        if listing_id:
            listing = db.get_listing(listing_id)
            pet_name = listing["pet_name"] if listing else "?"
            st.markdown(f"**{other_name}** — *{pet_name}*")
        else:
            st.markdown(f"**{other_name}**")

        messages = db.get_conversation(user["id"], other_id, listing_id)
        db.mark_messages_read(user["id"], other_id, listing_id)

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

        send_n_key = f"chat_send_n_{other_id}_{listing_id or 0}"
        send_count = st.session_state.get(send_n_key, 0)
        chat_key = f"chat_input_{other_id}_{listing_id or 0}_{send_count}"
        ic, bc = st.columns([5, 1])
        with ic:
            txt = st.text_input("Message", key=chat_key, label_visibility="collapsed",
                                placeholder="Type a message…")
        with bc:
            if st.button("Send ▶", key=f"chat_send_{other_id}_{listing_id or 0}"):
                content = st.session_state.get(chat_key, "").strip()
                if content:
                    db.send_message(user["id"], other_id, content, listing_id)
                    st.session_state[send_n_key] = send_count + 1
                    st.rerun()
