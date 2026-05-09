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
- [AI Features (Gemini)](#ai-features-gemini)
- [KPI Dashboard](#kpi-dashboard)
- [Smart Filter](#smart-filter)
- [Shelter Map](#shelter-map)
- [Profile Page](#profile-page)
- [Engagement Surveys](#engagement-surveys)
- [Update Index](#update-index)
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
- **Photo Studio** — Gemini transforms each pet photo into a professional studio portrait with a
  complementary solid backdrop; falls back to rembg + PIL if Gemini is unavailable
- **AI adoption speed prediction** — XGBoost predicts adoption speed (0–4) with confidence
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
registration flow:

| Field | Value |
|-------|-------|
| Username | `Admin` |
| Email | `simon.anthofer00@web.de` |
| Role | `admin` |

**Password:** Set in `.streamlit/secrets.toml` (git-ignored, never committed):

```toml
[admin]
password = "your_secure_password"
```

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
password = "your_app_password"   # Gmail App Password
```

**Admin Dashboard** (nav: Dashboard tab) has five sections:

| Tab | Content |
|-----|---------|
| Growth | User registrations per month, listings per month, role distribution chart |
| Users | Full user table (all roles, join date, action count) |
| Listings | Platform-wide listing table with status, predicted speed, shelter |
| Surveys | User engagement survey scores + chart; post-adoption survey table |
| Events | Live event feed — recent messages and watchlist saves |

The admin can also change the admin password from the **Profile** page (separate from the
secrets.toml value — use secrets.toml on fresh installs, Profile for in-app rotation).

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

---

## Marketplace Features

### Pet Listings

- 20 demo listings seeded from the first 20 pets in `train.csv` with real images
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

### Authentication

SHA-256 + random salt password hashing. Login / Register buttons in the top navbar.
Shelter managers must provide phone number and location during registration. Browsing is
always public.

**Profile dropdown** (avatar button) — Profile · Update Index (managers only) · Log out

---

## AI Features (Gemini)

Configure your Gemini API key in `frontend/.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key-here"
```

Get a free key at https://aistudio.google.com/app/apikey

All Gemini calls use the **`google-genai` SDK** (`from google import genai`), replacing the
deprecated `google-generativeai` package.

### AI Loading Overlay

Every Gemini call shows a full-screen overlay with a bouncing AdoptSense logo on a blurred,
darkened background, cycling through 30 rotating funny loading messages so users always know
AI is working.

### Description Improvement (Finalize with AI)

`gemini-2.5-flash` rewrites a shelter manager's raw description into a 4–8 sentence, warm,
adoption-optimised format. The first uploaded pet photo is optionally included for multimodal
context. The result **replaces** the description textarea content directly.

### Voice Memo (Speech-to-Text)

Shelter managers can record a voice memo directly in the listing form (create or edit).
Clicking **Transcribe memo** sends the audio to `gemini-2.5-flash` and **appends** the
transcript to the description field — no intermediate Use/Discard dialog.

### Text-to-Speech (Listen button)

Every pet detail page shows a 🔊 **Listen** button that reads the description aloud using
`gemini-2.5-flash-preview-tts`. The audio plays inline in the browser.

### Photo Studio

`gemini-2.0-flash-exp` transforms each pet photo into a professional studio portrait: removes
the background, intelligently inpaints hidden areas, and places the pet on a complementary
solid-colour backdrop. Falls back to `rembg` + PIL if Gemini image editing fails.

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

The browse grid re-orders from best match to worst. Synonym groups expand informal language
(e.g. "childs" → children, "chill" → calm, "little house" → apartment). Falls back to
keyword matching when Gemini is unavailable.

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
scores every available listing deterministically. No listing data is sent to Gemini — only the
query text. Results include a `compatibility_percentage` shown as a coloured badge on each card.

**Synonym-aware matching:** `_SYNONYM_GROUPS` in `gemini_utils.py` maps informal variants
(e.g. "childs", "toddler", "baby" → children; "apartment", "flat", "small space" → apartment)
so queries in broken or informal language still match correctly.

**Fallback:** If the Gemini API key is missing or the call fails, a keyword-matching fallback
scores listings by term overlap in name and description, ensuring the feature degrades gracefully.

---

## Shelter Map

The Shelter Map (household nav) shows registered AdoptSense shelters on an interactive
OpenStreetMap (via Plotly `scatter_mapbox`). No API token is needed.

**Behaviour:**
- **Default view** — world map centred on Malaysia (where seeded data is), showing all registered
  shelters with location data as blue marker pins
- **Country filter** — zooms to the country and shows only shelters in that country; city dots
  appear as reference points if no registered shelters exist there
- **City filter** — zooms to street level; shows the selected city's registered shelters
- **Hover** — shelter name, city, country, and phone visible on hover
- **Shelter cards** below the map list all matching shelters with address, phone, and a
  **💬 Chat** button (household) or **🔑 Log in** prompt (guest)
- **↺ Reset** clears all filters and returns to the world view

Shelter location is set during registration and can be updated from the profile Edit tab.

---

## Profile Page

All authenticated users can access their profile from the dropdown in the top-right navbar.

- **View tab** — username, role, member since date, email, phone, location, website, and bio;
  shelter managers also see shelter address and description; missing required fields shown with
  ⚠️ warnings (missing location = shelter invisible on the map)
- **Edit tab** — editable form for all profile fields; cascading country → city → postal code
  pickers for shelter managers; changes saved immediately

---

## Engagement Surveys

To measure household satisfaction over time, AdoptSense tracks cumulative pet interactions
(views, watchlist saves, messages sent) per household user. A brief 1–5 star satisfaction
survey appears **once** at each lifetime threshold:

```
Early:   10 → 30 → 50  (light touch during onboarding)
Plateau: 100 → 200 → 300 → …   (one survey every 100 actions)
```

**Survey presentation:** the survey renders as a centred card on a darkened page background.
Since the survey is the only content shown at that moment (the browse page stops rendering),
the dark app shell makes the white survey card stand out clearly. Users can submit or skip.

The survey is non-blocking — users can skip it. Responses are stored in `user_surveys`; each
threshold is marked completed once seen (either submitted or skipped). Admin can view all
responses in the Surveys tab of the Dashboard.

---

## Update Index

Shelter managers and the Admin can click **🔄 Update Index** in the profile dropdown to trigger
a full backfill of all listings:

1. **XGBoost adoption speed predictions** — filled for any listing still missing one
2. **Semantic metadata** — `temperament_tags`, `energy_level`, `housing_fit`,
   `good_with_children`, `good_with_cats`, `good_with_dogs`, `experience_required`,
   `special_needs` — **always re-derived** from current description keywords (existing values
   are overwritten so the index stays fresh after listing edits)
3. **Location data** — `country` and `city` — filled only where missing (derived from Malaysia
   state codes for seeded listings, or carried forward from the listing form)
4. **Demo shelter location** — ensures the demo shelter appears on the Shelter Map

> Latitude/longitude columns were removed from the schema. The Shelter Map resolves coordinates
> at render time from an internal city-name lookup dictionary — no stored coordinates needed.

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
    ├── app.py                        # Main Streamlit entry point + view routing
    ├── adoptsense.db                 # SQLite database (auto-created)
    ├── requirements.txt              # Frontend-only dependencies
    ├── run_app.sh / run_app.bat
    ├── .streamlit/
    │   └── secrets.toml              # Gemini API key (gitignored)
    ├── assets/
    │   ├── logo/                     # AdoptSense logo (PNG + SVG)
    │   ├── shelter_locations.json    # Country/city cascade data + postal codes
    │   ├── seed_photos/              # Auto-copied from train_images on first run
    │   ├── uploads/                  # Shelter manager photo uploads
    │   └── studio/                   # Studio-ready processed photos
    ├── components/
    │   ├── header.py                 # Navbar: logo, nav menu, profile popover dropdown
    │   ├── auth_overlay.py           # Login / register overlay with location pickers
    │   └── pet_card.py               # Pet card with compatibility badge support
    ├── styles.py                     # Brand colours, logo helpers, global CSS
    └── utils/
        ├── model_loader.py           # Singleton XGBoost pipeline loader
        ├── predictions.py            # AdoptionPredictor, feature alignment
        ├── recommendations.py        # Rule-based adoption factor analysis
        ├── db.py                     # SQLite data layer (all tables + migrations)
        ├── auth.py                   # Registration, login, session helpers
        ├── gemini_utils.py           # google-genai client, AI overlay, studio, smart filter
        ├── seed_data.py              # Seeds first 20 pets + backfills metadata/location
        ├── matching_platform.py      # Shared constants (labels, color maps)
        ├── matching_platform_ui.py   # Full marketplace Streamlit UI
        └── admin_ui.py               # Admin dashboard (Growth, Users, Listings, Surveys, Events)
```

---

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/SimonGithub00/AdoptSense-Pet-Adoption-Prediction.git
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

> `rembg` downloads a ~170 MB U2Net model on first use of the Studio feature.

**4. Download the dataset** (optional — required for training or re-running the notebook)

Download from the [PetFinder.my Kaggle competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
and place as:

```
data/
├── train/
│   ├── train.csv
│   └── train_images/
└── ...
```

**5. Configure secrets (required for admin account; optional for other features)**

Create `.streamlit/secrets.toml` (already in `.gitignore`):

```toml
[admin]
password = "your_secure_admin_password"

# SMTP for 2FA email codes (optional — skip to log in without 2FA)
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your_gmail@gmail.com"
password = "your_app_password"

# Gemini API key (optional — can also be entered in the UI)
[gemini]
api_key = "your-gemini-key-here"
```

Get a Gemini key at https://aistudio.google.com/app/apikey

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
1. Creates `frontend/adoptsense.db` with all tables and runs schema migrations
2. Creates the **Admin** account from `secrets.toml` (skipped if password not configured)
3. Creates a demo shelter account (`demo_shelter` / password: `shelter123`) located in Kuala Lumpur
4. Seeds the first 20 pets from `data/train/train.csv` with their real images
5. Backfills XGBoost adoption speed predictions and semantic metadata for all listings

**Navigation by role:**

| Nav Item | Access | Description |
|----------|--------|-------------|
| Browse | Public | Pet grid with filters and smart AI filter |
| Watchlist (N) | Household | Saved listings; N = count badge |
| Messages (N) | Logged in | One-thread-per-shelter chat; N = unread count |
| Shelter Map | Household | Interactive world map of registered shelters |
| My Listings | Shelter manager | Listing management panel |
| Create Listing | Shelter manager | Full listing form with AI tools |
| KPIs | Shelter manager | 16 metrics + 6 chart tabs |
| About | Public | Model documentation and tech stack |
| Tools | Shelter manager / Admin | Batch CSV upload + single-pet manual form |
| Dashboard | Admin only | Platform-wide metrics, users, surveys, event feed |
| Profile | Logged in | View / edit profile; admin can change password here |

---

## Notes

- The SQLite database is local and resets if deleted. No external database required.
- Schema upgrades run automatically — columns are added with `ALTER TABLE` when missing; the
  `users` table `CHECK` constraint is migrated at startup to include the `admin` role.
- Do not commit `data/`, `.venv/`, `frontend/adoptsense.db`, or `.streamlit/secrets.toml`.
- The model pickle (`src/model/petadoption_pipeline.pkl`) must exist before launching the app.
- All Gemini features degrade gracefully: descriptions can still be written manually, the smart
  filter falls back to keyword matching, and the photo studio still removes backgrounds via rembg
  without the Gemini AI backdrop.
- Chat is scoped per shelter-household pair (not per listing) — all messages with a shelter appear
  in one unified thread regardless of which pet page started the conversation.
- Admin 2FA requires SMTP credentials in `secrets.toml`. Without them, the admin logs in with
  password only.
- Latitude/longitude columns are no longer stored in the listings table. The Shelter Map resolves
  shelter coordinates from an in-memory city-name lookup — no DB coordinates needed.

---

## License

MIT License — see the LICENSE file for details.

---

## References

- Dataset: [PetFinder.my Kaggle Competition](https://www.kaggle.com/c/petfinder-adoption-prediction)
- ML: XGBoost, scikit-learn
- Sentiment: NLTK VADER
- AI: Google Gemini API (`google-genai`)
- Background removal: `rembg` (U2Net)
- Frontend: Streamlit, Plotly, streamlit-option-menu
