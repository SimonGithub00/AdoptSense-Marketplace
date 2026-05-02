"""
Legacy internal tools — Batch CSV upload and Single Pet form.

These are extracted verbatim from Simon's original app.py so shelter staff
can still use them for quick ad-hoc predictions outside the marketplace
flow. They are accessible through the "Tools" nav item (managers only).

No changes to prediction or recommendation logic — only the surrounding
markup uses our brand palette indirectly via the global CSS in styles.py.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.utils.predictions import AdoptionPredictor, make_prediction
from frontend.utils.recommendations import get_adoption_factors, get_description_sentiment


COLOR_MAP_TOOLS = {
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


def show_csv_upload():
    """Batch CSV upload tool — predict adoption speeds for many pets at once."""
    st.markdown("Upload a CSV with multiple pets to get predictions for all of them.")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("**Required columns:** Type, Name, Age, Breed1, Breed2, Gender, "
                "Color1, Color2, Color3, MaturitySize, FurLength, Vaccinated, "
                "Dewormed, Sterilized, Health, Quantity, Fee, State, VideoAmt, "
                "PhotoAmt, Description")
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
        st.download_button("⬇️ Download Sample CSV",
                           sample.to_csv(index=False),
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
                with st.spinner("Analysing pets…"):
                    results = make_prediction(df)

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
                    names = [p["original_data"].get("Name", f"Pet {p['pet_index']+1}")
                             for p in sorted_preds]
                    speeds = [p["prediction"] for p in sorted_preds]
                    fig = go.Figure(go.Bar(
                        x=names, y=speeds,
                        text=[f"Speed {s}" for s in speeds], textposition="auto",
                        marker=dict(color=speeds, colorscale="RdYlGn_r", showscale=True),
                    ))
                    fig.update_layout(
                        title="Adoption Speed Ranking (lower = better)",
                        xaxis_title="Pet", yaxis_title="Speed (0=fast, 4=slow)",
                        height=400,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"Prediction failed: {results.get('error')}")
        except Exception as e:
            st.error(f"Error: {e}")


def show_manual_form():
    """Single Pet form — predict speed for one pet manually."""
    st.markdown("Analyse one pet at a time — get adoption speed prediction "
                "and recommendations.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    c_opts_prim = list(COLOR_MAP_TOOLS.keys())
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
                                     format_func=lambda x: {0: "N/A", 1: "Small", 2: "Medium",
                                                             3: "Large", 4: "XL"}[x])
        fur_length = st.selectbox("Fur Length", [0, 1, 2, 3], key="spf_fur",
                                  format_func=lambda x: {0: "N/A", 1: "Short", 2: "Medium",
                                                          3: "Long"}[x])
        color1 = st.selectbox("Primary Color", c_opts_prim, key="spf_col1",
                              format_func=lambda x: COLOR_MAP_TOOLS[x])
        color2 = st.selectbox("Secondary Color", c_opts_opt, key="spf_col2",
                              format_func=lambda x: "None" if x == 0 else COLOR_MAP_TOOLS[x])
        color3 = st.selectbox("Tertiary Color", c_opts_opt, key="spf_col3",
                              format_func=lambda x: "None" if x == 0 else COLOR_MAP_TOOLS[x])

    with col2:
        st.subheader("Health & Care")
        health = st.selectbox("Health", [1, 2, 3], key="spf_health",
                              format_func=lambda x: {1: "Healthy", 2: "Minor Injury",
                                                      3: "Serious Injury"}[x])
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
    breed_opts = [(bid, bname) for bid, btype, bname in BREED_DATA_FULL
                  if btype == pet_type]
    breed_ids = [b[0] for b in breed_opts]
    breed_names = [b[1] for b in breed_opts]
    bc1, bc2 = st.columns(2)
    with bc1:
        b1_name = st.selectbox("Primary Breed", breed_names,
                               key=f"spf_breed1_{pet_type}")
        breed1 = breed_ids[breed_names.index(b1_name)] if b1_name in breed_names else breed_ids[0]
    with bc2:
        b2_name = st.selectbox("Secondary Breed (optional)", ["None"] + breed_names,
                               key=f"spf_breed2_{pet_type}")
        breed2 = (0 if b2_name == "None"
                  else (breed_ids[breed_names.index(b2_name)] if b2_name in breed_names else 0))

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

        with st.spinner("Analysing…"):
            results = make_prediction(pet_df)

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
