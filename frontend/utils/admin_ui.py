"""
Admin dashboard — platform-wide overview for the Admin account.
Renders charts, KPI metrics, user/listing/survey tables, and event feed.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from frontend.styles import COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT_MUTED, COLOR_BORDER
from frontend.utils import db, auth


def render_admin_dashboard(user: dict):
    st.markdown(
        f'<h1 style="color:{COLOR_PRIMARY};margin-bottom:4px;">🛡️ Admin Dashboard</h1>'
        f'<p style="color:{COLOR_TEXT_MUTED};font-size:13px;margin-top:0;">'
        f'Platform-wide overview · AdoptSense</p>',
        unsafe_allow_html=True,
    )

    stats = db.get_platform_stats()

    # ── Tier-1 metrics ────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total users", stats["total_users"])
    c2.metric("Adopters", stats["households"])
    c3.metric("Shelters", stats["managers"])
    c4.metric("Total listings", stats["total_listings"])
    c5.metric("Adoption rate", f"{stats['adoption_rate']:.1f}%")

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Active listings", stats["active_listings"])
    c7.metric("Adopted", stats["adopted_listings"])
    c8.metric("Messages sent", stats["total_messages"])
    c9.metric("Watchlist saves", stats["total_watchlist"])
    avg_sat = stats["avg_satisfaction"]
    c10.metric("Avg satisfaction", f"{avg_sat:.2f}/5" if avg_sat else "—")

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_overview, tab_users, tab_listings, tab_surveys, tab_events = st.tabs([
        "📈 Growth", "👥 Users", "🐾 Listings", "⭐ Surveys", "📋 Events",
    ])

    # ── Growth tab ────────────────────────────────────────────────────────────
    with tab_overview:
        col_reg, col_lst = st.columns(2)

        with col_reg:
            reg_data = stats["registrations_by_month"]
            if reg_data:
                df_reg = pd.DataFrame(reg_data)
                fig = go.Figure(go.Bar(
                    x=df_reg["month"], y=df_reg["cnt"],
                    marker_color=COLOR_PRIMARY,
                    text=df_reg["cnt"], textposition="outside",
                ))
                fig.update_layout(
                    title="User registrations per month",
                    height=300, xaxis_title="Month", yaxis_title="New users",
                    margin=dict(t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No registration data yet.")

        with col_lst:
            lst_data = stats["listings_by_month"]
            if lst_data:
                df_lst = pd.DataFrame(lst_data)
                fig2 = go.Figure(go.Bar(
                    x=df_lst["month"], y=df_lst["cnt"],
                    marker_color=COLOR_PRIMARY_LIGHT,
                    text=df_lst["cnt"], textposition="outside",
                ))
                fig2.update_layout(
                    title="Listings created per month",
                    height=300, xaxis_title="Month", yaxis_title="New listings",
                    margin=dict(t=40, b=20),
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No listing data yet.")

        # Role distribution donut
        role_fig = go.Figure(go.Pie(
            labels=["Adopters", "Shelter Managers"],
            values=[stats["households"], stats["managers"]],
            hole=0.5,
            marker_colors=[COLOR_PRIMARY, COLOR_PRIMARY_LIGHT],
        ))
        role_fig.update_layout(title="User role distribution", height=260, margin=dict(t=40, b=0))
        st.plotly_chart(role_fig, use_container_width=True)

    # ── Users tab ─────────────────────────────────────────────────────────────
    with tab_users:
        all_users = db.get_all_users()
        if all_users:
            df_users = pd.DataFrame(all_users)
            df_users = df_users.rename(columns={
                "id": "ID", "username": "Username", "email": "Email",
                "role": "Role", "shelter_name": "Shelter name",
                "country": "Country", "city": "City",
                "action_count": "Actions", "created_at": "Joined",
            })
            df_users["Joined"] = df_users["Joined"].str[:10]
            st.dataframe(
                df_users[["ID", "Username", "Email", "Role", "Shelter name",
                           "City", "Country", "Actions", "Joined"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No users yet.")

        st.markdown(
            f'<p style="font-size:12px;color:{COLOR_TEXT_MUTED};">'
            f'Admin account is not shown in this table.</p>',
            unsafe_allow_html=True,
        )

    # ── Listings tab ──────────────────────────────────────────────────────────
    with tab_listings:
        conn = db.get_conn()
        all_listings = conn.execute(
            """SELECT l.id, l.pet_name, l.type, l.status, l.fee,
                      l.adoption_speed_pred, l.photo_amt, l.created_at,
                      u.shelter_name, u.username AS shelter_username
               FROM listings l JOIN users u ON l.shelter_id = u.id
               ORDER BY l.created_at DESC"""
        ).fetchall()
        conn.close()

        if all_listings:
            from frontend.utils.matching_platform import TYPE_MAP, ADOPTION_SPEED_LABELS
            rows = []
            for r in all_listings:
                r = dict(r)
                spd = r.get("adoption_speed_pred")
                rows.append({
                    "ID": r["id"],
                    "Pet name": r["pet_name"],
                    "Type": TYPE_MAP.get(r.get("type", 1), "?"),
                    "Status": r["status"].title(),
                    "Speed pred": ADOPTION_SPEED_LABELS.get(spd, "—") if spd is not None else "—",
                    "Fee (€)": r.get("fee") or 0,
                    "Photos": r.get("photo_amt") or 0,
                    "Shelter": r.get("shelter_name") or r.get("shelter_username", "?"),
                    "Created": r["created_at"][:10],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No listings yet.")

    # ── Surveys tab ───────────────────────────────────────────────────────────
    with tab_surveys:
        surveys = db.get_all_surveys()
        if surveys:
            df_surv = pd.DataFrame(surveys)

            # Score distribution chart
            score_dist = stats["survey_score_dist"]
            if score_dist:
                fig_sc = go.Figure(go.Bar(
                    x=[f"{'⭐'*k}" for k in sorted(score_dist)],
                    y=[score_dist[k] for k in sorted(score_dist)],
                    marker_color=COLOR_PRIMARY,
                    text=[score_dist[k] for k in sorted(score_dist)],
                    textposition="outside",
                ))
                fig_sc.update_layout(
                    title="User engagement survey scores",
                    height=260, yaxis_title="Responses",
                    margin=dict(t=40, b=20),
                )
                st.plotly_chart(fig_sc, use_container_width=True)

            df_display = df_surv[["username", "email", "threshold", "score", "comment", "created_at"]].copy()
            df_display.columns = ["Username", "Email", "At action #", "Score", "Comment", "Submitted"]
            df_display["Submitted"] = df_display["Submitted"].str[:16]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No engagement surveys submitted yet.")

        st.markdown("---")
        st.markdown("**Post-adoption surveys** (listing-level)")
        conn2 = db.get_conn()
        adopt_surveys = conn2.execute(
            """SELECT a.satisfaction_score, a.comment, a.created_at,
                      u.username AS adopter, l.pet_name
               FROM adoption_surveys a
               JOIN users u ON a.user_id = u.id
               JOIN listings l ON a.listing_id = l.id
               ORDER BY a.created_at DESC"""
        ).fetchall()
        conn2.close()
        if adopt_surveys:
            df_as = pd.DataFrame([dict(r) for r in adopt_surveys])
            df_as.columns = ["Score", "Comment", "Submitted", "Adopter", "Pet"]
            df_as["Submitted"] = df_as["Submitted"].str[:16]
            st.dataframe(df_as[["Adopter", "Pet", "Score", "Comment", "Submitted"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("No post-adoption surveys yet.")

    # ── Events tab ────────────────────────────────────────────────────────────
    with tab_events:
        events = db.get_recent_events(limit=60)
        if events:
            for ev in events:
                icon = "💬" if ev["event_type"] == "message" else "❤️"
                ts = str(ev["created_at"])[:16]
                st.markdown(
                    f'<div style="border-left:3px solid {COLOR_BORDER};'
                    f'padding:6px 12px;margin-bottom:6px;border-radius:4px;">'
                    f'{icon} <strong>{ev["actor"]}</strong> → <strong>{ev["target"]}</strong>'
                    f'<span style="color:{COLOR_TEXT_MUTED};font-size:12px;margin-left:8px;">'
                    f'{ev["detail"]}</span>'
                    f'<div style="font-size:11px;color:{COLOR_TEXT_MUTED};">{ts}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No events recorded yet.")

    # ── Password change section ───────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🔑 Change Admin Password"):
        with st.form("admin_pw_form"):
            cur_pw = st.text_input("Current password", type="password", key="adm_cur_pw")
            new_pw = st.text_input("New password (min 6 chars)", type="password", key="adm_new_pw")
            new_pw2 = st.text_input("Confirm new password", type="password", key="adm_new_pw2")
            submitted = st.form_submit_button("Change password", type="primary")
        if submitted:
            if new_pw != new_pw2:
                st.error("Passwords do not match.")
            else:
                ok, msg = auth.change_password(user["id"], cur_pw, new_pw)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
