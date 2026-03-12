import pandas as pd
import os

df = None

def load_dataset():
    global df
    df_path = "../dataset.csv" if os.path.exists("../dataset.csv") else "dataset.csv"
    df = pd.read_csv(df_path)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop empty/unnamed columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df.loc[:, df.columns != '']

    # Drop rows where user_id is empty or not a valid number
    df = df[df["user_id"].notna()]
    df = df[pd.to_numeric(df["user_id"], errors="coerce").notna()]
    df["user_id"] = df["user_id"].astype(int)

    # Clean text columns
    text_cols = ["city", "locality", "room/roomate", "preferred_gender"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    # Lowercase role column
    df["room/roomate"] = df["room/roomate"].str.lower()

    # Convert numeric columns - handle comma-separated values like "20,000"
    numeric_cols = ["budget_min", "budget_max", "Room_price"]
    for col in numeric_cols:
        if col in df.columns:
            # Remove commas and convert to numeric
            df[col] = df[col].astype(str).str.replace(",", "", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Convert lifestyle and personality columns to numeric
    lifestyle_personality_cols = [
        "openness", "conscientiousness", "extraversion", 
        "agreeableness", "neuroticism",
        "cleanliness", "noise_tolerance", "guests"
    ]
    for col in lifestyle_personality_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Fill remaining numeric NaN
    numeric_cols_all = df.select_dtypes(include='number').columns
    df[numeric_cols_all] = df[numeric_cols_all].fillna(0)

def get_data():
    return df

def generate_training_pairs():
    """
    Generate all valid user-candidate pairs that pass hard filters.
    Returns df_pairs with user_id, candidate_id, features, target_score (heuristic).
    """
    from matching_service import calculate_match
    df = get_data()
    pairs = []
    for i, user_row in df.iterrows():
        for j, cand_row in df.iterrows():
            if user_row['user_id'] == cand_row['user_id']:
                continue
            score = calculate_match(dict(user_row), dict(cand_row))
            if score is not None:
                pairs.append({
                    'user_id': user_row['user_id'],
                    'candidate_id': cand_row['user_id'],
                    'heuristic_score': score,  # Already 0-1
                    'features': compute_feature_vector(user_row, cand_row)
                })
    return pd.DataFrame(pairs)

def compute_feature_vector(user, candidate):
    """
    Numeric feature diffs + derived for MLR X matrix.
    """
    numeric_cols = ["openness", "conscientiousness", "extraversion", 
                    "agreeableness", "neuroticism", "cleanliness", 
                    "noise_tolerance", "guests"]
    diffs = []
    for col in numeric_cols:
        diffs.append(abs(user.get(col, 0) - candidate.get(col, 0)))
    # Price diff
    diffs.append(abs(user.get('Room_price', 0) - candidate.get('Room_price', 0)))
    # Locality score (reuse)
    from matching_service import find_closest_locality
    loc_score, _ = find_closest_locality(user['locality'], candidate['locality'])
    diffs.append(loc_score)
    # Categorical exact match (0/1)
    cat_cols = ["smoking", "drinking", "diet", "pets", "sleep_schedule", "sharing_pref", "cooking", "social_style", "communication"]
    for col in cat_cols:
        diffs.append(1 if user.get(col) == candidate.get(col) else 0)
    return diffs

