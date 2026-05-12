"""
Matching platform constants and helpers.
Data persistence is handled by db.py; this module holds shared mappings.
"""

ADOPTION_SPEED_LABELS = {
    0: "Top listing — strong demand expected",
    1: "Good listing — good adoption outlook",
    2: "Optimize listing — moderate demand",
    3: "Needs attention — improve photos & description",
    4: "High priority — consider fee reduction or rewrite",
}

ADOPTION_SPEED_EMOJI = {
    0: "⭐⭐⭐⭐⭐",
    1: "⭐⭐⭐⭐",
    2: "⭐⭐⭐",
    3: "⭐⭐",
    4: "⭐",
}

ADOPTION_SPEED_COLORS = {
    0: "#4CAF50",
    1: "#8BC34A",
    2: "#FFC107",
    3: "#FF9800",
    4: "#F44336",
}

COLOR_MAP = {
    0: "None", 1: "Black", 2: "Brown", 3: "Golden",
    4: "Yellow", 5: "Cream", 6: "Gray", 7: "White",
}

GENDER_MAP = {1: "Male", 2: "Female", 3: "Mixed"}
HEALTH_MAP = {1: "Healthy", 2: "Minor Injury", 3: "Serious Injury"}
VACCINATED_MAP = {1: "Yes", 2: "No", 3: "Unknown"}
DEWORMED_MAP = {1: "Yes", 2: "No", 3: "Unknown"}
STERILIZED_MAP = {1: "Yes", 2: "No", 3: "Unknown"}
SIZE_MAP = {0: "N/A", 1: "Small", 2: "Medium", 3: "Large", 4: "XL"}
FUR_MAP = {0: "N/A", 1: "Short", 2: "Medium", 3: "Long"}
TYPE_MAP = {1: "Dog 🐶", 2: "Cat 🐱"}

STATE_MAP = {
    41326: "Selangor", 41401: "Kuala Lumpur", 41415: "Putrajaya",
    41324: "Pahang", 41325: "Johor", 41332: "Kedah", 41327: "Kelantan",
    41335: "Melaka", 41330: "Negeri Sembilan", 41338: "Perak",
    41336: "Penang", 41339: "Perlis", 41342: "Sabah", 41344: "Sarawak",
    41345: "Terengganu", 41347: "Labuan",
}


def speed_badge_html(speed: int, confidence: float) -> str:
    color = ADOPTION_SPEED_COLORS.get(speed, "#999")
    label = ADOPTION_SPEED_LABELS.get(speed, "?")
    emoji = ADOPTION_SPEED_EMOJI.get(speed, "")
    return (
        f"<div style='background:{color};color:white;padding:6px 12px;"
        f"border-radius:8px;text-align:center;display:inline-block;'>"
        f"<b>{emoji} {label}</b> &nbsp;·&nbsp; {confidence:.0%} confidence</div>"
    )
