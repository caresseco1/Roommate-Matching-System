import pandas as pd

df = None

def load_dataset():
    global df
    df = pd.read_csv("dataset.csv")

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
