"""
Seed the database with the first 20 pets from train.csv and their images.
Creates a demo shelter account and populates listings with XGBoost predictions.
Backfill also fills semantic metadata and location fields.
"""
import shutil
from pathlib import Path

import pandas as pd

from frontend.utils import db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_CSV = PROJECT_ROOT / "data" / "train" / "train.csv"
TRAIN_IMAGES_DIR = PROJECT_ROOT / "data" / "train_images"

SEED_SHELTER_USERNAME = "demo_shelter"
SEED_SHELTER_EMAIL = "demo@adoptsense.org"

# Malaysia state code → (city, latitude, longitude)
_MALAYSIA_STATE_COORDS: dict[int, tuple[str, float, float]] = {
    41324: ("Johor Bahru", 1.4927, 103.7414),
    41316: ("Alor Setar", 6.1248, 100.3673),
    41317: ("Kota Bharu", 6.1254, 102.2381),
    41318: ("Melaka City", 2.1896, 102.2501),
    41319: ("Seremban", 2.7259, 101.9424),
    41320: ("Kuantan", 3.8077, 103.3260),
    41321: ("George Town", 5.4141, 100.3288),
    41322: ("Ipoh", 4.5975, 101.0901),
    41323: ("Kangar", 6.4433, 100.1980),
    41326: ("Kuala Lumpur", 3.1390, 101.6869),
    41325: ("Labuan", 5.2767, 115.2308),
    41327: ("Putrajaya", 2.9264, 101.6964),
    41328: ("Kota Kinabalu", 5.9804, 116.0735),
    41329: ("Kuching", 1.5533, 110.3592),
    41330: ("Shah Alam", 3.0738, 101.5183),
    41331: ("Kuala Terengganu", 5.3302, 103.1408),
}


def _infer_listing_metadata(description: str, state: int) -> dict:
    """Infer semantic metadata fields from listing description + Malaysia state code."""
    desc = (description or "").lower()

    # Temperament tags — comma-separated keywords
    tags = []
    if any(w in desc for w in ["playful", "energetic", "active", "lively", "loves to play", "spirited"]):
        tags.append("playful")
    if any(w in desc for w in ["calm", "gentle", "quiet", "relaxed", "laid-back", "docile", "easy-going"]):
        tags.append("calm")
    if any(w in desc for w in ["friendly", "sociable", "social", "affectionate", "loving", "cuddly", "sweet"]):
        tags.append("friendly")
    if any(w in desc for w in ["loyal", "devoted", "bonded"]):
        tags.append("loyal")
    if any(w in desc for w in ["curious", "intelligent", "smart", "clever"]):
        tags.append("curious")
    if any(w in desc for w in ["independent", "aloof", "reserved"]):
        tags.append("independent")
    if any(w in desc for w in ["protective", "guard", "watchdog"]):
        tags.append("protective")

    # Energy level
    if any(w in desc for w in ["high energy", "very energetic", "very active", "loves to run"]):
        energy_level = "high"
    elif any(w in desc for w in ["calm", "lazy", "relaxed", "quiet", "low energy", "mellow", "laid-back", "docile"]):
        energy_level = "low"
    elif any(w in desc for w in ["playful", "energetic", "active", "lively"]):
        energy_level = "medium"
    else:
        energy_level = "medium"

    # Housing fit
    housing_fits = []
    if any(w in desc for w in ["apartment", "flat", "small space", "indoor", "condo"]):
        housing_fits.append("apartment")
    if any(w in desc for w in ["yard", "garden", "outdoor", "space to run", "house"]):
        housing_fits.append("house")
    housing_fit = ", ".join(housing_fits) if housing_fits else "any"

    # Good with children
    if any(w in desc for w in ["good with children", "good with kids", "great with kids",
                                "child-friendly", "kid-friendly", "loves children", "loves kids",
                                "family-friendly", "children friendly"]):
        good_with_children = 1
    elif any(w in desc for w in ["not good with children", "not good with kids", "no children",
                                  "no kids", "prefers adult", "not suitable for children"]):
        good_with_children = 0
    else:
        good_with_children = None

    # Good with cats
    if any(w in desc for w in ["good with cats", "gets along with cats", "cat-friendly",
                                "lives with cats", "cat friendly"]):
        good_with_cats = 1
    elif any(w in desc for w in ["not good with cats", "chases cats", "no cats",
                                  "cannot live with cats"]):
        good_with_cats = 0
    else:
        good_with_cats = None

    # Good with dogs
    if any(w in desc for w in ["good with dogs", "gets along with dogs", "dog-friendly",
                                "lives with dogs", "dog friendly"]):
        good_with_dogs = 1
    elif any(w in desc for w in ["not good with dogs", "chases dogs", "no dogs",
                                  "cannot live with dogs"]):
        good_with_dogs = 0
    else:
        good_with_dogs = None

    # Experience required
    if any(w in desc for w in ["experienced owner", "experienced handler", "not for beginners",
                                "requires experience", "needs experienced"]):
        experience_required = "experienced"
    elif any(w in desc for w in ["great for first time", "ideal for beginners", "first-time owner",
                                  "easy to train", "easy to care", "low maintenance"]):
        experience_required = "beginner"
    else:
        experience_required = "any"

    # Special needs
    need_kws = ["special needs", "medical attention", "disabled", "blind", "deaf",
                "heart condition", "fiv", "felv", "feline leukemia", "diabetes",
                "epilepsy", "seizure", "three leg", "amputee", "medication"]
    found = [kw for kw in need_kws if kw in desc]
    special_needs = ", ".join(found) if found else "none"

    # Location from Malaysia state code (lat/lon retained in dict for future use but not stored)
    loc = _MALAYSIA_STATE_COORDS.get(int(state) if state else 41326)
    city = loc[0] if loc else "Kuala Lumpur"

    return {
        "temperament_tags": ", ".join(tags) if tags else None,
        "energy_level": energy_level,
        "housing_fit": housing_fit,
        "good_with_children": good_with_children,
        "good_with_cats": good_with_cats,
        "good_with_dogs": good_with_dogs,
        "experience_required": experience_required,
        "special_needs": special_needs,
        "country": "Malaysia",
        "city": city,
    }


ADMIN_USERNAME = "Admin"
ADMIN_EMAIL = "simon.anthofer00@web.de"


def create_admin_if_needed():
    """Create or update the admin account using password from .streamlit/secrets.toml."""
    try:
        import streamlit as st
        pw = st.secrets.get("admin", {}).get("password", "")
        if not pw:
            return
    except Exception:
        return

    from frontend.utils.auth import hash_password, verify_password
    existing = db.get_user_by_username(ADMIN_USERNAME)
    if not existing:
        pw_hash = hash_password(pw)
        db.create_user(ADMIN_USERNAME, ADMIN_EMAIL, pw_hash, "admin")
    else:
        # Re-hash and update only if the configured password changed
        if not verify_password(pw, existing["password_hash"]):
            new_hash = hash_password(pw)
            db.update_user(existing["id"], password_hash=new_hash)


def seed_if_needed():
    """Run once to populate database with demo data."""
    if db.is_seeded():
        return

    shelter = db.get_user_by_username(SEED_SHELTER_USERNAME)
    if not shelter:
        from frontend.utils.auth import hash_password
        pw_hash = hash_password("shelter123")
        uid = db.create_user(
            SEED_SHELTER_USERNAME,
            SEED_SHELTER_EMAIL,
            pw_hash,
            "shelter_manager",
            shelter_name="AdoptSense Demo Shelter",
        )
        if uid is None:
            shelter = db.get_user_by_username(SEED_SHELTER_USERNAME)
            if shelter:
                uid = shelter["id"]
            else:
                return
    else:
        uid = shelter["id"]

    if not TRAIN_CSV.exists():
        return

    try:
        df = pd.read_csv(TRAIN_CSV).head(20)
    except Exception:
        return

    from frontend.utils.predictions import make_prediction

    for _, row in df.iterrows():
        pet_id = str(row.get("PetID", ""))
        pet_name = str(row.get("Name", "")) if pd.notna(row.get("Name")) else "Unknown"
        if not pet_name or pet_name in ("nan", "NaN"):
            pet_name = "Unknown"

        description = str(row.get("Description", "")) if pd.notna(row.get("Description")) else ""

        # Count images for PhotoAmt
        photo_count = 0
        if TRAIN_IMAGES_DIR.exists():
            photo_count = len(list(TRAIN_IMAGES_DIR.glob(f"{pet_id}-*.jpg")))

        # Run XGBoost prediction before creating listing
        speed = conf = None
        try:
            pet_df = pd.DataFrame([{
                "Type": int(row.get("Type", 1)),
                "Name": pet_name,
                "Age": int(row.get("Age", 0)),
                "Breed1": int(row.get("Breed1", 0)),
                "Breed2": int(row.get("Breed2", 0)),
                "Gender": int(row.get("Gender", 1)),
                "Color1": int(row.get("Color1", 1)),
                "Color2": int(row.get("Color2", 0)),
                "Color3": int(row.get("Color3", 0)),
                "MaturitySize": int(row.get("MaturitySize", 0)),
                "FurLength": int(row.get("FurLength", 0)),
                "Vaccinated": int(row.get("Vaccinated", 3)),
                "Dewormed": int(row.get("Dewormed", 3)),
                "Sterilized": int(row.get("Sterilized", 3)),
                "Health": int(row.get("Health", 1)),
                "Quantity": int(row.get("Quantity", 1)),
                "Fee": float(row.get("Fee", 0)),
                "State": int(row.get("State", 41326)),
                "PhotoAmt": photo_count,
                "VideoAmt": int(row.get("VideoAmt", 0)),
                "Description": description,
            }])
            pred_result = make_prediction(pet_df)
            if pred_result.get("success"):
                p0 = pred_result["predictions"][0]
                speed = p0["prediction"]
                conf = p0["confidence"]
        except Exception:
            pass

        lid = db.create_listing(
            shelter_id=uid,
            pet_name=pet_name,
            pet_type=int(row.get("Type", 1)),
            pet_id=pet_id,
            age=int(row.get("Age", 0)),
            breed1=int(row.get("Breed1", 0)),
            breed2=int(row.get("Breed2", 0)),
            gender=int(row.get("Gender", 1)),
            color1=int(row.get("Color1", 1)),
            color2=int(row.get("Color2", 0)),
            color3=int(row.get("Color3", 0)),
            maturity_size=int(row.get("MaturitySize", 0)),
            fur_length=int(row.get("FurLength", 0)),
            vaccinated=int(row.get("Vaccinated", 3)),
            dewormed=int(row.get("Dewormed", 3)),
            sterilized=int(row.get("Sterilized", 3)),
            health=int(row.get("Health", 1)),
            quantity=int(row.get("Quantity", 1)),
            fee=float(row.get("Fee", 0)),
            state=int(row.get("State", 41326)),
            video_amt=int(row.get("VideoAmt", 0)),
            description=description,
            adoption_speed_pred=speed,
            adoption_speed_confidence=conf,
        )

        # Copy images
        seed_dir = db.SEED_DIR / str(lid)
        seed_dir.mkdir(parents=True, exist_ok=True)
        if TRAIN_IMAGES_DIR.exists():
            imgs = sorted(TRAIN_IMAGES_DIR.glob(f"{pet_id}-*.jpg"))
            for img_path in imgs:
                dest = seed_dir / img_path.name
                shutil.copy2(str(img_path), str(dest))
                db.add_photo(lid, str(dest))


def backfill_predictions():
    """
    Backfill all listings:
    - XGBoost predictions for listings missing them
    - Semantic metadata (temperament, energy, housing fit, compatibility, etc.)
      is ALWAYS overwritten from description text for every listing
    - Location (country, city) filled only where missing
    """
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM listings").fetchall()
    conn.close()

    # Ensure demo shelter has location data so it appears on the map
    demo = db.get_user_by_username(SEED_SHELTER_USERNAME)
    if demo and not demo.get("city"):
        db.update_user(
            demo["id"],
            country="Malaysia",
            city="Kuala Lumpur",
            phone="+60 3-9999 9999",
            shelter_address="Jalan Demo 1, Kuala Lumpur",
        )

    if not rows:
        return

    from frontend.utils.predictions import make_prediction

    for row in rows:
        r = dict(row)
        updates: dict = {}

        # XGBoost prediction if missing
        if r.get("adoption_speed_pred") is None:
            try:
                pet_df = pd.DataFrame([{
                    "Type": r.get("type", 1),
                    "Name": r.get("pet_name", ""),
                    "Age": r.get("age", 0),
                    "Breed1": r.get("breed1", 0),
                    "Breed2": r.get("breed2", 0),
                    "Gender": r.get("gender", 1),
                    "Color1": r.get("color1", 1),
                    "Color2": r.get("color2", 0),
                    "Color3": r.get("color3", 0),
                    "MaturitySize": r.get("maturity_size", 0),
                    "FurLength": r.get("fur_length", 0),
                    "Vaccinated": r.get("vaccinated", 3),
                    "Dewormed": r.get("dewormed", 3),
                    "Sterilized": r.get("sterilized", 3),
                    "Health": r.get("health", 1),
                    "Quantity": r.get("quantity", 1),
                    "Fee": r.get("fee", 0),
                    "State": r.get("state", 41326),
                    "PhotoAmt": r.get("photo_amt", 0),
                    "VideoAmt": r.get("video_amt", 0),
                    "Description": r.get("description", ""),
                }])
                pred_result = make_prediction(pet_df)
                if pred_result.get("success"):
                    p0 = pred_result["predictions"][0]
                    updates["adoption_speed_pred"] = p0["prediction"]
                    updates["adoption_speed_confidence"] = p0["confidence"]
            except Exception:
                pass

        # Always overwrite semantic metadata from description
        meta = _infer_listing_metadata(r.get("description", ""), r.get("state", 41326))
        _SEMANTIC_FIELDS = {
            "temperament_tags", "energy_level", "housing_fit",
            "good_with_children", "good_with_cats", "good_with_dogs",
            "experience_required", "special_needs",
        }
        for k, v in meta.items():
            if k in _SEMANTIC_FIELDS:
                updates[k] = v  # always overwrite
            elif r.get(k) is None and v is not None:
                updates[k] = v  # fill location only if missing

        if updates:
            db.update_listing(r["id"], **updates)
