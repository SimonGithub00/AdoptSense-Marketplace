"""
Marketplace UI — two personas: Shelter Managers and Private Households.
Navigation is session-state driven within the Marketplace tab.
"""
import io
import uuid
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def _show_gallery(photos: list[dict], max_cols: int = 3):
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


def _save_upload(uploaded, listing_id: int) -> str:
    dest_dir = UPLOAD_DIR / str(listing_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_{uploaded.name}"
    dest = dest_dir / fname
    dest.write_bytes(uploaded.read())
    return str(dest)


# ── Filters ────────────────────────────────────────────────────────────────────

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
                f["min_age"] = age_r[0]; f["max_age"] = age_r[1]
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
            spd = st.selectbox("Max predicted speed (performance filter)",
                               options=[-1, 0, 1, 2, 3, 4],
                               format_func=lambda x: "Any" if x == -1 else f"Speed {x} — {ADOPTION_SPEED_LABELS[x]}",
                               key="f_speed")
            if spd >= 0:
                f["max_speed"] = spd
    return f


def _listing_card(listing: dict, user: dict | None):
    photos = db.get_photos(listing["id"])
    with st.container(border=True):
        first_photo = next((p for p in photos if _img_bytes(p["photo_path"])), None)
        if first_photo:
            st.image(_img_bytes(first_photo["photo_path"]), use_container_width=True)
        else:
            emoji = "🐶" if listing["type"] == 1 else "🐱"
            st.markdown(
                f"<div style='text-align:center;font-size:3rem;padding:1rem;background:#f8f8f8;border-radius:8px;'>{emoji}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(f"**{listing['pet_name']}**")
        fee_str = "Free" if listing["fee"] == 0 else f"{int(listing['fee'])}"
        st.caption(f"{TYPE_MAP.get(listing['type'], '?')} · {listing['age']} mo · {fee_str}")

        speed = listing.get("adoption_speed_pred")
        if speed is not None:
            color = ADOPTION_SPEED_COLORS[speed]
            st.markdown(
                f"<span style='background:{color};color:white;padding:2px 8px;"
                f"border-radius:5px;font-size:0.8em;'>"
                f"{ADOPTION_SPEED_EMOJI[speed]} {ADOPTION_SPEED_LABELS[speed]}</span>",
                unsafe_allow_html=True,
            )

        shelter = listing.get("shelter_name") or listing.get("shelter_username", "")
        st.caption(f"🏥 {shelter}")
        st.markdown("")
        if st.button("📋 Details", key=f"det_{listing['id']}", use_container_width=True):
            _nav("detail", mp_listing_id=listing["id"])


# ── Browse ─────────────────────────────────────────────────────────────────────

def render_browse(user: dict | None):
    is_manager = bool(user and user.get("role") == "shelter_manager")
    filters = _render_filters(is_manager=is_manager)
    listings = db.get_listings(filters)

    if not listings:
        st.info("No listings match your filters.")
        return

    st.caption(f"{len(listings)} pets found")
    cols = st.columns(3)
    for i, listing in enumerate(listings):
        with cols[i % 3]:
            _listing_card(listing, user)


# ── Detail ─────────────────────────────────────────────────────────────────────

def render_detail(listing_id: int, user: dict | None):
    listing = db.get_listing(listing_id)
    if not listing:
        st.error("Listing not found.")
        if st.button("← Browse"):
            _nav("browse")
        return

    db.increment_views(listing_id)

    if st.button("← Back to Browse"):
        _nav("browse")

    st.markdown(f"## {listing['pet_name']}")

    photos = db.get_photos(listing_id)
    col_photo, col_info = st.columns([1, 1])

    with col_photo:
        _show_gallery(photos)

    with col_info:
        data_rows = [
            ("Type", TYPE_MAP.get(listing["type"], "?")),
            ("Age", f"{listing['age']} months"),
            ("Gender", GENDER_MAP.get(listing["gender"], "?")),
            ("Size", SIZE_MAP.get(listing["maturity_size"], "?")),
            ("Fur", FUR_MAP.get(listing["fur_length"], "?")),
            ("Health", HEALTH_MAP.get(listing["health"], "?")),
            ("Vaccinated", VACCINATED_MAP.get(listing["vaccinated"], "?")),
            ("Dewormed", DEWORMED_MAP.get(listing["dewormed"], "?")),
            ("Sterilized", STERILIZED_MAP.get(listing["sterilized"], "?")),
            ("Primary color", COLOR_MAP.get(listing["color1"], "?")),
            ("Fee", "Free" if listing["fee"] == 0 else str(int(listing["fee"]))),
            ("Quantity", listing["quantity"]),
            ("State", STATE_MAP.get(listing["state"], str(listing["state"]))),
            ("Shelter", listing.get("shelter_name") or listing.get("shelter_username", "")),
        ]
        for k, v in data_rows:
            st.markdown(f"**{k}:** {v}")

    st.markdown("---")
    st.markdown("### Description")
    desc = listing.get("description_improved") or listing.get("description") or ""
    if listing.get("description_improved") and listing.get("description"):
        with st.expander("Show original description"):
            st.caption(listing["description"])
    st.markdown(desc if desc else "*No description provided.*")

    # Household actions
    if user and user.get("role") == "household":
        st.markdown("---")
        wl_col, msg_col = st.columns(2)
        with wl_col:
            in_wl = db.is_in_watchlist(user["id"], listing_id)
            if in_wl:
                if st.button("💔 Remove from Watchlist", use_container_width=True):
                    db.remove_from_watchlist(user["id"], listing_id)
                    st.rerun()
            else:
                if st.button("❤️ Add to Watchlist", use_container_width=True):
                    db.add_to_watchlist(user["id"], listing_id)
                    st.success("Added to watchlist!")
                    st.rerun()
        with msg_col:
            shelter_uid = listing.get("shelter_user_id") or listing.get("shelter_id")
            if st.button("💬 Message Shelter", use_container_width=True):
                _nav("chat", mp_chat_with=shelter_uid, mp_chat_listing=listing_id)

    elif not user:
        st.markdown("---")
        st.info("Log in to save to watchlist or message the shelter.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔑 Log In"):
                st.session_state.show_auth = "login"
                st.rerun()
        with c2:
            if st.button("📝 Register"):
                st.session_state.show_auth = "register"
                st.rerun()

    # Shelter manager — own listing performance (hidden from households)
    if (user and user.get("role") == "shelter_manager"
            and user["id"] == listing.get("shelter_id")):
        st.markdown("---")
        st.markdown("### 📊 Listing Performance")

        # Adoption speed prediction
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
            st.markdown("**Helping adoption**")
            for fac in pos_f:
                with st.container(border=True):
                    st.markdown(f"**{fac['label']}**")
                    st.caption(fac["sentence"])
            if not pos_f:
                st.caption("No strong positive factors identified.")
        with fc2:
            st.markdown("**Hindering adoption**")
            for fac in neg_f:
                with st.container(border=True):
                    st.markdown(f"**{fac['label']}**")
                    st.caption(fac["sentence"])
            if not neg_f:
                st.caption("No significant hindering factors. Great profile!")

        # ── Photo Studio — directly accessible without going to Edit ─────────
        photo_list = db.get_photos(listing_id)
        if photo_list:
            st.markdown("---")
            st.markdown("### 📸 Photo Studio")
            for p in photo_list:
                img_b = _img_bytes(p["photo_path"])
                if not img_b:
                    continue
                pending_key = f"studio_pending_{p['id']}"
                choice_key = f"studio_use_{p['id']}"
                pending_bytes = st.session_state.get(pending_key)

                if pending_bytes:
                    # Before/after comparison — let the manager choose
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
                        key=choice_key,
                        horizontal=True,
                        index=0,
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
                            ok_s = False
                            if st.button("✨ Make Studio Ready", key=f"det_studio_{p['id']}"):
                                with st.status("Creating studio photo…", expanded=True) as status:
                                    status.write("🎨 Asking Gemini for the best backdrop colour…")
                                    gem_ok, bg_color = gemini_utils.get_studio_bg_color(img_b)
                                    if not gem_ok:
                                        status.write("⚠️ Gemini colour suggestion unavailable — using default backdrop.")
                                    status.write("✂️ Removing background and compositing…")
                                    ok_s, result = gemini_utils.make_studio_ready_bytes(img_b, bg_color)
                                    if ok_s:
                                        st.session_state[pending_key] = result
                                        status.update(label="✅ Studio photo ready! Choose your preferred version below.", state="complete")
                                    else:
                                        status.update(label="❌ Processing failed", state="error")
                                if ok_s:
                                    st.rerun()
                                else:
                                    st.error(result)

        st.markdown("---")
        act1, act2, act3 = st.columns(3)
        with act1:
            if st.button("✏️ Edit Listing", use_container_width=True):
                _nav("edit", mp_listing_id=listing_id)
        with act2:
            if listing.get("status") == "available":
                if st.button("✅ Mark as Adopted", use_container_width=True):
                    db.mark_adopted(listing_id, listing.get("adoption_speed_pred", 2))
                    st.success("Marked as adopted!")
                    st.rerun()
        with act3:
            if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
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
    st.markdown("## 📋 My Listings")
    listings = db.get_shelter_listings(user["id"])

    if not listings:
        st.info("No listings yet.")
        if st.button("➕ Create First Listing"):
            _nav("create")
        return

    active = [l for l in listings if l["status"] == "available"]
    adopted = [l for l in listings if l["status"] == "adopted"]
    rate = len(adopted) / len(listings) * 100 if listings else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(listings)); c2.metric("Active", len(active))
    c3.metric("Adopted", len(adopted)); c4.metric("Adoption rate", f"{rate:.1f}%")

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
                if st.button("📋 View", key=f"mlv_{listing['id']}", use_container_width=True):
                    _nav("detail", mp_listing_id=listing["id"])
            with lc3:
                if listing["status"] == "available":
                    if st.button("✅ Adopted", key=f"mla_{listing['id']}", use_container_width=True):
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


def render_create_listing(user: dict):
    # Clear stale form state from a previously published listing
    if st.session_state.pop("_cl_just_published", False):
        for k in list(st.session_state.keys()):
            if k.startswith("cl_") and k != "cl_gem_key":
                st.session_state.pop(k, None)
        st.rerun()

    st.markdown("## ➕ Create New Listing")

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
        b2_name = st.selectbox("Secondary breed", ["None"] + breed_names, key=f"cl_breed2_{pet_type}")
        breed2 = 0 if b2_name == "None" else (breed_ids[breed_names.index(b2_name)] if b2_name in breed_names else 0)

    st.markdown("---")
    st.subheader("📸 Photos")
    uploaded_files = st.file_uploader(
        "Upload pet photos (JPG/PNG)",
        type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="cl_photos"
    )

    if uploaded_files:
        for i, uf in enumerate(uploaded_files):
            studio_key = f"cl_studio_{i}"
            studio_fn_key = f"cl_studio_fn_{i}"
            choice_key = f"cl_studio_use_{i}"

            # Invalidate cached studio result when the file at this slot changes
            if st.session_state.get(studio_fn_key) != uf.name:
                st.session_state.pop(studio_key, None)
                st.session_state.pop(choice_key, None)
            st.session_state[studio_fn_key] = uf.name

            studio_bytes = st.session_state.get(studio_key)

            if studio_bytes:
                # Before/after comparison
                st.caption(f"📸 **{uf.name}**")
                ba1, ba2 = st.columns(2)
                with ba1:
                    st.caption("📷 Original")
                    uf.seek(0)
                    st.image(uf.read(), use_container_width=True)
                    uf.seek(0)
                with ba2:
                    st.caption("✨ Studio version")
                    st.image(studio_bytes, use_container_width=True)
                st.radio(
                    "Which version to publish?",
                    ["studio", "original"],
                    format_func=lambda x: "✨ Studio version" if x == "studio" else "📷 Original photo",
                    key=choice_key,
                    horizontal=True,
                )
            else:
                pc1, pc2 = st.columns([1, 4])
                with pc1:
                    uf.seek(0)
                    st.image(uf.read(), width=90)
                    uf.seek(0)
                with pc2:
                    st.caption(uf.name)
                    if gemini_utils.is_configured():
                        if st.button("✨ Make Studio Ready", key=f"cl_studio_btn_{i}"):
                            uf.seek(0)
                            img_data = uf.read()
                            uf.seek(0)
                            ok_s = False
                            with st.status("Creating studio photo…", expanded=True) as status:
                                status.write("🎨 Asking Gemini for the best backdrop colour…")
                                gem_ok, bg_color = gemini_utils.get_studio_bg_color(img_data)
                                if not gem_ok:
                                    status.write("⚠️ Gemini colour suggestion unavailable — using default backdrop.")
                                status.write("✂️ Removing background and compositing…")
                                ok_s, result = gemini_utils.make_studio_ready_bytes(img_data, bg_color)
                                if ok_s:
                                    st.session_state[studio_key] = result
                                    status.update(label="✅ Studio photo ready! Choose your preferred version below.", state="complete")
                                else:
                                    status.update(label="❌ Processing failed", state="error")
                            if ok_s:
                                st.rerun()
                            else:
                                st.error(result)

    st.markdown("---")
    st.subheader("📝 Description")
    description = st.text_area(
        "Raw description (optional — used as context for AI generation)",
        height=100, placeholder="Personality, history, care needs…", key="cl_desc"
    )

    # ── Generate AI Description button ───────────────────────────────────────
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

        # Use the AI-generated description if the user clicked Generate Description
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
            studio_b = st.session_state.get(f"cl_studio_{i}")
            if choice == "studio" and studio_b:
                dest_dir = UPLOAD_DIR / str(lid)
                dest_dir.mkdir(parents=True, exist_ok=True)
                stem = uf.name.rsplit(".", 1)[0]
                dest = dest_dir / f"{uuid.uuid4().hex}_{stem}.png"
                dest.write_bytes(studio_b)
                db.add_photo(lid, str(dest))
            else:
                uf.seek(0)
                dest = _save_upload(uf, lid)
                db.add_photo(lid, dest)

        # Clear form state on the next visit to Create Listing
        st.session_state["_cl_just_published"] = True
        _nav("detail", mp_listing_id=lid)


# ── Edit Listing ───────────────────────────────────────────────────────────────

def render_edit_listing(listing_id: int, user: dict):
    listing = db.get_listing(listing_id)
    if not listing or listing.get("shelter_id") != user["id"]:
        st.error("Not found or access denied.")
        return

    st.markdown(f"## ✏️ Edit — {listing['pet_name']}")
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

    # ── Studio-ready photos ──────────────────────────────────────────────────
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
                    # Sticker: derive path from studio path (saved alongside during processing)
                    if p.get("studio_photo_path"):
                        stk_path = str(p["studio_photo_path"]).replace(
                            f"studio_{p['id']}", f"sticker_{p['id']}"
                        )
                        stk_b = _img_bytes(stk_path)
                        if stk_b:
                            st.download_button(
                                "⬇️ Download Sticker (transparent bg)",
                                data=stk_b,
                                file_name=f"sticker_{p['id']}.png",
                                mime="image/png",
                                key=f"dl_ed_tk_{p['id']}",
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
                            key=ed_choice_key,
                            horizontal=True,
                            index=0,
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
                        ok_ed = False
                        if st.button("✨ Make Studio Ready", key=f"ed_studio_{p['id']}"):
                            with st.status("Creating studio photo…", expanded=True) as status:
                                status.write("🎨 Asking Gemini for the best backdrop colour…")
                                gem_ok, bg_color = gemini_utils.get_studio_bg_color(img_b)
                                if not gem_ok:
                                    status.write("⚠️ Gemini colour suggestion unavailable — using default backdrop.")
                                status.write("✂️ Removing background and compositing…")
                                ok_ed, result = gemini_utils.make_studio_ready_bytes(img_b, bg_color)
                                if ok_ed:
                                    st.session_state[ed_pending_key] = result
                                    status.update(label="✅ Studio photo ready! Choose your preferred version below.", state="complete")
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

    # ── Gemini description regeneration ─────────────────────────────────────
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
                # Stage the result; the text area reinitialises from this on next render
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


# ── KPI Dashboard ──────────────────────────────────────────────────────────────

def render_kpis(user: dict):
    st.markdown("## 📊 Performance Dashboard")
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
            fig = go.Figure(go.Bar(x=grp["month"], y=grp["count"], marker_color="#667eea"))
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
                               color_discrete_sequence=["#764ba2"])
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
                    "Speed": f"{ADOPTION_SPEED_EMOJI.get(spd, '')} {ADOPTION_SPEED_LABELS.get(spd, '—')}" if spd is not None else "—",
                    "Views": l.get("views") or 0,
                    "Contacts": l.get("contacts") or 0,
                    "LOS (days)": l.get("adoption_time_days") or "—",
                    "Created": l["created_at"][:10],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Watchlist ──────────────────────────────────────────────────────────────────

def render_watchlist(user: dict):
    st.markdown("## ❤️ My Watchlist")
    listings = db.get_watchlist(user["id"])
    if not listings:
        st.info("Your watchlist is empty. Browse pets and click ❤️ to save them!")
        return

    for listing in listings:
        with st.container(border=True):
            wc1, wc2, wc3, wc4 = st.columns([3, 1, 1, 1])
            with wc1:
                spd = listing.get("adoption_speed_pred")
                badge = (f" {ADOPTION_SPEED_EMOJI.get(spd, '')} {ADOPTION_SPEED_LABELS.get(spd, '')}"
                         if spd is not None else "")
                st.markdown(f"**{listing['pet_name']}** —{badge}")
                sh = listing.get("shelter_name") or listing.get("shelter_username", "")
                st.caption(f"🏥 {sh} · Saved {listing['saved_at'][:10]}")
            with wc2:
                if st.button("📋 Details", key=f"wld_{listing['id']}", use_container_width=True):
                    _nav("detail", mp_listing_id=listing["id"])
            with wc3:
                s_uid = listing.get("shelter_id")
                if st.button("💬 Message", key=f"wlm_{listing['id']}", use_container_width=True):
                    _nav("chat", mp_chat_with=s_uid, mp_chat_listing=listing["id"])
            with wc4:
                if st.button("🗑️ Remove", key=f"wlr_{listing['id']}", use_container_width=True):
                    db.remove_from_watchlist(user["id"], listing["id"])
                    st.rerun()


# ── Chat ───────────────────────────────────────────────────────────────────────

def render_chat(user: dict):
    st.markdown("## 💬 Messages")
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
                bg = "#667eea" if is_me else "#f0f0f0"
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

        # Message input — rotate the widget key after each send to clear it without
        # touching a live widget's session state (which Streamlit forbids).
        send_n_key = f"chat_send_n_{other_id}_{listing_id or 0}"
        send_count = st.session_state.get(send_n_key, 0)
        chat_key = f"chat_input_{other_id}_{listing_id or 0}_{send_count}"
        ic, bc = st.columns([5, 1])
        with ic:
            txt = st.text_input(
                "Message", key=chat_key, label_visibility="collapsed",
                placeholder="Type a message…"
            )
        with bc:
            if st.button("Send ▶", key=f"chat_send_{other_id}_{listing_id or 0}"):
                content = st.session_state.get(chat_key, "").strip()
                if content:
                    db.send_message(user["id"], other_id, content, listing_id)
                    st.session_state[send_n_key] = send_count + 1
                    st.rerun()


# ── Entry point ────────────────────────────────────────────────────────────────

def show_matching_platform():
    user = auth.current_user()
    is_manager = bool(user and user.get("role") == "shelter_manager")

    if "mp_view" not in st.session_state:
        st.session_state.mp_view = "browse"
    view = st.session_state.mp_view

    # ── Inline navigation bar ─────────────────────────────────────────────────
    nav_items: list[tuple[str, str]] = [("🔍 Browse", "browse")]
    if user:
        if is_manager:
            nav_items += [
                ("📋 My Listings", "my_listings"),
                ("➕ Create Listing", "create"),
                ("📊 KPIs", "kpis"),
            ]
        else:
            nav_items.append(("❤️ Watchlist", "watchlist"))
        unread = db.get_unread_count(user["id"])
        msg_lbl = f"💬 Messages{f' ({unread})' if unread else ''}"
        nav_items.append((msg_lbl, "chat"))

    nav_cols = st.columns(len(nav_items))
    for i, (label, target) in enumerate(nav_items):
        with nav_cols[i]:
            btn_type = "primary" if view == target else "secondary"
            if st.button(label, use_container_width=True,
                         type=btn_type, key=f"nav_{target}"):
                _nav(target)

    st.markdown("---")

    # ── View routing ──────────────────────────────────────────────────────────
    if view == "browse":
        st.markdown("### 🐾 Marketplace")
        st.caption("Browse pets available for adoption. Log in to use full features.")
        render_browse(user)

    elif view == "detail":
        lid = st.session_state.get("mp_listing_id")
        if lid:
            render_detail(lid, user)
        else:
            _nav("browse")

    elif view == "my_listings":
        if not auth.require_login("manage your listings"):
            return
        if not is_manager:
            st.error("Only shelter managers can access My Listings.")
            return
        render_my_listings(user)

    elif view == "create":
        if not auth.require_login("create a listing"):
            return
        if not is_manager:
            st.error("Only shelter managers can create listings.")
            return
        render_create_listing(user)

    elif view == "edit":
        if not auth.require_login("edit listings"):
            return
        lid = st.session_state.get("mp_listing_id")
        if lid:
            render_edit_listing(lid, user)
        else:
            _nav("browse")

    elif view == "kpis":
        if not auth.require_login("view performance data"):
            return
        if not is_manager:
            st.error("Only shelter managers can view KPIs.")
            return
        render_kpis(user)

    elif view == "watchlist":
        if not auth.require_login("use your watchlist"):
            return
        if is_manager:
            st.error("Watchlist is for households only.")
            return
        render_watchlist(user)

    elif view == "chat":
        if not auth.require_login("send messages"):
            return
        render_chat(user)
