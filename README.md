# AdoptSense — Pet Adoption Speed Prediction & Marketplace

End-to-end ML platform combining XGBoost adoption speed prediction with a two-sided marketplace.
Built on the Kaggle PetFinder.my dataset; powered by a Streamlit frontend with AI-enhanced
listings, photo studio tools, KPI tracking, live chat, and role-based access.

---

## Table of Contents

- [Overview](#overview)
- [Two Personas](#two-personas)
- [Model](#model)
- [Marketplace Features](#marketplace-features)
- [AI Features (Gemini)](#ai-features-gemini)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Running the App](#running-the-app)

---

## Overview

AdoptSense trains an XGBoost multi-class classifier on ~15,000 labelled pet listings to predict
one of five adoption speed classes:

| Class | Label | Meaning |
|---|---|---|
| 0 | Same day | Adopted on the day of listing |
| 1 | 1–7 days | Adopted within the first week |
| 2 | 8–30 days | Adopted within the first month |
| 3 | 31–90 days | Adopted within three months |
| 4 | No adoption | Not adopted after 100 days |

---

## Two Personas

AdoptSense supports exactly two user roles:

### 🏥 Shelter Manager

Shelter managers represent animal rescue organisations. After registering with a shelter name they can:

- **Create listings** with a full pet form (breed, age, health, fee, photos, description)
- **Photo upload** — select from device or take a photo directly with a mobile camera
- **AI description improvement** — Gemini rewrites raw descriptions into a 4–8 sentence,
  warm, adoption-optimised format; optionally informed by the uploaded pet photo
- **Voice memo** — record a voice description with the microphone; Gemini transcribes it
  to text and pre-fills the description box
- **Studio-ready photos** — remove the pet from its background and place it on a professional
  studio backdrop; download as a studio photo or transparent sticker for social media
- **AI adoption speed prediction** — XGBoost predicts adoption speed (0–4) with confidence
- **Edit / delete listings**
- **Mark pets as adopted** and track actual vs. predicted speed
- **KPI dashboard** — views, contacts, adoption rate, avg length-of-stay, speed distribution
- **Adoption factor analysis** — ranked positive and negative factors per listing
- **Chat** with households who enquire about their listings

### 🏠 Private Household

Households are individuals looking to adopt a pet. They can:

- **Browse** all available listings (no login required)
- **Filter** by: pet type, age range, max fee, vaccinated, dewormed, sterilized, health status,
  gender, maturity size, primary color, and which shelter the pet comes from
- **Smart AI Filter** (login required) — describe your ideal pet in plain language; Gemini
  ranks all listings by how well they match and re-orders the grid accordingly
- **Listen to descriptions** — a 🔊 Listen button on each listing detail page uses Gemini TTS
  to read the pet description aloud
- **View listing detail pages** with photos, full description, and characteristics
- **Add to watchlist** (login required)
- **Message shelter managers** about a specific pet (login required)
- **Chat** with shelters directly in the app

> Households cannot create listings, see performance dashboards, or view adoption factor analysis.

---

## Model

**Algorithm:** XGBoost multi-class classifier (`multi:softmax`, 5 classes)

**Validation metrics (37-feature model with Google NLP JSON):**

| Metric | Value |
|---|---|
| Accuracy | 0.3991 |
| Macro F1 | 0.3461 |
| Weighted F1 | 0.3877 |

**Deployed pipeline:** 27 tabular + 4 VADER sentiment = 31 features (no external API at inference).

**Top feature importances:**

| Rank | Feature | Importance |
|---|---|---|
| 1 | has_photo | 0.1290 |
| 2 | Sterilized | 0.0501 |
| 3 | age_bin | 0.0422 |
| 4 | Age | 0.0392 |
| 5 | photo_bin | 0.0389 |

---

## Marketplace Features

### Pet Listings

- 20 demo listings seeded from the first 20 pets in `train.csv` with real images
- Shelter managers create new listings through a full web form
- Each listing has its own detail page with photo gallery, characteristics table, and description

### Filters (Households)

Pet type · Age range · Max fee · Vaccinated · Dewormed · Sterilized ·
Health status · Gender · Maturity size · Primary color · From which shelter

### Filters (Shelter Managers — additional)

All household filters + **Max predicted adoption speed** (performance view)

### Chat

Real-time (session-based) messaging between households and shelter managers,
scoped per listing. Unread message badge in the sidebar.

### Watchlist

Households can save listings and manage them in a dedicated watchlist tab.

### Database

SQLite database at `frontend/adoptsense.db` stores: users, listings, photos,
messages, watchlist, and listing KPIs. All relationships enforced with foreign keys.

### Authentication

SHA-256 + random salt password hashing (no external auth dependency).
Login / Register buttons in the sidebar; browsing is always public.

---

## AI Features (Gemini)

Configure your Gemini API key in `frontend/.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key-here"
```

Get a free key at https://aistudio.google.com/app/apikey

### Description Improvement

`gemini-2.5-flash` rewrites a shelter manager's raw description into a 4–8 sentence, warm,
adoption-optimised format. Optionally, the first uploaded pet photo is included in the prompt
for multimodal context.

### Voice Memo (Speech-to-Text)

Shelter managers can record a voice memo with the microphone directly in the listing form.
`gemini-2.5-flash` transcribes the audio and pre-fills the description text box so it can be
reviewed and further edited before publishing.

### Text-to-Speech (Listen button)

Every pet detail page shows a 🔊 **Listen** button that reads the description aloud using
`gemini-2.5-flash-preview-tts`. The audio plays inline — no download required.

### Smart AI Filter

Logged-in households can describe their ideal pet in plain language (e.g. *"a calm small
vaccinated dog with no adoption fee"*). `gemini-2.5-flash` scores all listings against the
query and re-orders the browse grid from best match to worst. Regular filters still apply on
top of the AI ranking.

### Backdrop Colour Selection

`gemini-2.5-flash` analyses each pet photo and suggests the ideal solid studio backdrop colour
to complement the pet's coat before running background removal.

### Studio-Ready Photos

1. **Background removal** via `rembg` (U2Net deep learning model — downloads ~170 MB on first use)
2. **Studio backdrop** — Gemini-suggested colour composited via Pillow
3. **Download options:**
   - Studio photo (pet on professional backdrop, PNG)
   - Transparent sticker (pet cut out, PNG with alpha channel) — ready for social media

---

## Project Structure

```
AdoptSense-Pet-Adoption-Prediction/
├── README.md
├── requirements.txt                  # Root dependencies (notebook + frontend)
├── data/                             # gitignored — Kaggle files
│   ├── train/train.csv
│   └── train_images/
├── src/
│   ├── config.py
│   ├── features_tabular.py           # TabularFeatures + VADER
│   ├── features_sentiment.py         # Google NLP JSON (analytical only)
│   ├── petadoption_run.ipynb
│   └── model/
│       ├── petadoption_pipeline.pkl
│       └── pipeline_summary.txt
└── frontend/
    ├── app.py                        # Main Streamlit app
    ├── adoptsense.db                 # SQLite database (auto-created)
    ├── requirements.txt              # Frontend-only dependencies
    ├── run_app.sh / run_app.bat
    ├── .streamlit/
    │   └── secrets.toml              # Gemini API key (gitignored)
    ├── assets/
    │   ├── seed_photos/              # Auto-copied from train_images on first run
    │   ├── uploads/                  # Shelter manager photo uploads
    │   └── studio/                   # Studio-ready processed photos
    └── utils/
        ├── model_loader.py           # Singleton XGBoost pipeline loader
        ├── predictions.py            # AdoptionPredictor, feature alignment
        ├── recommendations.py        # Rule-based adoption factor analysis
        ├── db.py                     # SQLite data layer (all tables)
        ├── auth.py                   # Registration, login, session helpers
        ├── gemini_utils.py           # Gemini description + rembg studio photos
        ├── seed_data.py              # Seeds first 20 pets from train.csv
        ├── matching_platform.py      # Shared constants (labels, color maps)
        └── matching_platform_ui.py   # Full marketplace Streamlit UI
```

---

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/<your-username>/AdoptSense-Pet-Adoption-Prediction.git
cd AdoptSense-Pet-Adoption-Prediction
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
.\.venv\Scripts\Activate.ps1
```

**3. Install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> `rembg` downloads a ~170 MB U2Net model on first use of the studio-ready feature.
> `google-generativeai` requires a Gemini API key (see below).

**4. Download the dataset** (optional — required for training / re-running the notebook)

Download from the [PetFinder.my Kaggle competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
and place as:

```
data/
├── train/
│   ├── train.csv
│   └── train_images/
└── ...
```

**5. Configure Gemini (optional)**

Edit `frontend/.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key-here"
```

**6. Run the notebook** (optional — to regenerate the model pickle)

```bash
jupyter notebook src/petadoption_run.ipynb
```

---

## Running the App

```bash
streamlit run frontend/app.py
```

On first launch the app:
1. Creates `frontend/adoptsense.db` with all tables
2. Creates a demo shelter account (`demo_shelter` / password: `shelter123`)
3. Seeds the first 20 pets from `data/train/train.csv` with their real images

**App tabs:**

| Tab | Access | Description |
|-----|--------|-------------|
| 📊 Home | Public | Overview of the platform and adoption speed categories |
| 🐾 Marketplace | Browse: public · Features: login | Full marketplace with filters, detail pages, chat, watchlist |
| 📁 Batch Upload | Public | Predict adoption speeds for a CSV of pets |
| 📝 Single Pet | Public | Predict speed + recommendations for one pet |
| ℹ️ About | Public | Model documentation and tech stack |

---

## Notes

- The SQLite database is local and resets if deleted. No external database required.
- Sample data resets if `frontend/adoptsense.db` is deleted and the app is restarted.
- Do not commit `data/`, `.venv/`, `frontend/adoptsense.db`, or `frontend/.streamlit/secrets.toml`.
- The model pickle (`src/model/petadoption_pipeline.pkl`) must exist before launching the app.

---

## License

MIT License — see the LICENSE file for details.

---

## References

- Dataset: [PetFinder.my Kaggle Competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
- ML: XGBoost, scikit-learn
- Sentiment: NLTK VADER
- AI: Google Gemini API (`google-generativeai`)
- Background removal: `rembg` (U2Net)
- Frontend: Streamlit, Plotly
