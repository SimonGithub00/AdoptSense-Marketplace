# Frontend Refactor — Info for Simon

Hi Simon, hier ein Überblick was sich im Frontend-Branch geändert hat. Kurzfassung: **deine Backend-Utils sind 1:1 unverändert geblieben**, ich hab nur die UI-Schicht und das Routing umgebaut.

## Was UNVERÄNDERT bleibt (deine Arbeit, nicht angefasst)

Diese Files sind exakt wie du sie gepusht hast:

- `frontend/utils/auth.py`
- `frontend/utils/db.py`
- `frontend/utils/gemini_utils.py`
- `frontend/utils/matching_platform.py` (Konstanten/Maps)
- `frontend/utils/model_loader.py`
- `frontend/utils/predictions.py`
- `frontend/utils/recommendations.py`
- `frontend/utils/seed_data.py`

Alle DB-Schemas, Auth-Flows, Gemini-Calls (Description Improvement + Studio Photos + Stickers), Seed-Logik und ML-Predictions laufen genau wie bei dir.

## Was GEÄNDERT wurde

### `frontend/app.py` — komplett neu

- Vorher: Sidebar-basierte Navigation mit Tabs (Home, Marketplace, Batch, Single Pet, About)
- Jetzt: Eine echte Top-Navbar mit Logo + horizontaler Nav (`streamlit-option-menu`) + User-Avatar
- Sidebar ist komplett deaktiviert (`section[data-testid="stSidebar"] { display: none }`)
- Routing erfolgt über `st.session_state.mp_view` — kompatibel zu deinem System, nutzt deine Views direkt
- Bootstrap-Calls (`db.init_db()`, `seed_if_needed()`, `backfill_predictions()`) bleiben am Anfang
- "Home" und "Marketplace" Schachtel ist weg — der Marketplace IST die App. Browse ist die Default-View.
- Batch + Single Pet Form sind in einen "Tools"-Tab gewandert (manager-only)

### `frontend/utils/matching_platform_ui.py` — visuell überarbeitet

**Wichtig:** Alle deine Funktions-Signaturen sind erhalten. Alle DB- und Gemini-Calls sind 1:1 drin geblieben:
- `render_browse(user)`, `render_detail(listing_id, user)`, `render_my_listings(user)`, `render_create_listing(user)`, `render_edit_listing(listing_id, user)`, `render_kpis(user)`, `render_watchlist(user)`, `render_chat(user)` — alle gleich
- Die alte `show_matching_platform()` Wrapper-Funktion wurde entfernt, weil das Routing jetzt in `app.py` passiert. Die Sub-Navigation innerhalb des Marketplace ist in die Top-Navbar gewandert.
- `_listing_card()` wurde durch `frontend/components/pet_card.py` ersetzt (lädt Fotos als Base64 inline)
- Headers sind jetzt mit Brand-Color (`COLOR_PRIMARY = "#1E2761"` Navy) statt Standard-Streamlit
- "Create New Listing" hat jetzt einen "✨ AI ASSISTED" Badge im Header

**Wenn du `matching_platform_ui.py` weiterentwickelst während der Branch noch offen ist, gibt's hier potenziell Merge-Konflikte.** Sonst bleibt alles konfliktfrei.

### Neue Files (alle in der UI-Schicht)

```
frontend/styles.py                         — Brand-Theme, CSS-Tokens, Logo-SVG
frontend/components/header.py              — Top-Navbar mit Logo + Nav + Avatar
frontend/components/auth_overlay.py        — Login/Register als Modal-Overlay
frontend/components/pet_card.py            — Pet-Card für Browse-Grid
frontend/components/__init__.py            — leeres Package init
frontend/utils/tools_legacy.py             — Batch + Single Pet Form aus deiner alten app.py extrahiert
```

### Requirements

- `streamlit-option-menu>=0.3.13` ist als neue Dependency dazugekommen — wird für die Top-Navbar verwendet
- Die alte `requirements.txt` im Root hatte einen Tippfehler (`asttokens==3.0.1plo`) und mischte Production + Notebook-Dependencies wild. Ist jetzt aufgeräumt.
- Frontend-only deps in `frontend/requirements.txt`, full project deps in Root

## Login-Flow

Wir haben uns für **Variante B** entschieden (Browsen ohne Login möglich, Save/Message triggert Login):
- Anonyme Besucher sehen Hero + Browse + Detail-Seiten
- Klick auf "Save" oder "Message Shelter" → Login-Overlay erscheint
- Nach Login/Registrierung weitergeleitet zur ursprünglichen Aktion

## Was der Prof beim Stresstest sehen wird

1. **Anonymer Besuch:** Hero mit Pet-Bild + Pet Cards Grid → kann clicken, Detail sehen
2. **Registrieren als Adopter:** Header rechts oben → Modal Overlay → nach Login Watchlist + Messages verfügbar
3. **Registrieren als Shelter:** gleiche Flow, aber kommt auf "My Listings" / "Create Listing" / "KPIs" Navbar
4. **Listing Agent Demo:** "Create Listing" → Foto upload → "Make Studio Ready" Button → Gemini macht Background Removal → Side-by-side Vergleich → "Generate AI Description" → Gemini schreibt 4-8 Sätze
5. **Adoption Speed Prediction:** läuft beim Publish automatisch über dein XGBoost

## Wenn was nicht funktioniert

Die wahrscheinlichsten Stolperfallen:

1. **`streamlit-option-menu` nicht installiert** → `pip install streamlit-option-menu`
2. **Sidebar-Navigation ist weg** → das ist Absicht, wurde deaktiviert
3. **Gemini API Key** → bleibt in `.streamlit/secrets.toml`, gleiche Lookup-Logik wie bisher
4. **Seeded DB / Photos fehlen** → `seed_if_needed()` und `backfill_predictions()` werden bei jedem App-Start aufgerufen, sollten greifen wenn `data/train/train.csv` und `data/train_images/` da sind

Falls du Fragen hast oder was im Marketplace UI weiterentwickeln willst — `matching_platform_ui.py` ist die Datei wo's passiert. Versuche dort möglichst die Helper aus `frontend/styles.py` und `frontend/components/*.py` zu nutzen, dann bleibt das Design konsistent.

— Nora
