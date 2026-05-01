"""
AdoptSense Pet Adoption Prediction - Frontend UI
Main Streamlit application
"""
import sys
from pathlib import Path

# Setup paths before local imports so that the `frontend` package is
# discoverable regardless of whether the app is launched from the project
# root or from inside the frontend/ directory.
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.utils.predictions import AdoptionPredictor, make_prediction
from frontend.utils.recommendations import get_adoption_factors, get_description_sentiment
from frontend.utils.matching_platform_ui import show_matching_platform

# Page configuration
st.set_page_config(
    page_title="AdoptSense - Pet Adoption Predictor",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with animations and beautiful styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .css-1d6bido {
        padding: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1.1em;
        padding: 0.5rem 1rem;
    }
    .streamlit-expanderHeader {
        font-size: 1.1em;
        font-weight: 600;
    }
    .predict-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* Loading animation */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-20px); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .loading-spinner {
        display: inline-block;
        width: 60px;
        height: 60px;
        animation: spin 2s linear infinite;
    }
    
    .loading-paws {
        font-size: 3em;
        animation: bounce 1.5s ease-in-out infinite;
        display: inline-block;
    }
    
    .loading-text {
        font-size: 1.2em;
        font-weight: 600;
        margin-top: 1rem;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    
    .model-badge {
        display: inline-block;
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9em;
        margin: 0.5rem 0.25rem;
        font-weight: 600;
    }
    
    .success-card {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    """Main application entry point."""

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🐾 AdoptSense")
        st.markdown("### Pet Adoption Speed Predictor")
    with col2:
        pass

    st.markdown("---")

    # Navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Home",
        "📁 Batch Upload (CSV)",
        "📝 Single Pet Form",
        "🤝 Marketplace",
        "ℹ️ About"
    ])

    with tab1:
        show_home()

    with tab2:
        show_csv_upload()

    with tab3:
        show_manual_form()

    with tab4:
        show_matching_platform()

    with tab5:
        show_about()


def show_home():
    """Display home/landing page."""

    st.markdown("""
    ## Welcome to AdoptSense 👋

    **AdoptSense** is an AI-powered pet adoption speed predictor powered by advanced machine learning.
    The model analyzes 27 key pet characteristics to forecast adoption timelines and provide data-driven
    recommendations to help pets find loving homes faster.

    ### Who is this for?

    - 🏥 **Animal Shelters & Rescue Organizations** - Optimize listings and identify at-risk pets early
    - 👨‍👩‍👧 **Pet Owners** - Understand adoption prospects before rehoming
    - 💼 **Pet Adoption Businesses** - Data-driven strategy for better outcomes

    ### How it Works

    1. **Input Pet Data** - Upload a CSV with multiple pets or fill a form for a single pet
    2. **AI Analysis** - XGBoost analyzes 27 tabular + sentiment features
    3. **Get Predictions** - Adoption speed forecast with class probabilities
    4. **Actionable Recommendations** - Specific, prioritized improvement suggestions
    5. **Visualizations** - See rankings and sentiment analysis (for batch uploads)

    ### Key Features

    - ⚡ **Real-time Predictions** - Instant adoption speed forecasts
    - 📊 **Comparative Analysis** - Compare multiple pets side-by-side
    - 🎯 **Targeted Recommendations** - Prioritized improvement suggestions based on feature importance
    - 📈 **Performance Ranking** - Visualize relative adoption potential
    - 💭 **Sentiment Analysis** - Description tone analysis (VADER sentiment)
    - 📱 **User-Friendly Interface** - No coding required

    ### Adoption Speed Categories

    """)

    # Display adoption speed info
    col1, col2, col3, col4, col5 = st.columns(5)

    speed_info = [
        ("⭐⭐⭐⭐⭐", "Same Day", "Exceptional appeal"),
        ("⭐⭐⭐⭐", "1-7 Days", "Strong demand"),
        ("⭐⭐⭐", "8-30 Days", "Moderate appeal"),
        ("⭐⭐", "31-90 Days", "Needs improvement"),
        ("⭐", "No Adoption", "Critical intervention")
    ]

    with col1:
        with st.container(border=True):
            st.markdown("**Speed 0**")
            st.markdown(speed_info[0][0])
            st.caption(speed_info[0][1])

    with col2:
        with st.container(border=True):
            st.markdown("**Speed 1**")
            st.markdown(speed_info[1][0])
            st.caption(speed_info[1][1])

    with col3:
        with st.container(border=True):
            st.markdown("**Speed 2**")
            st.markdown(speed_info[2][0])
            st.caption(speed_info[2][1])

    with col4:
        with st.container(border=True):
            st.markdown("**Speed 3**")
            st.markdown(speed_info[3][0])
            st.caption(speed_info[3][1])

    with col5:
        with st.container(border=True):
            st.markdown("**Speed 4**")
            st.markdown(speed_info[4][0])
            st.caption(speed_info[4][1])

    st.markdown("---")

    st.markdown("""
    ### Get Started

    Choose one of the options above to start:

    - **Single Pet**: Fill in the form to analyze one pet at a time
    - **Batch Upload**: Upload a CSV file with multiple pets for comparative analysis

    """)


def show_csv_upload():
    """Display CSV upload page."""

    st.header("📁 Batch Upload (CSV)")

    st.markdown("""
    Upload a CSV file with multiple pets to get predictions and rankings for all of them.
    """)

    # Download template
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### CSV Format")
        st.info("""
        Your CSV file should include these columns:
        - **Type** (1=Dog, 2=Cat)
        - **Name** (pet name, optional)
        - **Age** (in months)
        - **Breed1, Breed2** (breed IDs)
        - **Gender** (1=Male, 2=Female, 3=Mixed)
        - **Color1, Color2, Color3** (color IDs)
        - **MaturitySize** (0=N/A, 1=Small, 2=Medium, 3=Large, 4=XL)
        - **FurLength** (0=N/A, 1=Short, 2=Medium, 3=Long)
        - **Vaccinated, Dewormed, Sterilized** (1=Yes, 2=No, 3=Not Sure)
        - **Health** (1=Healthy, 2=Minor Injury, 3=Serious Injury)
        - **Quantity** (number of pets)
        - **Fee** (adoption fee)
        - **State** (state ID)
        - **VideoAmt** (number of videos, optional)
        - **PhotoAmt** (number of photos)
        - **Description** (pet description)
        """)

    with col2:
        st.markdown("### Sample File")
        sample_data = {
            'Type': [2, 2, 1],
            'Name': ['Fluffy', 'Whiskers', 'Rex'],
            'Age': [12, 24, 36],
            'Breed1': [265, 285, 307],
            'Breed2': [0, 264, 0],
            'Gender': [1, 2, 1],
            'Color1': [6, 2, 1],
            'Color2': [7, 4, 5],
            'Color3': [0, 7, 0],
            'MaturitySize': [2, 2, 3],
            'FurLength': [2, 3, 1],
            'Vaccinated': [1, 1, 1],
            'Dewormed': [1, 1, 1],
            'Sterilized': [1, 2, 1],
            'Health': [1, 1, 2],
            'Quantity': [1, 1, 2],
            'Fee': [100, 0, 200],
            'State': [41326, 41326, 41312],
            'PhotoAmt': [3, 1, 2],
            'VideoAmt': [0, 0, 1],
            'Description': ['Fluffy is a friendly kitten', 'Urban rescue cat', 'Energetic dogs'],
        }
        sample_df = pd.DataFrame(sample_data)
        st.download_button(
            label="⬇️ Download Sample CSV",
            data=sample_df.to_csv(index=False),
            file_name="sample_pets.csv",
            mime="text/csv"
        )

    st.markdown("---")

    # File uploader
    uploaded_file = st.file_uploader("Upload your CSV file", type=['csv'])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            st.success(f"✅ File uploaded successfully! ({len(df)} pets)")

            # Show preview
            with st.expander("📋 Preview Data"):
                st.dataframe(df.head(10), use_container_width=True)

            # Make predictions
            batch_predict_clicked = st.button("🚀 Run Predictions", key="batch_predict", type="primary")
            st.caption("⏳ Note: First run may take 1-2 minutes. Subsequent runs are faster.")
            if batch_predict_clicked:
                st.markdown("---")
                
                # Beautiful loading animation
                loading_placeholder = st.empty()
                with loading_placeholder.container():
                    st.markdown("""
                    <div class="loading-container">
                        <div class="loading-paws">🐾</div>
                        <div class="loading-text">Analyzing Pets...</div>
                        <p>The XGBoost model is evaluating adoption factors...</p>
                    </div>
                    """, unsafe_allow_html=True)

                results = make_prediction(df)
                loading_placeholder.empty()  # Clear loading animation

                if results['success']:
                    predictions = results['predictions']

                    # Display results
                    st.markdown("## 📊 Prediction Results")

                    # Summary stats
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Pets", len(predictions))
                    with col2:
                        avg_confidence = (
                            sum(p['confidence'] for p in predictions) / len(predictions)
                        )
                        st.metric("Avg Confidence", f"{avg_confidence*100:.1f}%")
                    with col3:
                        fast_adopt = len([p for p in predictions if p['prediction'] <= 1])
                        st.metric("Fast Adopters", fast_adopt)
                    with col4:
                        slow_adopt = len([p for p in predictions if p['prediction'] >= 3])
                        st.metric("Slow Adopters", slow_adopt)

                    st.markdown("---")

                    # Results table
                    results_data = []
                    for pred in predictions:
                        results_data.append({
                            'Pet': pred['original_data'].get('Name', f"Pet {pred['pet_index']+1}"),
                            'Adoption Speed': pred['prediction_emoji'],
                            'Category': pred['prediction_label'],
                            'Confidence': f"{pred['confidence']*100:.1f}%",
                        })

                    results_df = pd.DataFrame(results_data)
                    st.markdown("### Individual Predictions")
                    st.dataframe(results_df, use_container_width=True)

                    # Detailed results
                    st.markdown("### Detailed Recommendations")

                    for i, pred in enumerate(predictions):
                        pet_name = pred['original_data'].get('Name', f"Pet {i+1}")

                        expander_title = (
                            f"{pred['prediction_emoji']} {pet_name} - {pred['prediction_label']}"
                        )
                        with st.expander(expander_title, expanded=i == 0):
                            col1, col_sent, col2 = st.columns([1, 2, 1])

                            with col1:
                                st.markdown(f"**Confidence:** {pred['confidence']*100:.1f}%")

                            with col_sent:
                                sentiment = get_description_sentiment(
                                    pred['original_data'].get('Description', '')
                                )
                                tone_colors = {
                                    'success': '#2e7d32',
                                    'info':    '#1565c0',
                                    'warning': '#e65100',
                                    'error':   '#b71c1c',
                                }
                                tone_hex = tone_colors[sentiment['tone_color']]
                                pos_pct = sentiment['pos'] * 100
                                neu_pct = sentiment['neu'] * 100
                                neg_pct = sentiment['neg'] * 100
                                st.markdown(
                                    f"**Description Sentiment** — "
                                    f"<span style='color:{tone_hex}; font-weight:600;'>"
                                    f"{sentiment['tone']}  |  Score: {sentiment['compound']:+.2f}"
                                    f"</span>",
                                    unsafe_allow_html=True
                                )
                                bar_style = (
                                    "width:160px; height:13px; background:#e0e0e0;"
                                    " border-radius:3px; overflow:hidden; flex-shrink:0;"
                                )
                                st.markdown(f"""
<div style="font-size:13px; line-height:2;">
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="{bar_style}">
      <div style="width:{pos_pct:.0f}%; height:100%; background:#4CAF50;"></div>
    </div>
    <span style="color:#4CAF50; font-weight:600; min-width:70px;">Positive</span>
    <span>{pos_pct:.0f}%</span>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="{bar_style}">
      <div style="width:{neu_pct:.0f}%; height:100%; background:#90A4AE;"></div>
    </div>
    <span style="color:#607D8B; font-weight:600; min-width:70px;">Neutral</span>
    <span>{neu_pct:.0f}%</span>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="{bar_style}">
      <div style="width:{neg_pct:.0f}%; height:100%; background:#F44336;"></div>
    </div>
    <span style="color:#F44336; font-weight:600; min-width:70px;">Negative</span>
    <span>{neg_pct:.0f}%</span>
  </div>
</div>
""", unsafe_allow_html=True)
                                st.caption(sentiment['advice'])

                            with col2:
                                st.markdown("**Probability Breakdown:**")
                                for speed_id, prob in pred['probabilities'].items():
                                    label = AdoptionPredictor.ADOPTION_SPEED_LABELS[speed_id]
                                    st.caption(f"Speed {speed_id} ({label}): {prob*100:.1f}%")

                            st.markdown("---")

                            pos_factors, neg_factors = get_adoption_factors(pred['original_data'])

                            col_pos, col_neg = st.columns(2)

                            with col_pos:
                                st.markdown("**Top Factors *Helping* Adoption**")
                                if pos_factors:
                                    for j, f in enumerate(pos_factors, 1):
                                        with st.container(border=True):
                                            st.markdown(f"**{j}. {f['label']}**")
                                            st.caption(f['sentence'])
                                else:
                                    st.info("No strong positive factors identified.")

                            with col_neg:
                                st.markdown("**Top Factors *Hindering* Adoption**")
                                if neg_factors:
                                    for j, f in enumerate(neg_factors, 1):
                                        with st.container(border=True):
                                            st.markdown(f"**{j}. {f['label']}**")
                                            st.caption(f['sentence'])
                                else:
                                    st.success("No significant hindering factors found!")

                    # Visualization
                    st.markdown("---")
                    st.markdown("### 📈 Rankings & Visualization")

                    # Ranking bar chart
                    ranking_data = []
                    for pred in sorted(predictions, key=lambda x: x['prediction']):
                        pet_label = pred['original_data'].get(
                            'Name', f"Pet {pred['pet_index'] + 1}"
                        )
                        ranking_data.append({
                            'name': pet_label,
                            'speed': pred['prediction'],
                            'confidence': pred['confidence']
                        })

                    fig = go.Figure(data=[
                        go.Bar(
                            x=[d['name'] for d in ranking_data],
                            y=[d['speed'] for d in ranking_data],
                            text=[f"Speed {d['speed']}" for d in ranking_data],
                            textposition='auto',
                            marker=dict(
                                color=[d['speed'] for d in ranking_data],
                                colorscale='RdYlGn_r',
                                showscale=True,
                                colorbar=dict(title="Adoption Speed")
                            )
                        )
                    ])

                    fig.update_layout(
                        title="Pet Adoption Speed Ranking (Lower is Better)",
                        xaxis_title="Pet",
                        yaxis_title="Adoption Speed (0=Fast, 4=Slow)",
                        height=400
                    )

                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.error(f"❌ Prediction failed: {results.get('error', 'Unknown error')}")

        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")


def show_manual_form():
    """Display manual pet form input."""

    st.header("📝 Single Pet Form")

    st.markdown("""
    Fill in the information about a single pet to get adoption speed prediction
    and recommendations.
    """)

    st.markdown("---")

    # Color mapping (from color_labels.csv)
    COLOR_MAP = {
        1: "Black", 2: "Brown", 3: "Golden", 4: "Yellow",
        5: "Cream", 6: "Gray", 7: "White",
    }
    color_options_primary = list(COLOR_MAP.keys())
    color_options_optional = [0] + color_options_primary

    def color_format(x):
        """Format color option for display."""
        return "None" if x == 0 else COLOR_MAP[x]

    # Form
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🐱 Basic Information")

        pet_type = st.selectbox("Pet Type", options=[1, 2],
            format_func=lambda x: "🐶 Dog" if x == 1 else "🐱 Cat",
            help="Select the type of pet. Choosing Dog or Cat also filters the breeds below.")
        name = st.text_input("Pet Name (optional)", value="",
            help="The name of the pet. Optional, not used in the prediction. Example: 'Buddy'")
        age = st.slider("Age (months)", min_value=0, max_value=120, value=12,
            help="Age of the pet in months. Example: 12 = 1 year old, 6 = half a year old.")

        st.subheader("🎨 Physical Characteristics")

        gender = st.selectbox("Gender", options=[1, 2, 3],
            format_func=lambda x: {1: "Male", 2: "Female", 3: "Mixed"}[x],
            help="Gender of the pet. Use 'Mixed' for groups of different genders.")
        size_labels = {0: "N/A", 1: "Small", 2: "Medium", 3: "Large", 4: "Extra Large"}
        maturity_size = st.selectbox("Maturity Size", options=[0, 1, 2, 3, 4],
            format_func=size_labels.get,
            help="Expected adult size of the pet. Example: Chihuahua = Small, Labrador = Large.")
        fur_length = st.selectbox("Fur Length", options=[0, 1, 2, 3],
            format_func=lambda x: {0: "N/A", 1: "Short", 2: "Medium", 3: "Long"}[x],
            help="Length of the pet's coat. Example: Poodle = Long, Beagle = Short.")

        color1 = st.selectbox("Primary Color", options=color_options_primary,
            format_func=COLOR_MAP.get,
            help="The main coat color of the pet. Example: A black Labrador → Black.")
        color2 = st.selectbox("Secondary Color (optional)", options=color_options_optional,
            format_func=color_format,
            help="A second coat color for markings or patches. Select 'None' if not applicable.")
        color3 = st.selectbox("Tertiary Color (optional)", options=color_options_optional,
            format_func=color_format,
            help="A third coat color for tri-colored pets. Select 'None' if not applicable.")

    with col2:
        st.subheader("🏥 Health & Care")

        health = st.selectbox("Health Status", options=[1, 2, 3],
            format_func=lambda x: {1: "Healthy", 2: "Minor Injury", 3: "Serious Injury"}[x],
            help="Current health condition of the pet. Example: 'Healthy' for no known issues.")
        vaccinated = st.selectbox("Vaccinated?", options=[1, 2, 3],
            format_func=lambda x: {1: "Yes", 2: "No", 3: "Not Sure"}[x],
            help="Whether the pet has received vaccinations. Select 'Not Sure' if unknown.")
        dewormed = st.selectbox("Dewormed?", options=[1, 2, 3],
            format_func=lambda x: {1: "Yes", 2: "No", 3: "Not Sure"}[x],
            help="Whether the pet has been treated for worms. Select 'Not Sure' if unknown.")
        sterilized = st.selectbox("Sterilized?", options=[1, 2, 3],
            format_func=lambda x: {1: "Yes", 2: "No", 3: "Not Sure"}[x],
            help="Whether the pet has been spayed or neutered. Select 'Not Sure' if unknown.")

        st.subheader("💰 Listing Information")

        fee = st.number_input("Adoption Fee (currency)", min_value=0, value=100,
            help="Fee charged for adoption in local currency (MYR). Set to 0 for free adoption.")
        quantity = st.number_input("Number of Pets", min_value=1, value=1,
            help="How many pets are included in this listing. Usually 1 for a single pet listing.")
        state = st.number_input("State ID", min_value=0, value=41326,
            help="Malaysian state code. Example: 41326 = Selangor, 41401 = Kuala Lumpur.")

    st.markdown("---")

    st.subheader("📸 Media & Description")

    col1, col2, col3 = st.columns(3)

    with col1:
        photo_amt = st.number_input("Number of Photos", min_value=0, max_value=50, value=3,
            help="More photos improve adoption chances. Min 3-5 recommended.")

    with col2:
        video_amt = st.number_input("Number of Videos", min_value=0, max_value=10, value=0,
            help="Videos are optional but can help showcase the pet's personality.")

    with col3:
        st.markdown("")
        st.markdown("")
        st.info("📌 Photos are critical - minimum 3-5 recommended")

    description = st.text_area(
        "Pet Description", value="", height=150,
        placeholder=(
            "Describe the pet's personality, history, and characteristics..."
            "\n\n(Minimum 50 words recommended)"
        ),
        help=(
            "Free-text description of the pet. A longer, positive description improves "
            "adoption speed predictions. Minimum 50 words recommended."
        ),
    )

    # Breed info
    st.markdown("---")

    # Hardcoded breed labels (Type 1 = Dog, Type 2 = Cat)
    BREED_DATA = [
        (1, 1, "Affenpinscher"), (2, 1, "Afghan Hound"), (3, 1, "Airedale Terrier"),
        (4, 1, "Akbash"), (5, 1, "Akita"), (6, 1, "Alaskan Malamute"),
        (7, 1, "American Bulldog"), (8, 1, "American Eskimo Dog"),
        (9, 1, "American Hairless Terrier"), (10, 1, "American Staffordshire Terrier"),
        (11, 1, "American Water Spaniel"), (12, 1, "Anatolian Shepherd"),
        (13, 1, "Appenzell Mountain Dog"), (14, 1, "Australian Cattle Dog/Blue Heeler"),
        (15, 1, "Australian Kelpie"), (16, 1, "Australian Shepherd"),
        (17, 1, "Australian Terrier"), (18, 1, "Basenji"), (19, 1, "Basset Hound"),
        (20, 1, "Beagle"), (21, 1, "Bearded Collie"), (22, 1, "Beauceron"),
        (23, 1, "Bedlington Terrier"), (24, 1, "Belgian Shepherd Dog Sheepdog"),
        (25, 1, "Belgian Shepherd Laekenois"), (26, 1, "Belgian Shepherd Malinois"),
        (27, 1, "Belgian Shepherd Tervuren"), (28, 1, "Bernese Mountain Dog"),
        (29, 1, "Bichon Frise"), (30, 1, "Black and Tan Coonhound"),
        (31, 1, "Black Labrador Retriever"), (32, 1, "Black Mouth Cur"),
        (33, 1, "Black Russian Terrier"), (34, 1, "Bloodhound"), (35, 1, "Blue Lacy"),
        (36, 1, "Bluetick Coonhound"), (37, 1, "Boerboel"), (38, 1, "Bolognese"),
        (39, 1, "Border Collie"), (40, 1, "Border Terrier"), (41, 1, "Borzoi"),
        (42, 1, "Boston Terrier"), (43, 1, "Bouvier des Flanders"), (44, 1, "Boxer"),
        (45, 1, "Boykin Spaniel"), (46, 1, "Briard"), (47, 1, "Brittany Spaniel"),
        (48, 1, "Brussels Griffon"), (49, 1, "Bull Terrier"), (50, 1, "Bullmastiff"),
        (51, 1, "Cairn Terrier"), (52, 1, "Canaan Dog"), (53, 1, "Cane Corso Mastiff"),
        (54, 1, "Carolina Dog"), (55, 1, "Catahoula Leopard Dog"), (56, 1, "Cattle Dog"),
        (57, 1, "Caucasian Sheepdog (Caucasian Ovtcharka)"),
        (58, 1, "Cavalier King Charles Spaniel"), (59, 1, "Chesapeake Bay Retriever"),
        (60, 1, "Chihuahua"), (61, 1, "Chinese Crested Dog"), (62, 1, "Chinese Foo Dog"),
        (63, 1, "Chinook"), (64, 1, "Chocolate Labrador Retriever"), (65, 1, "Chow Chow"),
        (66, 1, "Cirneco dell'Etna"), (67, 1, "Clumber Spaniel"), (68, 1, "Cockapoo"),
        (69, 1, "Cocker Spaniel"), (70, 1, "Collie"), (71, 1, "Coonhound"),
        (72, 1, "Corgi"), (73, 1, "Coton de Tulear"), (74, 1, "Curly-Coated Retriever"),
        (75, 1, "Dachshund"), (76, 1, "Dalmatian"), (77, 1, "Dandi Dinmont Terrier"),
        (78, 1, "Doberman Pinscher"), (79, 1, "Dogo Argentino"),
        (80, 1, "Dogue de Bordeaux"), (81, 1, "Dutch Shepherd"),
        (82, 1, "English Bulldog"), (83, 1, "English Cocker Spaniel"),
        (84, 1, "English Coonhound"), (85, 1, "English Pointer"),
        (86, 1, "English Setter"), (87, 1, "English Shepherd"),
        (88, 1, "English Springer Spaniel"), (89, 1, "English Toy Spaniel"),
        (90, 1, "Entlebucher"), (91, 1, "Eskimo Dog"), (92, 1, "Feist"),
        (93, 1, "Field Spaniel"), (94, 1, "Fila Brasileiro"),
        (95, 1, "Finnish Lapphund"), (96, 1, "Finnish Spitz"),
        (97, 1, "Flat-coated Retriever"), (98, 1, "Fox Terrier"), (99, 1, "Foxhound"),
        (100, 1, "French Bulldog"), (101, 1, "Galgo Spanish Greyhound"),
        (102, 1, "German Pinscher"), (103, 1, "German Shepherd Dog"),
        (104, 1, "German Shorthaired Pointer"), (105, 1, "German Spitz"),
        (106, 1, "German Wirehaired Pointer"), (107, 1, "Giant Schnauzer"),
        (108, 1, "Glen of Imaal Terrier"), (109, 1, "Golden Retriever"),
        (110, 1, "Gordon Setter"), (111, 1, "Great Dane"), (112, 1, "Great Pyrenees"),
        (113, 1, "Greater Swiss Mountain Dog"), (114, 1, "Greyhound"),
        (115, 1, "Harrier"), (116, 1, "Havanese"), (117, 1, "Hound"),
        (118, 1, "Hovawart"), (119, 1, "Husky"), (120, 1, "Ibizan Hound"),
        (121, 1, "Illyrian Sheepdog"), (122, 1, "Irish Setter"),
        (123, 1, "Irish Terrier"), (124, 1, "Irish Water Spaniel"),
        (125, 1, "Irish Wolfhound"), (126, 1, "Italian Greyhound"),
        (127, 1, "Italian Spinone"), (128, 1, "Jack Russell Terrier"),
        (129, 1, "Jack Russell Terrier (Parson Russell Terrier)"),
        (130, 1, "Japanese Chin"), (131, 1, "Jindo"), (132, 1, "Kai Dog"),
        (133, 1, "Karelian Bear Dog"), (134, 1, "Keeshond"),
        (135, 1, "Kerry Blue Terrier"), (136, 1, "Kishu"), (137, 1, "Klee Kai"),
        (138, 1, "Komondor"), (139, 1, "Kuvasz"), (140, 1, "Kyi Leo"),
        (141, 1, "Labrador Retriever"), (142, 1, "Lakeland Terrier"),
        (143, 1, "Lancashire Heeler"), (144, 1, "Leonberger"), (145, 1, "Lhasa Apso"),
        (146, 1, "Lowchen"), (147, 1, "Maltese"), (148, 1, "Manchester Terrier"),
        (149, 1, "Maremma Sheepdog"), (150, 1, "Mastiff"), (151, 1, "McNab"),
        (152, 1, "Miniature Pinscher"), (153, 1, "Mountain Cur"),
        (154, 1, "Mountain Dog"), (155, 1, "Munsterlander"),
        (156, 1, "Neapolitan Mastiff"), (157, 1, "New Guinea Singing Dog"),
        (158, 1, "Newfoundland Dog"), (159, 1, "Norfolk Terrier"),
        (160, 1, "Norwegian Buhund"), (161, 1, "Norwegian Elkhound"),
        (162, 1, "Norwegian Lundehund"), (163, 1, "Norwich Terrier"),
        (164, 1, "Nova Scotia Duck-Tolling Retriever"), (165, 1, "Old English Sheepdog"),
        (166, 1, "Otterhound"), (167, 1, "Papillon"),
        (168, 1, "Patterdale Terrier (Fell Terrier)"), (169, 1, "Pekingese"),
        (170, 1, "Peruvian Inca Orchid"), (171, 1, "Petit Basset Griffon Vendeen"),
        (172, 1, "Pharaoh Hound"), (173, 1, "Pit Bull Terrier"),
        (174, 1, "Plott Hound"), (175, 1, "Podengo Portugueso"), (176, 1, "Pointer"),
        (177, 1, "Polish Lowland Sheepdog"), (178, 1, "Pomeranian"), (179, 1, "Poodle"),
        (180, 1, "Portuguese Water Dog"), (181, 1, "Presa Canario"), (182, 1, "Pug"),
        (183, 1, "Puli"), (184, 1, "Pumi"), (185, 1, "Rat Terrier"),
        (186, 1, "Redbone Coonhound"), (187, 1, "Retriever"),
        (188, 1, "Rhodesian Ridgeback"), (189, 1, "Rottweiler"),
        (190, 1, "Saint Bernard"), (191, 1, "Saluki"), (192, 1, "Samoyed"),
        (193, 1, "Sarplaninac"), (194, 1, "Schipperke"), (195, 1, "Schnauzer"),
        (196, 1, "Scottish Deerhound"), (197, 1, "Scottish Terrier Scottie"),
        (198, 1, "Sealyham Terrier"), (199, 1, "Setter"), (200, 1, "Shar Pei"),
        (201, 1, "Sheep Dog"), (202, 1, "Shepherd"),
        (203, 1, "Shetland Sheepdog Sheltie"), (204, 1, "Shiba Inu"),
        (205, 1, "Shih Tzu"), (206, 1, "Siberian Husky"), (207, 1, "Silky Terrier"),
        (208, 1, "Skye Terrier"), (209, 1, "Sloughi"),
        (210, 1, "Smooth Fox Terrier"), (211, 1, "South Russian Ovtcharka"),
        (212, 1, "Spaniel"), (213, 1, "Spitz"), (214, 1, "Staffordshire Bull Terrier"),
        (215, 1, "Standard Poodle"), (216, 1, "Sussex Spaniel"),
        (217, 1, "Swedish Vallhund"), (218, 1, "Terrier"), (219, 1, "Thai Ridgeback"),
        (220, 1, "Tibetan Mastiff"), (221, 1, "Tibetan Spaniel"),
        (222, 1, "Tibetan Terrier"), (223, 1, "Tosa Inu"), (224, 1, "Toy Fox Terrier"),
        (225, 1, "Treeing Walker Coonhound"), (226, 1, "Vizsla"),
        (227, 1, "Weimaraner"), (228, 1, "Welsh Corgi"),
        (229, 1, "Welsh Springer Spaniel"), (230, 1, "Welsh Terrier"),
        (231, 1, "West Highland White Terrier Westie"), (232, 1, "Wheaten Terrier"),
        (233, 1, "Whippet"), (234, 1, "White German Shepherd"),
        (235, 1, "Wire Fox Terrier"), (236, 1, "Wire-haired Pointing Griffon"),
        (237, 1, "Wirehaired Terrier"), (238, 1, "Xoloitzcuintle/Mexican Hairless"),
        (239, 1, "Yellow Labrador Retriever"), (240, 1, "Yorkshire Terrier Yorkie"),
        (307, 1, "Mixed Breed"),
        (241, 2, "Abyssinian"), (242, 2, "American Curl"),
        (243, 2, "American Shorthair"), (244, 2, "American Wirehair"),
        (245, 2, "Applehead Siamese"), (246, 2, "Balinese"), (247, 2, "Bengal"),
        (248, 2, "Birman"), (249, 2, "Bobtail"), (250, 2, "Bombay"),
        (251, 2, "British Shorthair"), (252, 2, "Burmese"), (253, 2, "Burmilla"),
        (254, 2, "Calico"), (255, 2, "Canadian Hairless"), (256, 2, "Chartreux"),
        (257, 2, "Chausie"), (258, 2, "Chinchilla"), (259, 2, "Cornish Rex"),
        (260, 2, "Cymric"), (261, 2, "Devon Rex"), (262, 2, "Dilute Calico"),
        (263, 2, "Dilute Tortoiseshell"), (264, 2, "Domestic Long Hair"),
        (265, 2, "Domestic Medium Hair"), (266, 2, "Domestic Short Hair"),
        (267, 2, "Egyptian Mau"), (268, 2, "Exotic Shorthair"),
        (269, 2, "Extra-Toes Cat (Hemingway Polydactyl)"), (270, 2, "Havana"),
        (271, 2, "Himalayan"), (272, 2, "Japanese Bobtail"), (273, 2, "Javanese"),
        (274, 2, "Korat"), (275, 2, "LaPerm"), (276, 2, "Maine Coon"),
        (277, 2, "Manx"), (278, 2, "Munchkin"), (279, 2, "Nebelung"),
        (280, 2, "Norwegian Forest Cat"), (281, 2, "Ocicat"),
        (282, 2, "Oriental Long Hair"), (283, 2, "Oriental Short Hair"),
        (284, 2, "Oriental Tabby"), (285, 2, "Persian"), (286, 2, "Pixie-Bob"),
        (287, 2, "Ragamuffin"), (288, 2, "Ragdoll"), (289, 2, "Russian Blue"),
        (290, 2, "Scottish Fold"), (291, 2, "Selkirk Rex"), (292, 2, "Siamese"),
        (293, 2, "Siberian"), (294, 2, "Silver"), (295, 2, "Singapura"),
        (296, 2, "Snowshoe"), (297, 2, "Somali"), (298, 2, "Sphynx (hairless cat)"),
        (299, 2, "Tabby"), (300, 2, "Tiger"), (301, 2, "Tonkinese"),
        (302, 2, "Torbie"), (303, 2, "Tortoiseshell"), (304, 2, "Turkish Angora"),
        (305, 2, "Turkish Van"), (306, 2, "Tuxedo"),
    ]

    breed_options = [
        (breed_id, f"{breed_id} - {breed_name}")
        for breed_id, breed_type, breed_name in BREED_DATA
        if breed_type == pet_type
    ]
    breed_ids = [b[0] for b in breed_options]
    breed_labels = [b[1] for b in breed_options]

    col1, col2 = st.columns(2)
    with col1:
        breed1_label = st.selectbox("Primary Breed", options=breed_labels, index=0,
            help="Main breed. For mixed breeds, select the dominant breed.")
        breed1 = breed_ids[breed_labels.index(breed1_label)]
    with col2:
        none_option = "0 - None"
        breed2_options_labels = [none_option] + breed_labels
        breed2_options_ids = [0] + breed_ids
        breed2_label = st.selectbox(
            "Secondary Breed (optional)", options=breed2_options_labels, index=0,
            help="For mixed-breed pets, select the secondary breed.",
        )
        breed2 = breed2_options_ids[breed2_options_labels.index(breed2_label)]

    st.markdown("---")

    # Predict button
    predict_clicked = st.button(
        "🚀 Get Prediction & Recommendations", key="single_predict", type="primary"
    )
    st.caption("⏳ Note: First run may take 1-2 minutes. Subsequent runs are faster.")
    if predict_clicked:

        # Create DataFrame
        pet_data = pd.DataFrame({
            'Type': [pet_type],
            'Name': [name] if name else [None],
            'Age': [age],
            'Breed1': [breed1],
            'Breed2': [breed2],
            'Gender': [gender],
            'Color1': [color1],
            'Color2': [color2],
            'Color3': [color3],
            'MaturitySize': [maturity_size],
            'FurLength': [fur_length],
            'Vaccinated': [vaccinated],
            'Dewormed': [dewormed],
            'Sterilized': [sterilized],
            'Health': [health],
            'Quantity': [quantity],
            'Fee': [fee],
            'State': [state],
            'PhotoAmt': [photo_amt],
            'VideoAmt': [video_amt],
            'Description': [description],
        })
        
        # Beautiful loading animation
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st.markdown("""
            <div class="loading-container">
                <div class="loading-paws">🐾</div>
                <div class="loading-text">Analyzing Pet...</div>
                <p>XGBoost model processing adoption factors...</p>
            </div>
            """, unsafe_allow_html=True)

        results = make_prediction(pet_data)
        loading_placeholder.empty()  # Clear loading animation

        if results['success']:
            pred = results['predictions'][0]

            st.markdown("---")
            st.markdown("## 🎯 Adoption Speed Prediction")

            # Large prediction display
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
                st.markdown(f"# {pred['prediction_emoji']}")
                st.markdown(f"### {pred['prediction_label'].upper()}")
                st.markdown(f"**Confidence:** {pred['confidence']*100:.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")

            # Probability breakdown
            st.markdown("### 📊 Prediction Probabilities")

            probs = pred['probabilities']
            prob_df = pd.DataFrame({
                'Adoption Speed': [AdoptionPredictor.ADOPTION_SPEED_LABELS[i] for i in range(5)],
                'Emoji': [AdoptionPredictor.ADOPTION_SPEED_EMOJI[i] for i in range(5)],
                'Probability': [f"{probs[i]*100:.1f}%" for i in range(5)]
            })

            st.dataframe(prob_df, use_container_width=True, hide_index=True)

            # Visualize probabilities
            fig = go.Figure(data=[
                go.Bar(
                    x=[f"Speed {i}" for i in range(5)],
                    y=[probs[i]*100 for i in range(5)],
                    text=[f"{probs[i]*100:.1f}%" for i in range(5)],
                    textposition='auto',
                    marker=dict(
                        color=[probs[i]*100 for i in range(5)],
                        colorscale='RdYlGn_r',
                        showscale=False
                    )
                )
            ])

            fig.update_layout(
                title="Adoption Speed Probability Distribution",
                xaxis_title="Adoption Speed Category",
                yaxis_title="Probability (%)",
                height=350,
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # Description sentiment analysis
            st.markdown("### Description Sentiment Analysis")
            sentiment = get_description_sentiment(pred['original_data'].get('Description', ''))

            tone_colors = {
                'success': '#2e7d32',
                'info':    '#1565c0',
                'warning': '#e65100',
                'error':   '#b71c1c',
            }
            tone_hex = tone_colors[sentiment['tone_color']]
            pos_pct = sentiment['pos'] * 100
            neu_pct = sentiment['neu'] * 100
            neg_pct = sentiment['neg'] * 100

            sent_col1, sent_col2 = st.columns([1, 2])
            with sent_col1:
                st.markdown(
                    f"<span style='color:{tone_hex}; font-weight:600; font-size:15px;'>"
                    f"{sentiment['tone']}  |  Score: {sentiment['compound']:+.2f}</span>",
                    unsafe_allow_html=True
                )
                bar_style2 = (
                    "width:180px; height:13px; background:#e0e0e0;"
                    " border-radius:3px; overflow:hidden; flex-shrink:0;"
                )
                st.markdown(f"""
<div style="font-size:13px; line-height:2.2; margin-top:6px;">
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="{bar_style2}">
      <div style="width:{pos_pct:.0f}%; height:100%; background:#4CAF50;"></div>
    </div>
    <span style="color:#4CAF50; font-weight:600; min-width:70px;">Positive</span>
    <span>{pos_pct:.0f}%</span>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="{bar_style2}">
      <div style="width:{neu_pct:.0f}%; height:100%; background:#90A4AE;"></div>
    </div>
    <span style="color:#607D8B; font-weight:600; min-width:70px;">Neutral</span>
    <span>{neu_pct:.0f}%</span>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="{bar_style2}">
      <div style="width:{neg_pct:.0f}%; height:100%; background:#F44336;"></div>
    </div>
    <span style="color:#F44336; font-weight:600; min-width:70px;">Negative</span>
    <span>{neg_pct:.0f}%</span>
  </div>
</div>
""", unsafe_allow_html=True)
            with sent_col2:
                st.markdown("")
                st.markdown("")
                st.info(sentiment['advice'])

            st.markdown("---")

            # Adoption factor analysis
            st.markdown("## Adoption Factor Analysis")

            positive_factors, negative_factors = get_adoption_factors(pred['original_data'])

            col_pos, col_neg = st.columns(2)

            with col_pos:
                st.markdown("### Top 5 Factors Helping Adoption")
                if positive_factors:
                    for i, factor in enumerate(positive_factors, 1):
                        with st.container(border=True):
                            st.markdown(f"**{i}. {factor['label']}**")
                            st.caption(factor['sentence'])
                else:
                    st.info("No strong positive factors identified for this pet.")

            with col_neg:
                st.markdown("### Top 5 Factors Hindering Adoption")
                if negative_factors:
                    for i, factor in enumerate(negative_factors, 1):
                        with st.container(border=True):
                            st.markdown(f"**{i}. {factor['label']}**")
                            st.caption(factor['sentence'])
                else:
                    st.success("No significant hindering factors found — great profile!")

        else:
            st.error(f"❌ Prediction failed: {results.get('error', 'Unknown error')}")


def show_about():
    """Display about/information page."""

    st.header("ℹ️ About AdoptSense")

    st.markdown("""
    ## 🎯 Mission

    **AdoptSense** accelerates pet adoptions by providing data-driven insights to animal
    shelters, rescue organizations, and pet owners. The machine learning model predicts
    adoption timelines and identifies key improvement factors to help pets find homes faster.

    ## 🤖 ML Model: XGBoost Classifier

    **Architecture:** Multi-class gradient boosting classifier (5 adoption speed categories)

    **Training Data:** 14,993 pet listings from Petfinder.my (Malaysia)

    **Features:** 27 tabular attributes + 4 VADER sentiment features
    - Tabular: age, size, health, fee, location, media counts, breed, color, etc.
    - Sentiment: compound, positive, negative, neutral scores from description

    **Performance Metrics:**
    - **Accuracy:** 39.75% (Validation on 3,000 held-out pets)
    - **Weighted F1:** 0.3809
    - **Model Features:** 27 (23 tabular + 4 VADER sentiment)

    ## 📊 Feature Importance (Top 10)

    1. **has_photo** (0.1290) - Presence of photos (STRONGEST DRIVER)
    2. **Sterilized** (0.0501) - Spay/neuter status
    3. **age_bin** (0.0422) - Age group binned
    4. **Age** (0.0392) - Age in months
    5. **photo_bin** (0.0389) - Number of photos grouped
    6. **FurLength** (0.0376) - Coat length
    7. **Type** (0.0372) - Dog vs Cat
    8. **Quantity** (0.0360) - Number of pets
    9. **MaturitySize** (0.0355) - Maturity size
    10. **State** (0.0343) - Geographic location

    ## 🔄 Model Comparison & Selection

    The project systematically compares **XGBoost vs Random Forest** to select the best production model.
    Both were trained with identical hyperparameters (300 estimators, max_depth=6) on the same
    27-feature (tabular + VADER) dataset.
    
    **XGBoost Wins on All 5 Metrics:**
    
    | Metric | XGBoost | Random Forest | Difference |
    |--------|---------|---------------|------------|
    | **Accuracy** | 0.3931 | 0.3491 | **+4.40%** ✓ |
    | **Macro F1** | 0.3314 | 0.2877 | **+4.37%** ✓ |
    | **Weighted F1** | 0.3809 | 0.3354 | **+4.55%** ✓ |
    | **Macro Precision** | 0.4115 | 0.3000 | **+11.15%** ✓ |
    | **Macro Recall** | 0.3263 | 0.3100 | **+1.63%** ✓ |
    
    **Why XGBoost?** Sequential tree building with gradient-based corrections handles class
    imbalance better and learns richer feature interactions than Random Forest's averaging approach.

    ## 🛠️ Sentiment Feature Selection

    Two sentiment enrichment strategies were evaluated for the final pipeline:

    | Approach | Features | Accuracy | Macro F1 | Deployable? | Selected? |
    |----------|----------|----------|----------|-----------|-----------|
    | **VADER** | 4 (compound, pos, neg, neu) | 0.3931 | 0.3314 | ✅ Yes (inline) | ✅ YES |
    | **Google NLP JSON** | 10 (doc/entity scores) | 0.3995 | 0.3304 | ❌ No (API) | ❌ No |
    
    **Analysis:**
    - Google NLP slightly outperforms VADER on accuracy (+0.64%), but lower on macro F1
    - Google NLP requires pre-computed JSON files from training corpus → unavailable at inference
    - VADER computes inline from description text → zero dependencies, identical train/prod behavior
    - **Deployment Decision:** VADER selected for reliability over marginal metric gains
    
    This ensures the model deployed to production behaves identically to the training notebook.

    ## 📚 Complete Data Processing Pipeline

    **Section 1: Exploratory Data Analysis** (1.1-1.9)
    - Dataset overview: 14,993 pets across 40 variables
    - Target distribution: Highly imbalanced adoption speeds
    - Key patterns: Photos, description, age, fee are critical
    - Geographic, temporal, and health insights
    
    **Section 2: Predictive Modeling** (2.1-2.4)
    1. Feature Engineering: Create 27 tabular + 4 sentiment features
    2. Train/Val Split: Stratified 80/20 (11,994 train / 2,999 validation)
    3. Scaling: StandardScaler fitted on training set
    4. XGBoost Training: 300 estimators, max_depth=6, class weights
    
    **Section 3: Model Evaluation & Selection** (3.1-3.5)
    5. XGBoost Metrics: Accuracy 0.3931, Macro F1 0.3461
    6. Random Forest Comparison: XGBoost wins 5/5 metrics
    7. Visualizations: Confusion matrices, ROC curves, PR curves
    8. Feature Importance: 20 most influential features ranked
    9. JSON Sentiment Impact: +0.0147 Macro F1 vs baseline
    10. Sentiment Approach Test: VADER vs Google NLP (VADER selected)
    
    **Section 4: Pipeline Serialization** (4.1-4.2)
    11. Save to Pickle: Complete scaler + model + metadata
    12. Pipeline Summary: Human-readable notes on deployment
    
    **Section 5: Actionable Recommendations** (5.1-5.2)
    13. Key Drivers: Top 10 features mapped to business factors
    14. Strategic Actions: 5 concrete improvement areas for shelters

    ## 🚀 Future Improvements

    - CNN-based image quality scoring to enhance photo importance
    - Transformer-based sentiment (DistilBERT) for richer text understanding
    - Temporal/seasonality analysis for adoption trends
    - A/B testing framework to measure recommendation impact
    - Geographic heatmaps for state-level adoption patterns

    ## 📄 References

    - **Dataset:** Petfinder.my dataset (14,993 pet listings)
    - **ML Framework:** XGBoost
    - **Sentiment:** VADER (nltk) + Google Cloud NLP (comparison)
    - **Interface:** Streamlit
    - **Deployment:** Python pickle serialization

    ## 💬 Contact & Support

    For questions, feedback, or feature requests, please refer to the project documentation
    or open an issue on the GitHub repository.

    """)


if __name__ == "__main__":
    main()
