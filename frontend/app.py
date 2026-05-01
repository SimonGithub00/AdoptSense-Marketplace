"""
AdoptSense Pet Adoption Prediction — Streamlit frontend
Two personas: Shelter Managers (create & manage listings) and
Private Households (browse, watchlist, message shelters).
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.utils import auth, db
from frontend.utils.predictions import AdoptionPredictor, make_prediction
from frontend.utils.recommendations import get_adoption_factors, get_description_sentiment
from frontend.utils.matching_platform_ui import show_matching_platform
from frontend.utils.seed_data import seed_if_needed, backfill_predictions

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AdoptSense",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main { padding: 0rem 1rem; }
.stTabs [data-baseweb="tab-list"] button { font-size: 1.05em; padding: 0.5rem 1rem; }
.predict-card {
    background: linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    color:white; padding:1.5rem; border-radius:10px; margin:1rem 0;
}
.loading-container {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:2rem; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    border-radius:15px; color:white; text-align:center;
}
.loading-paws { font-size:3em; animation:bounce 1.5s ease-in-out infinite; display:inline-block; }
.loading-text { font-size:1.2em; font-weight:600; margin-top:1rem; animation:pulse 1.5s ease-in-out infinite; }
@keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-20px)} }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
</style>
""", unsafe_allow_html=True)


# ── Bootstrap ──────────────────────────────────────────────────────────────────

db.init_db()
seed_if_needed()
backfill_predictions()


# ── Auth overlay ───────────────────────────────────────────────────────────────

def _render_auth_overlay():
    """Show login or register form overlaid on the page."""
    mode = st.session_state.get("show_auth", "")
    if mode not in ("login", "register"):
        return

    st.markdown("---")
    if mode == "login":
        st.subheader("🔑 Log In")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button("Log In", type="primary")
            if col2.form_submit_button("Cancel"):
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
        st.caption("No account? ")
        if st.button("Register instead"):
            st.session_state.show_auth = "register"
            st.rerun()

    else:  # register
        st.subheader("📝 Create Account")
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            role = st.selectbox(
                "I am a…",
                options=["household", "shelter_manager"],
                format_func=lambda x: "🏠 Private Household (adopter)" if x == "household"
                else "🏥 Shelter Manager",
            )
            shelter_name = ""
            if role == "shelter_manager":
                shelter_name = st.text_input("Shelter / Organisation name")
            password = st.text_input("Password (min 6 chars)", type="password")
            password2 = st.text_input("Confirm password", type="password")
            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button("Register", type="primary")
            if col2.form_submit_button("Cancel"):
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
                    auth.login(username, password)
                    st.session_state.pop("show_auth", None)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        st.caption("Already have an account? ")
        if st.button("Log in instead"):
            st.session_state.show_auth = "login"
            st.rerun()

    st.markdown("---")


# ── Sidebar header ──────────────────────────────────────────────────────────────

def _render_sidebar_auth():
    user = auth.current_user()
    with st.sidebar:
        st.markdown("## 🐾 AdoptSense")
        if user:
            role_label = "🏥 Shelter Manager" if user.get("role") == "shelter_manager" else "🏠 Household"
            name = user.get("shelter_name") or user["username"]
            st.markdown(f"**{role_label}**  \n{name}")
            if st.button("Log Out", use_container_width=True):
                auth.logout()
                st.rerun()
        else:
            st.caption("Browse pets freely — log in for more features.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔑 Log In", use_container_width=True):
                    st.session_state.show_auth = "login"
                    st.rerun()
            with c2:
                if st.button("📝 Register", use_container_width=True):
                    st.session_state.show_auth = "register"
                    st.rerun()
        st.markdown("---")


# ── Tab: Home ──────────────────────────────────────────────────────────────────

def show_home():
    st.markdown("""
## Welcome to AdoptSense 👋

**AdoptSense** is an AI-powered pet adoption platform combining XGBoost adoption speed prediction
with a two-sided marketplace — connecting animal shelters with loving households.

### How it works

| Role | What you can do |
|------|-----------------|
| 🏥 **Shelter Manager** | Create listings, upload photos, AI-improve descriptions, track KPIs, chat with adopters |
| 🏠 **Private Household** | Browse pets, filter by characteristics, save to watchlist, message shelters |

### Adoption Speed Categories
""")

    cols = st.columns(5)
    info = [
        ("Speed 0", "⭐⭐⭐⭐⭐", "Same Day", "#4CAF50"),
        ("Speed 1", "⭐⭐⭐⭐", "1–7 Days", "#8BC34A"),
        ("Speed 2", "⭐⭐⭐", "8–30 Days", "#FFC107"),
        ("Speed 3", "⭐⭐", "31–90 Days", "#FF9800"),
        ("Speed 4", "⭐", "No Adoption", "#F44336"),
    ]
    for col, (label, emoji, caption, color) in zip(cols, info):
        with col:
            st.markdown(
                f"<div style='background:{color};color:white;padding:0.75rem;"
                f"border-radius:8px;text-align:center;'>"
                f"<b>{label}</b><br>{emoji}<br><small>{caption}</small></div>",
                unsafe_allow_html=True,
            )

    st.markdown("""
---
### Getting Started

- **Shelter managers**: Register → Create listings with AI prediction and photo enhancement
- **Households**: Browse pets freely or register to save favourites and message shelters
- **Batch predictions**: Use the **Batch Upload** tab to predict adoption speeds for a CSV of pets
""")


# ── Tab: CSV Upload ────────────────────────────────────────────────────────────

def show_csv_upload():
    st.header("📁 Batch Upload (CSV)")
    st.markdown("Upload a CSV with multiple pets to get predictions for all of them.")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("""**Required columns:** Type, Name, Age, Breed1, Breed2, Gender, Color1, Color2,
Color3, MaturitySize, FurLength, Vaccinated, Dewormed, Sterilized, Health,
Quantity, Fee, State, VideoAmt, PhotoAmt, Description""")
    with col2:
        sample = pd.DataFrame({
            "Type": [2, 1], "Name": ["Fluffy", "Rex"], "Age": [12, 36],
            "Breed1": [265, 307], "Breed2": [0, 0], "Gender": [1, 1],
            "Color1": [6, 2], "Color2": [7, 0], "Color3": [0, 0],
            "MaturitySize": [2, 3], "FurLength": [2, 1],
            "Vaccinated": [1, 1], "Dewormed": [1, 1], "Sterilized": [1, 2],
            "Health": [1, 1], "Quantity": [1, 2], "Fee": [100, 0],
            "State": [41326, 41326], "PhotoAmt": [3, 2], "VideoAmt": [0, 0],
            "Description": ["Friendly kitten looking for a home.", "Energetic dogs."],
        })
        st.download_button("⬇️ Download Sample CSV", sample.to_csv(index=False),
                           "sample_pets.csv", "text/csv")

    st.markdown("---")
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="csv_upload")

    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.success(f"✅ {len(df)} pets loaded.")
            with st.expander("Preview"):
                st.dataframe(df.head(10), use_container_width=True)

            if st.button("🚀 Run Predictions", type="primary", key="csv_predict"):
                placeholder = st.empty()
                with placeholder.container():
                    st.markdown(
                        '<div class="loading-container">'
                        '<div class="loading-paws">🐾</div>'
                        '<div class="loading-text">Analysing Pets…</div>'
                        '<p>XGBoost model processing…</p></div>',
                        unsafe_allow_html=True,
                    )
                results = make_prediction(df)
                placeholder.empty()

                if results["success"]:
                    preds = results["predictions"]
                    st.markdown("## 📊 Results")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total", len(preds))
                    avg_conf = sum(p["confidence"] for p in preds) / len(preds)
                    c2.metric("Avg Confidence", f"{avg_conf*100:.1f}%")
                    c3.metric("Fast (0–1)", sum(1 for p in preds if p["prediction"] <= 1))
                    c4.metric("Slow (3–4)", sum(1 for p in preds if p["prediction"] >= 3))

                    rows = [
                        {
                            "Pet": p["original_data"].get("Name", f"Pet {p['pet_index']+1}"),
                            "Speed": p["prediction_emoji"],
                            "Category": p["prediction_label"],
                            "Confidence": f"{p['confidence']*100:.1f}%",
                        }
                        for p in preds
                    ]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

                    sorted_preds = sorted(preds, key=lambda x: x["prediction"])
                    names = [p["original_data"].get("Name", f"Pet {p['pet_index']+1}") for p in sorted_preds]
                    speeds = [p["prediction"] for p in sorted_preds]
                    fig = go.Figure(go.Bar(
                        x=names, y=speeds,
                        text=[f"Speed {s}" for s in speeds], textposition="auto",
                        marker=dict(color=speeds, colorscale="RdYlGn_r", showscale=True),
                    ))
                    fig.update_layout(title="Adoption Speed Ranking (lower = better)",
                                      xaxis_title="Pet", yaxis_title="Speed (0=fast, 4=slow)",
                                      height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"Prediction failed: {results.get('error')}")
        except Exception as e:
            st.error(f"Error: {e}")


# ── Tab: Single Pet Form ───────────────────────────────────────────────────────

COLOR_MAP = {
    1: "Black", 2: "Brown", 3: "Golden", 4: "Yellow",
    5: "Cream", 6: "Gray", 7: "White",
}
BREED_DATA_FULL = [
    (1, 1, "Affenpinscher"), (20, 1, "Beagle"), (44, 1, "Boxer"), (60, 1, "Chihuahua"),
    (65, 1, "Chow Chow"), (75, 1, "Dachshund"), (76, 1, "Dalmatian"),
    (78, 1, "Doberman Pinscher"), (82, 1, "English Bulldog"), (100, 1, "French Bulldog"),
    (103, 1, "German Shepherd Dog"), (109, 1, "Golden Retriever"), (111, 1, "Great Dane"),
    (119, 1, "Husky"), (141, 1, "Labrador Retriever"), (147, 1, "Maltese"),
    (178, 1, "Pomeranian"), (179, 1, "Poodle"), (182, 1, "Pug"), (189, 1, "Rottweiler"),
    (205, 1, "Shih Tzu"), (206, 1, "Siberian Husky"), (240, 1, "Yorkshire Terrier"),
    (307, 1, "Mixed Breed"),
    (265, 2, "Domestic Medium Hair"), (266, 2, "Domestic Short Hair"),
    (264, 2, "Domestic Long Hair"), (285, 2, "Persian"), (292, 2, "Siamese"),
    (247, 2, "Bengal"), (251, 2, "British Shorthair"), (276, 2, "Maine Coon"),
    (288, 2, "Ragdoll"), (289, 2, "Russian Blue"), (299, 2, "Tabby"), (306, 2, "Tuxedo"),
]


def show_manual_form():
    st.header("📝 Single Pet Prediction")
    st.markdown("Analyse one pet at a time — get adoption speed prediction and recommendations.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    c_opts_prim = list(COLOR_MAP.keys())
    c_opts_opt = [0] + c_opts_prim

    with col1:
        st.subheader("Basic Info")
        pet_type = st.selectbox("Pet Type", [1, 2], key="spf_type",
                                format_func=lambda x: "🐶 Dog" if x == 1 else "🐱 Cat")
        name = st.text_input("Pet Name (optional)", key="spf_name")
        age = st.slider("Age (months)", 0, 120, 12, key="spf_age")
        gender = st.selectbox("Gender", [1, 2, 3], key="spf_gender",
                              format_func=lambda x: {1: "Male", 2: "Female", 3: "Mixed"}[x])

        st.subheader("Physical")
        maturity_size = st.selectbox("Maturity Size", [0, 1, 2, 3, 4], key="spf_size",
                                     format_func=lambda x: {0: "N/A", 1: "Small", 2: "Medium", 3: "Large", 4: "XL"}[x])
        fur_length = st.selectbox("Fur Length", [0, 1, 2, 3], key="spf_fur",
                                  format_func=lambda x: {0: "N/A", 1: "Short", 2: "Medium", 3: "Long"}[x])
        color1 = st.selectbox("Primary Color", c_opts_prim, key="spf_col1",
                              format_func=lambda x: COLOR_MAP[x])
        color2 = st.selectbox("Secondary Color", c_opts_opt, key="spf_col2",
                              format_func=lambda x: "None" if x == 0 else COLOR_MAP[x])
        color3 = st.selectbox("Tertiary Color", c_opts_opt, key="spf_col3",
                              format_func=lambda x: "None" if x == 0 else COLOR_MAP[x])

    with col2:
        st.subheader("Health & Care")
        health = st.selectbox("Health", [1, 2, 3], key="spf_health",
                              format_func=lambda x: {1: "Healthy", 2: "Minor Injury", 3: "Serious Injury"}[x])
        vaccinated = st.selectbox("Vaccinated", [1, 2, 3], key="spf_vacc",
                                  format_func=lambda x: {1: "Yes", 2: "No", 3: "Not Sure"}[x])
        dewormed = st.selectbox("Dewormed", [1, 2, 3], key="spf_dew",
                                format_func=lambda x: {1: "Yes", 2: "No", 3: "Not Sure"}[x])
        sterilized = st.selectbox("Sterilized", [1, 2, 3], key="spf_ster",
                                  format_func=lambda x: {1: "Yes", 2: "No", 3: "Not Sure"}[x])

        st.subheader("Listing")
        fee = st.number_input("Adoption Fee", 0, 5000, 100, key="spf_fee")
        quantity = st.number_input("Number of Pets", 1, 20, 1, key="spf_qty")
        state = st.number_input("State ID", 0, 99999, 41326, key="spf_state")

    st.markdown("---")
    st.subheader("Media & Description")
    mc1, mc2 = st.columns(2)
    with mc1:
        photo_amt = st.number_input("Number of Photos", 0, 50, 3, key="spf_photo_amt")
        video_amt = st.number_input("Number of Videos", 0, 10, 0, key="spf_video_amt")
    with mc2:
        st.info("📌 Photos are the #1 driver of adoption speed.")

    description = st.text_area(
        "Pet Description", height=150, key="spf_desc",
        placeholder="Describe personality, history, characteristics… (50+ words recommended)",
    )

    st.markdown("---")
    breed_opts = [(bid, bname) for bid, btype, bname in BREED_DATA_FULL if btype == pet_type]
    breed_ids = [b[0] for b in breed_opts]
    breed_names = [b[1] for b in breed_opts]
    bc1, bc2 = st.columns(2)
    with bc1:
        b1_name = st.selectbox("Primary Breed", breed_names, key=f"spf_breed1_{pet_type}")
        breed1 = breed_ids[breed_names.index(b1_name)] if b1_name in breed_names else breed_ids[0]
    with bc2:
        b2_name = st.selectbox("Secondary Breed (optional)", ["None"] + breed_names, key=f"spf_breed2_{pet_type}")
        breed2 = 0 if b2_name == "None" else (breed_ids[breed_names.index(b2_name)] if b2_name in breed_names else 0)

    st.markdown("---")
    if st.button("🚀 Predict", type="primary", key="spf_predict"):
        pet_df = pd.DataFrame([{
            "Type": pet_type, "Name": name or None, "Age": age,
            "Breed1": breed1, "Breed2": breed2, "Gender": gender,
            "Color1": color1, "Color2": color2, "Color3": color3,
            "MaturitySize": maturity_size, "FurLength": fur_length,
            "Vaccinated": vaccinated, "Dewormed": dewormed, "Sterilized": sterilized,
            "Health": health, "Quantity": quantity, "Fee": fee, "State": state,
            "PhotoAmt": photo_amt, "VideoAmt": video_amt, "Description": description,
        }])

        ph = st.empty()
        with ph.container():
            st.markdown(
                '<div class="loading-container">'
                '<div class="loading-paws">🐾</div>'
                '<div class="loading-text">Analysing…</div>'
                '<p>XGBoost processing…</p></div>',
                unsafe_allow_html=True,
            )
        results = make_prediction(pet_df)
        ph.empty()

        if results["success"]:
            pred = results["predictions"][0]
            st.markdown("## 🎯 Prediction")
            pc1, pc2, pc3 = st.columns([1, 2, 1])
            with pc2:
                st.markdown(
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:3rem;'>{pred['prediction_emoji']}</div>"
                    f"<h3>{pred['prediction_label'].upper()}</h3>"
                    f"<p><b>Confidence:</b> {pred['confidence']*100:.1f}%</p></div>",
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            st.markdown("### Probability Breakdown")
            probs = pred["probabilities"]
            prob_df = pd.DataFrame({
                "Speed": [AdoptionPredictor.ADOPTION_SPEED_LABELS[i] for i in range(5)],
                "Emoji": [AdoptionPredictor.ADOPTION_SPEED_EMOJI[i] for i in range(5)],
                "Probability": [f"{probs[i]*100:.1f}%" for i in range(5)],
            })
            st.dataframe(prob_df, use_container_width=True, hide_index=True)

            fig = go.Figure(go.Bar(
                x=[f"Speed {i}" for i in range(5)],
                y=[probs[i]*100 for i in range(5)],
                text=[f"{probs[i]*100:.1f}%" for i in range(5)],
                textposition="auto",
                marker=dict(color=[probs[i]*100 for i in range(5)],
                            colorscale="RdYlGn_r", showscale=False),
            ))
            fig.update_layout(title="Adoption Speed Probability", height=350,
                              xaxis_title="Speed Category", yaxis_title="Probability (%)")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown("### Sentiment Analysis")
            sentiment = get_description_sentiment(pred["original_data"].get("Description", ""))
            tone_colors = {"success": "#2e7d32", "info": "#1565c0",
                           "warning": "#e65100", "error": "#b71c1c"}
            tone_hex = tone_colors[sentiment["tone_color"]]
            st.markdown(
                f"<span style='color:{tone_hex};font-weight:600;'>"
                f"{sentiment['tone']} | Score: {sentiment['compound']:+.2f}</span>",
                unsafe_allow_html=True,
            )
            st.info(sentiment["advice"])

            st.markdown("---")
            st.markdown("### Adoption Factor Analysis")
            pos_f, neg_f = get_adoption_factors(pred["original_data"])
            af1, af2 = st.columns(2)
            with af1:
                st.markdown("**Top Factors Helping Adoption**")
                for i, f in enumerate(pos_f, 1):
                    with st.container(border=True):
                        st.markdown(f"**{i}. {f['label']}**")
                        st.caption(f["sentence"])
                if not pos_f:
                    st.info("No strong positive factors identified.")
            with af2:
                st.markdown("**Top Factors Hindering Adoption**")
                for i, f in enumerate(neg_f, 1):
                    with st.container(border=True):
                        st.markdown(f"**{i}. {f['label']}**")
                        st.caption(f["sentence"])
                if not neg_f:
                    st.success("No significant hindering factors — great profile!")
        else:
            st.error(f"Prediction failed: {results.get('error')}")


# ── Tab: About ─────────────────────────────────────────────────────────────────

def show_about():
    st.header("ℹ️ About AdoptSense")
    st.markdown("""
## Mission

**AdoptSense** accelerates pet adoptions by combining machine learning predictions with a
structured marketplace — giving shelters actionable insights and households a simple way to
find their next companion.

## Two Personas

| Persona | Role | Key Features |
|---------|------|--------------|
| 🏥 **Shelter Manager** | Lists pets, tracks performance | Create listings, AI descriptions, studio photos, KPI dashboard, chat |
| 🏠 **Private Household** | Adopts pets | Browse with filters, watchlist, message shelters |

## AI Model: XGBoost Classifier

- **Task:** Multi-class adoption speed prediction (5 classes: 0–4)
- **Training data:** 14,993 pet listings from Petfinder.my (Malaysia)
- **Features:** 27 tabular + 4 VADER sentiment = 31 features at inference
- **Validation accuracy:** 39.31% | **Weighted F1:** 0.3809

## Top 5 Feature Importances

| # | Feature | Importance |
|---|---------|------------|
| 1 | has_photo | 0.1290 |
| 2 | Sterilized | 0.0501 |
| 3 | age_bin | 0.0422 |
| 4 | Age | 0.0392 |
| 5 | photo_bin | 0.0389 |

## Sentiment Analysis

Pet descriptions are scored using **VADER** (Valence Aware Dictionary and sEntiment Reasoner),
an offline lexicon-based model. The four VADER scores (compound, positive, negative, neutral)
are features in the XGBoost model and are also displayed to shelter managers as actionable feedback.

## AI Features (Gemini)

- **Description improvement:** Gemini Flash rewrites raw descriptions into a 4–8 sentence,
  positive, adoption-optimised format using the pet's characteristics and photo.
- **Studio-ready photos:** Background removal (rembg) + professional studio backdrop.
  Download as studio photo or transparent sticker for social media sharing.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| ML Model | XGBoost (scikit-learn pipeline) |
| Sentiment | NLTK VADER |
| AI Features | Google Gemini API |
| Background Removal | rembg |
| Frontend | Streamlit + Plotly |
| Database | SQLite |
| Auth | SHA-256 + salt |

## References

- Dataset: [PetFinder.my Kaggle Competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
- XGBoost, scikit-learn, NLTK VADER, Streamlit, Plotly, Google Gemini API
""")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    _render_sidebar_auth()

    if st.session_state.get("show_auth"):
        _render_auth_overlay()

    st.markdown("# 🐾 AdoptSense")
    st.caption("AI-powered pet adoption prediction & marketplace")

    user = auth.current_user()
    is_manager = bool(user and user.get("role") == "shelter_manager")

    if is_manager:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Home", "🐾 Marketplace", "📁 Batch Upload", "📝 Single Pet", "ℹ️ About",
        ])
        with tab1:
            show_home()
        with tab2:
            show_matching_platform()
        with tab3:
            show_csv_upload()
        with tab4:
            show_manual_form()
        with tab5:
            show_about()
    else:
        tab1, tab2, tab3 = st.tabs(["📊 Home", "🐾 Marketplace", "ℹ️ About"])
        with tab1:
            show_home()
        with tab2:
            show_matching_platform()
        with tab3:
            show_about()


if __name__ == "__main__":
    main()
