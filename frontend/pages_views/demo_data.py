"""
Demo data for the marketplace.

This is intentionally separate from `frontend/utils/matching_platform.py` (which
holds the production data model) so that we can rapidly tweak the pitch demo
without touching the schema Simon's Listing Agent is built against.

Replace this with real database reads once persistence is wired up.
"""
from dataclasses import dataclass


@dataclass
class DemoPet:
    name: str
    breed: str
    species: str        # "Dog" or "Cat"
    age_years: float
    gender: str
    weight_kg: float
    location: str
    description: str
    match_score: int    # 0–100, used for the adopter-facing match badge
    health: str
    fee_eur: int
    energy: str
    good_with: str
    shelter_name: str
    shelter_verified: bool
    listed_days_ago: int
    placeholder_index: int


DEMO_PETS: list[DemoPet] = [
    DemoPet(
        name="Buddy",
        breed="Border Collie",
        species="Dog",
        age_years=2,
        gender="Male",
        weight_kg=18,
        location="Lisbon",
        description="Playful, friendly, loves long walks",
        match_score=94,
        health="Vaccinated, Sterilized",
        fee_eur=80,
        energy="High",
        good_with="Kids, Other dogs",
        shelter_name="Patas Amigas Lisboa",
        shelter_verified=True,
        listed_days_ago=3,
        placeholder_index=0,
    ),
    DemoPet(
        name="Luna",
        breed="Tabby",
        species="Cat",
        age_years=1,
        gender="Female",
        weight_kg=4,
        location="Porto",
        description="Calm, affectionate, indoor cat",
        match_score=88,
        health="Vaccinated, Sterilized",
        fee_eur=40,
        energy="Low",
        good_with="Adults, Quiet homes",
        shelter_name="Animais do Porto",
        shelter_verified=True,
        listed_days_ago=7,
        placeholder_index=1,
    ),
    DemoPet(
        name="Max",
        breed="Mixed Breed",
        species="Dog",
        age_years=3,
        gender="Male",
        weight_kg=22,
        location="Lisbon",
        description="Active, loyal, great with kids",
        match_score=82,
        health="Vaccinated, Dewormed",
        fee_eur=60,
        energy="Medium",
        good_with="Kids, Active families",
        shelter_name="Patas Amigas Lisboa",
        shelter_verified=True,
        listed_days_ago=12,
        placeholder_index=2,
    ),
    DemoPet(
        name="Whiskers",
        breed="Persian",
        species="Cat",
        age_years=4,
        gender="Female",
        weight_kg=4.5,
        location="Cascais",
        description="Quiet, gentle, loves cuddles",
        match_score=76,
        health="Vaccinated, Sterilized",
        fee_eur=50,
        energy="Low",
        good_with="Calm households",
        shelter_name="Cascais Pet Rescue",
        shelter_verified=True,
        listed_days_ago=18,
        placeholder_index=3,
    ),
]


def get_pet_by_name(name: str) -> DemoPet | None:
    for pet in DEMO_PETS:
        if pet.name == name:
            return pet
    return None
