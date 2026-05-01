"""
Seed the database with the first 20 pets from train.csv and their images.
Creates a demo shelter account and populates listings with XGBoost predictions.
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
    One-time backfill: run XGBoost predictions for seeded listings that
    don't have them yet (handles databases seeded before this fix was added).
    """
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT * FROM listings WHERE pet_id IS NOT NULL AND adoption_speed_pred IS NULL"
    ).fetchall()
    conn.close()

    if not rows:
        return

    from frontend.utils.predictions import make_prediction

    for row in rows:
        r = dict(row)
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
                db.update_listing(
                    r["id"],
                    adoption_speed_pred=p0["prediction"],
                    adoption_speed_confidence=p0["confidence"],
                )
        except Exception:
            pass
