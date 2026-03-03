import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculate_match(current_user, candidate):

    # ==========================
    # HARD FILTERS
    # ==========================

    current_role = current_user["room/roomate"]
    candidate_role = candidate["room/roomate"]

    # Strict opposite role
    if current_role == candidate_role:
        return None

    # Same city
    if current_user["city"] != candidate["city"]:
        return None

    # Gender preference
    if current_user["preferred_gender"] != "Any":
        if candidate["gender"] != current_user["preferred_gender"]:
            return None

    # ==========================
    # PRICE / BUDGET MATCH
    # ==========================

    if current_role == "room":  # Needs room
        if not (candidate["Room_price"] >= current_user["budget_min"] and
                candidate["Room_price"] <= current_user["budget_max"]):
            return None
        room_price = candidate["Room_price"]
        mid_budget = (current_user["budget_min"] + current_user["budget_max"]) / 2

    elif current_role == "roommate":  # Has room
        if not (current_user["Room_price"] >= candidate["budget_min"] and
                current_user["Room_price"] <= candidate["budget_max"]):
            return None
        room_price = current_user["Room_price"]
        mid_budget = (candidate["budget_min"] + candidate["budget_max"]) / 2

    else:
        return None

    # ==========================
    # PERSONALITY (30%)
    # ==========================

    vec1 = np.array([
        current_user["openness"],
        current_user["conscientiousness"],
        current_user["extraversion"],
        current_user["agreeableness"],
        current_user["neuroticism"]
    ]).reshape(1, -1)

    vec2 = np.array([
        candidate["openness"],
        candidate["conscientiousness"],
        candidate["extraversion"],
        candidate["agreeableness"],
        candidate["neuroticism"]
    ]).reshape(1, -1)

    personality_score = cosine_similarity(vec1, vec2)[0][0]

    # ==========================
    # LIFESTYLE (30%)
    # ==========================

    numeric_lifestyle = [
        "cleanliness",
        "noise_tolerance",
        "guests"
    ]

    lifestyle_diff = sum(
        abs(current_user[col] - candidate[col])
        for col in numeric_lifestyle
    )

    lifestyle_numeric_score = 1 - (lifestyle_diff / (len(numeric_lifestyle) * 5))

    exact_match_cols = [
        "smoking",
        "drinking",
        "diet",
        "pets",
        "sleep_schedule",
        "sharing_pref",
        "cooking"
    ]

    exact_score = sum(
        current_user[col] == candidate[col]
        for col in exact_match_cols
    ) / len(exact_match_cols)

    lifestyle_score = (lifestyle_numeric_score + exact_score) / 2

    # ==========================
    # FINANCIAL (20%)
    # ==========================

    price_score = 1 - abs(room_price - mid_budget) / max(mid_budget, 1)
    price_score = max(price_score, 0)

    # ==========================
    # LOCALITY BONUS (10%)
    # ==========================

    locality_score = 1 if current_user["locality"] == candidate["locality"] else 0

    # ==========================
    # SOCIAL COMPATIBILITY (10%)
    # ==========================

    social_cols = ["social_style", "communication"]

    social_score = sum(
        current_user[col] == candidate[col]
        for col in social_cols
    ) / len(social_cols)

    # ==========================
    # FINAL SCORE
    # ==========================

    final_score = (
        0.30 * personality_score +
        0.30 * lifestyle_score +
        0.20 * price_score +
        0.10 * locality_score +
        0.10 * social_score
    )

    return round(final_score * 100, 2)