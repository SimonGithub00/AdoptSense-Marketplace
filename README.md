# AdoptSense — Pet Adoption Speed Prediction & Marketplace

End-to-end ML platform combining XGBoost adoption speed prediction with a two-sided marketplace.
Built on the Kaggle PetFinder.my dataset; powered by a Streamlit frontend with AI-enhanced
listings, photo studio tools, comprehensive KPI tracking, live chat, shelter maps, engagement
surveys, admin dashboard, and role-based access. All Gemini features use the `google-genai` SDK (v1.0+).

---

## Table of Contents

- [Overview](#overview)
- [Three Roles](#three-roles)
- [Admin Account](#admin-account)
- [Model](#model)
- [Marketplace Features](#marketplace-features)
- [AI Features](#ai-features)
- [KPI Dashboard](#kpi-dashboard)
- [Smart Filter](#smart-filter)
- [Shelter Map](#shelter-map)
- [Profile Page](#profile-page)
- [Engagement Surveys](#engagement-surveys)
- [Update Index](#update-index)
- [Ethics & Governance](#ethics--governance)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Running the App](#running-the-app)

---

## Overview

AdoptSense trains an XGBoost multi-class classifier on ~15,000 labelled pet listings to predict
one of five adoption speed classes, then translates those predictions into **actionable listing
recommendations** for shelter managers:

| Class | Recommendation | Meaning |
|---|---|---|
| 0 | Top listing | Strong adoption demand expected |
| 1 | List now | Good adoption outlook |
| 2 | Optimize listing | Moderate demand — improve photos or description |
| 3 | Needs attention | Slower outlook — actively improve the listing |
| 4 | High priority | Hard to place — consider fee reduction or AI rewrite |

---

## Three Roles

AdoptSense supports three user roles: **Shelter Manager**, **Private Household**, and **Admin**.

### 🏥 Shelter Manager

Shelter managers represent animal rescue organisations. Registration requires: username, email,
password, shelter name, phone number, and shelter location (country + city). After registering:

- **Create listings** with a full pet form (breed, age, health, fee, photos, videos, description,
  temperament tags, energy level, housing fit, compatibility with children/cats/dogs, location)
- **Photo upload** — select from device or take a photo with a camera
- **Video upload** — attach MP4/MOV/AVI/WEBM videos; count calculated automatically
- **Voice memo** — record a voice description; Gemini transcribes it and appends directly into
  the description field
- **Finalize description with AI** — Gemini rewrites the raw description into a warm, adoption-optimised
  format; AI-polished listings are adopted up to 46% faster
- **Photo Studio** — FLUX.1-Kontext (Black Forest Labs via Hugging Face) transforms each pet photo
  into a professional studio portrait with studio lighting, seamless backdrop, and contact shadow;
  falls back to rembg + PIL if HF token is unavailable or quota is exhausted. AI-enhanced photos
  are labelled with a transparent ✨ badge on the listing card
- **AI adoption speed prediction** — XGBoost predicts adoption speed (0–4) with confidence;
  displayed as actionable listing recommendations, not raw time predictions
- **Edit listings** — full editing form identical to create, including voice memo, AI description,
  photo studio, video upload, and cascading location pickers
- **Mark pets as adopted** and track actual vs. predicted speed
- **KPI dashboard** — 16 metrics across 6 chart tabs
- **Adoption factor analysis** — ranked positive and negative factors per listing
- **Chat** with households — one unified conversation thread per household (not per listing)
- **Profile page** — view and edit contact info, shelter location, bio, and shelter description;
  missing fields highlighted with warnings (visible on Shelter Map only when location is set)
- **Update Index** (dropdown in navbar) — backfills XGBoost predictions, semantic metadata
  (temperament, energy, housing fit, compatibility flags), and location data for all listings

### 🏠 Private Household

Households are individuals looking to adopt a pet. They can:

- **Browse** all available listings (no login required for browsing)
- **Filter** by: pet type, age range, max fee, vaccinated, dewormed, sterilized, health status,
  gender, maturity size, primary color, shelter, country, city, and postal code
- **Smart AI Filter** (login required) — describe your ideal pet in plain language; the system
  ranks all listings by compatibility percentage and re-orders the grid accordingly
- **Compatibility badge** — each card shows the match % in green (≥75%), blue (≥50%), or grey
- **Listen to descriptions** — a 🔊 Listen button on each listing detail page reads the pet
  description aloud using Gemini TTS
- **View listing detail pages** — key info (name, age, health, fee, vaccination status) shown
  prominently; secondary characteristics in a collapsible "Full characteristics" section
- **Add to watchlist** (login required)
- **Message shelter managers** directly — one conversation thread per shelter, regardless of
  which pet page initiated the chat
- **Shelter Map** — interactive world map showing registered AdoptSense shelters as markers,
  with country/city filters, shelter cards below the map, and a Chat button per shelter
- **Profile page** — view and edit email, phone, location, and bio
- **Engagement surveys** — short satisfaction surveys appear at 10, 30, 50, and every 100 pet interactions thereafter

> Households cannot create listings, view KPI dashboards, or access adoption factor analysis.

---

## Admin Account

There is a single, pre-configured administrator account that cannot be created through the
registration flow.

The password is SHA-256 + salt hashed on first launch (same scheme as all other accounts).
If the configured password changes, the hash is updated automatically on next app start.

**2-Factor Authentication:** If SMTP is configured in `secrets.toml`, the admin login flow
sends a 6-digit code to the admin email and requires it before completing login. Without SMTP
the login completes with password only. Resend is available on the 2FA screen; codes expire in
10 minutes.

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your_gmail@gmail.com"
password = "your_app_password"
```

**Admin Dashboard** (nav: Dashboard tab) has five sections:

| Tab | Content |
|-----|---------|
| Growth | User registrations per month, listings per month, role distribution chart |
| Users | Full user table (all roles, join date, action count) |
| Listings | Platform-wide listing table with status, predicted speed, shelter |
| Surveys | User engagement survey scores + chart; post-adoption survey table |
| Events | Live event feed — recent messages and watchlist saves |

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
Neither `id` nor `pet_id` are model features — these are database identifiers only.

**Top feature importances:**

| Rank | Feature | Importance |
|---|---|---|
| 1 | has_photo | 0.1290 |
| 2 | Sterilized | 0.0501 |
| 3 | age_bin | 0.0422 |
| 4 | Age | 0.0392 |
| 5 | photo_bin | 0.0389 |

> **Note on label framing:** Raw speed class predictions (0–4) are surfaced to shelter managers as
> actionable listing recommendations ("Top listing", "Optimize listing", etc.) rather than time
> promises. This avoids setting unrealistic expectations while preserving the model's predictive value
> as a decision-support tool.

---

## Marketplace Features

### Pet Listings

- Demo listings seeded from the PetFinder.my dataset with real images, distributed across
  six European demo shelters (Vienna, Barcelona, Berlin, Athens, Kyiv, Rome)
- Shelter managers create new listings through a full web form
- Each listing has its own detail page with photo gallery, characteristics table, and description
- Listing location fields (country, city, postal code) enable map and filter integration
- Semantic metadata fields (`temperament_tags`, `energy_level`, `housing_fit`,
  `good_with_children`, `good_with_cats`, `good_with_dogs`, `experience_required`,
  `special_needs`) power the Smart AI Filter compatibility scoring

### Filters (Households)

Pet type · Age range · Max fee · Vaccinated · Dewormed · Sterilized ·
Health status · Gender · Maturity size · Primary color · Shelter · Country · City · Postal code

### Filters (Shelter Managers — additional)

All household filters + **Max predicted adoption speed** (performance view)

### Chat

Persistent messaging between households and shelter managers with **one unified conversation
per pair** — messages from all pets are shown in a single thread. Unread count badge visible
in the nav tab and navbar notification. Messages marked as read on conversation open.

### Watchlist

Households can save listings and manage them in a dedicated watchlist tab. Watchlist count
badge shown in the nav tab.

### Videos

Shelter managers can upload MP4/MOV/AVI/WEBM video files per listing. The video count
(`VideoAmt`) is calculated automatically from the number of uploaded files.

### Database

SQLite database at `frontend/adoptsense.db` stores: users, listings, photos, videos, messages,
watchlist, listing KPIs, post-adoption surveys, and engagement surveys. All relationships
enforced with foreign keys. Schema migrations run automatically via `ALTER TABLE … ADD COLUMN`
— no destructive drops on upgrade.

**Tables:** `users` · `listings` · `listing_photos` · `listing_videos` · `listing_kpis` ·
`messages` · `watchlist` · `adoption_surveys` · `user_surveys`

---

## AI Features

### API Keys Required

```toml
# frontend/.streamlit/secrets.toml

GEMINI_API_KEY = "your-gemini-key"   # https://aistudio.google.com/app/apikey
HF_TOKEN = "your-hf-token"           # https://huggingface.co/settings/tokens
```

All Gemini calls use the **`google-genai` SDK** (`from google import genai`).
FLUX calls use **`huggingface_hub`** (`InferenceClient`).

### AI Loading Overlay

Every AI call shows a full-screen overlay with a bouncing AdoptSense logo on a blurred,
darkened background, cycling through 30 rotating funny loading messages.

### Description Improvement (Finalize with AI)

`gemini-2.5-flash` rewrites a shelter manager's raw description into a 4–8 sentence, warm,
adoption-optimised format. The first uploaded pet photo is optionally included for multimodal
context. AI-generated descriptions are flagged with a ✨ badge on the listing card.

### Voice Memo (Speech-to-Text)

Shelter managers can record a voice memo directly in the listing form (create or edit).
Clicking **Transcribe memo** sends the audio to `gemini-2.5-flash` and **appends** the
transcript to the description field — no intermediate Use/Discard dialog.

### Text-to-Speech (Listen button)

Every pet detail page shows a 🔊 **Listen** button that reads the description aloud using
`gemini-2.5-flash-preview-tts`. The audio plays inline in the browser.

### Photo Studio

**Primary:** FLUX.1-Kontext (Black Forest Labs) via Hugging Face Inference API performs
context-aware image editing — the original pet photo is passed with a detailed prompt, and
the model replaces the background with a professional studio backdrop while preserving the
animal's fur, pose, and anatomy. A contact shadow and floor reflection are composited
programmatically after the AI call. A negative prompt constrains hallucination of the subject.

**Fallback:** rembg (U2Net) cutout composited onto a flat neutral backdrop — used when
`HF_TOKEN` is missing or the monthly Hugging Face credit quota is exhausted.

**Transparency:** Photos processed through the Studio are labelled with a subtle ✨ AI badge
on listing cards and in the gallery view.

Available in **create** and **edit** listing modes — not in the read-only view panel.

### Smart AI Filter

Logged-in households describe their ideal pet in plain language. `gemini-2.5-flash` parses the
query into structured JSON; all scoring is deterministic:

```
score = 0.40 × hard_filter_match
      + 0.30 × soft_preference_match   (synonym-aware)
      + 0.20 × description_keyword_match
      + 0.10 × lifestyle_match
```

No listing data is sent to Gemini — only the query text. Synonym groups expand informal
language (e.g. "chill" → calm, "little house" → apartment). Falls back to keyword matching
when Gemini is unavailable.

---

## KPI Dashboard

Shelter managers access a full performance dashboard with 16 metric tiles and 6 chart tabs.

### Metric tiles (4 × 4 grid)

| Row | Metrics |
|-----|---------|
| Core | Total Listings · Active · Adopted · Avg Adoption Speed |
| Engagement | Total Inquiries · Avg Inquiries / Active · Total Views · Watchlist Saves |
| Care | Vaccination % · Sterilization % · Deworming % · Avg Fee |
| Quality | Photo Coverage Rate · Description Quality Score · Long-stay Rate · Survey Score |

### Chart tabs

| Tab | Charts |
|-----|--------|
| Over Time | Monthly new listings (bar) + adopted (line) |
| Speed Distribution | Pie chart of predicted speed classes (0–4) |
| Species | Dog vs. cat age distribution histograms |
| Health & Care | Health status bar chart + care coverage (vacc/ster/dew) |
| Welfare KPIs | Long-stay rate · Photo coverage · Description quality · Post-adoption survey avg |
| All Listings | Filterable dataframe with listing ID, name, speed, health, dates |

---

## Smart Filter

The Smart Filter parses free-text household queries into structured criteria using Gemini, then
scores every available listing deterministically. Results include a `compatibility_percentage`
shown as a coloured badge on each card.

---

## Shelter Map

The Shelter Map (household nav) shows registered AdoptSense shelters on an interactive
OpenStreetMap (via Plotly `scatter_mapbox`). No API token is needed.

---

## Profile Page

All authenticated users can access their profile from the dropdown in the top-right navbar.

- **View tab** — username, role, member since date, email, phone, location, website, and bio
- **Edit tab** — editable form for all profile fields with cascading country → city → postal code

---

## Engagement Surveys

AdoptSense tracks cumulative pet interactions per household user. A brief 1–5 star satisfaction
survey appears once at each lifetime threshold:

```
Early:   10 → 30 → 50
Plateau: 100 → 200 → 300 → …
```

---

## Update Index

Shelter managers and Admin can click **🔄 Update Index** to trigger a full backfill of all
listings: XGBoost predictions, semantic metadata, and location data.

---

## Ethics & Governance

### Model Card

| Attribute | Detail |
|-----------|--------|
| **Model type** | XGBoost multi-class classifier (5 classes) |
| **Training data** | PetFinder.my Kaggle dataset — ~15,000 pet listings from Malaysia (2018) |
| **Geographic scope** | Malaysia only; generalisation to other markets is unvalidated |
| **Prediction task** | Adoption speed class (0–4); surfaced as shelter recommendations |
| **Accuracy** | 39.9% (5-class); meaningful above the 20% random baseline |
| **Primary users** | Shelter managers (decision support), not adopters |
| **Not suitable for** | Automated rejection/acceptance decisions; legal or welfare determinations |

### Known Limitations

**Geographic bias.** The model was trained exclusively on Malaysian shelter data. Feature
distributions (state codes, fee ranges, breed composition) may not generalise to European
or other contexts. The demo shelters in Vienna, Barcelona, Berlin, Athens, Kyiv, and Rome
are illustrative; predictions for these listings should be interpreted with extra caution.

**Accuracy ceiling.** At ~40% accuracy on a 5-class task, the model is useful as a signal
but not as a deterministic predictor. Confidence scores are displayed alongside all predictions
to communicate uncertainty to shelter managers.

**Proxy features.** `has_photo` and `photo_bin` are the top predictors. This reflects a real
adoption dynamic (photos increase visibility) but may disadvantage shelters with fewer resources
for photography — a systemic inequity the platform tries to address through the Photo Studio feature.

**Label framing.** Raw speed classes (e.g. "Same day", "No adoption") have been relabelled as
actionable recommendations ("Top listing", "High priority") to avoid creating false expectations
or stigmatising hard-to-place animals.

### AI Transparency

- **Photo Studio:** Photos processed with FLUX.1-Kontext or rembg are labelled with a ✨ badge
  on listing cards. Adopters can always view the original photo in the gallery.
- **Descriptions:** AI-rewritten descriptions are flagged with ✨ on the listing card. The
  original description is always accessible via "Show original description" in the detail view.
- **Smart Filter:** The compatibility % badge is AI-assisted scoring, not a guarantee of fit.
  The full scoring formula is documented in this README.
- **No autonomous decisions:** All AI outputs are presented as recommendations or enhancements
  to human shelter managers. No listing is automatically accepted, rejected, or modified without
  explicit shelter manager action.

### Data Privacy

- All user data (accounts, listings, messages, watchlist) is stored in a local SQLite database.
  No data is transmitted to third parties except:
  - Gemini API: description text and optionally a pet photo are sent for description improvement,
    voice transcription, and TTS. No user account data is sent.
  - Hugging Face Inference API: pet photos are sent for Photo Studio processing.
- Passwords are hashed with SHA-256 + random salt; plaintext passwords are never stored.
- The database file (`adoptsense.db`) is excluded from version control via `.gitignore`.
- Admin 2FA codes are generated locally and sent via SMTP; codes expire in 10 minutes.

### Responsible Use

AdoptSense is a research and educational prototype built for a Nova SBE Advanced Topics in
Machine Learning course project. It is not intended for production deployment without:

- Independent bias auditing of the XGBoost model across different shelter populations
- GDPR compliance review for any EU deployment involving real user data
- Shelter manager training on interpreting AI predictions as decision support, not ground truth
- A formal data retention and deletion policy

---

## Project Structure

```
AdoptSense-Marketplace/
├── README.md
├── requirements.txt
├── data/                             # gitignored — Kaggle files
│   ├── train/train.csv
│   └── train_images/
├── src/
│   ├── config.py
│   ├── features_tabular.py
│   ├── features_sentiment.py
│   ├── petadoption_run.ipynb
│   └── model/
│       ├── petadoption_pipeline.pkl
│       └── pipeline_summary.txt
└── frontend/
    ├── app.py
    ├── adoptsense.db                 # gitignored
    ├── requirements.txt
    ├── run_app.sh / run_app.bat
    ├── .streamlit/
    │   └── secrets.toml              # gitignored
    ├── assets/
    │   ├── logo/
    │   ├── shelter_locations.json
    │   ├── seed_photos/
    │   ├── uploads/
    │   └── studio/
    ├── components/
    │   ├── header.py
    │   ├── auth_overlay.py
    │   └── pet_card.py
    ├── styles.py
    └── utils/
        ├── model_loader.py
        ├── predictions.py
        ├── recommendations.py
        ├── db.py
        ├── auth.py
        ├── gemini_utils.py
        ├── seed_data.py
        ├── matching_platform.py
        ├── matching_platform_ui.py
        └── admin_ui.py
```

---

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/SimonGithub00/AdoptSense-Marketplace.git
cd AdoptSense-Marketplace
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

> `rembg` downloads a ~170 MB U2Net model on first use of the Studio feature.

**4. Download the dataset** (optional — required for training or re-running the notebook)

Download from the [PetFinder.my Kaggle competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
and place as:

```
data/
├── train/
│   ├── train.csv
│   └── train_images/
```

**5. Configure secrets**

Create `frontend/.streamlit/secrets.toml` (already in `.gitignore`):

```toml
[admin]
password = "your_secure_admin_password"

# Gemini API key — https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "your-gemini-key"

# Hugging Face token — https://huggingface.co/settings/tokens
# Requires "Make calls to Inference Providers" permission
# Accept model license at: huggingface.co/black-forest-labs/FLUX.1-Kontext-dev
HF_TOKEN = "hf_your-token"

# SMTP for admin 2FA (optional)
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your_gmail@gmail.com"
password = "your_app_password"
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

On first launch the app seeds demo data and runs all migrations automatically.

**Navigation by role:**

| Nav Item | Access | Description |
|----------|--------|-------------|
| Browse | Public | Pet grid with filters and smart AI filter |
| Watchlist (N) | Household | Saved listings |
| Messages (N) | Logged in | One-thread-per-shelter chat |
| Shelter Map | Household | Interactive world map of registered shelters |
| My Listings | Shelter manager | Listing management panel |
| Create Listing | Shelter manager | Full listing form with AI tools |
| KPIs | Shelter manager | 16 metrics + 6 chart tabs |
| About | Public | Tech stack, ethics, and disclaimers |
| Tools | Shelter manager / Admin | Batch CSV upload + single-pet manual form |
| Dashboard | Admin only | Platform-wide metrics, users, surveys, event feed |
| Profile | Logged in | View / edit profile |

---

## Notes

- The SQLite database is local and resets if deleted. No external database required.
- Do not commit `data/`, `.venv/`, `frontend/adoptsense.db`, or `.streamlit/secrets.toml`.
- The model pickle (`src/model/petadoption_pipeline.pkl`) must exist before launching the app.
- All AI features degrade gracefully when API keys are missing.
- Chat is scoped per shelter-household pair — all messages appear in one unified thread.

---

## License

See the LICENSE file for details.

---

## References

- Dataset: [PetFinder.my Kaggle Competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
- ML: XGBoost, scikit-learn
- Sentiment: NLTK VADER
- AI descriptions & TTS: Google Gemini API (`google-genai`)
- Photo Studio: FLUX.1-Kontext (Black Forest Labs) via Hugging Face (`huggingface_hub`)
- Background removal fallback: `rembg` (U2Net)
- Frontend: Streamlit, Plotly, streamlit-option-menu