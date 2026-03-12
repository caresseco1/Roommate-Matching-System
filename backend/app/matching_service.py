import difflib
from typing import Tuple, Optional, Dict, Any, List
import re
import joblib
import numpy as np
import os

def find_closest_locality(locality1: str, locality2: str) -> Tuple[float, float]:
    """
    Find the closest matching locality between two locality strings.
    Returns a similarity score between 0 and 1.
    Also returns a base locality match bonus.
    """
    if not locality1 or not locality2:
        return 0.0, 0.0
    
    # Normalize: lower, remove extra spaces/punctuation
    norm1 = re.sub(r'[^a-zA-Z0-9\s]', '', locality1.lower()).strip()
    norm2 = re.sub(r'[^a-zA-Z0-9\s]', '', locality2.lower()).strip()
    
    if norm1 == norm2:
        return 1.0, 0.3  # Perfect match bonus
    
    # Fuzzy similarity using difflib
    similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    # Bonus if one is substring of the other (e.g. "New York" and "NY")
    bonus = 0.0
    if norm1 in norm2 or norm2 in norm1:
        bonus = 0.2
    
    return similarity, bonus

def compute_feature_vector(user: Dict[str, Any], candidate: Dict[str, Any]) -> List[float]:
    """
    Compute feature vector for MLR model (19 features).
    """
    numeric_cols = ["openness", "conscientiousness", "extraversion", 
                    "agreeableness", "neuroticism", "cleanliness", 
                    "noise_tolerance", "guests"]
    diffs = []
    for col in numeric_cols:
        diffs.append(abs(user.get(col, 0) - candidate.get(col, 0)))
    # Price diff
    diffs.append(abs(user.get('Room_price', 0) - candidate.get('Room_price', 0)))
    # Locality score
    loc_score, _ = find_closest_locality(user.get('locality', ''), candidate.get('locality', ''))
    diffs.append(loc_score)
    # Categorical matches (0/1)
    cat_cols = ["smoking", "drinking", "diet", "pets", "sleep_schedule", "sharing_pref", "cooking", "social_style", "communication"]
    for col in cat_cols:
        diffs.append(1.0 if user.get(col) == candidate.get(col) else 0.0)
    return diffs

def heuristic_match_score(current_user: Dict[str, Any], candidate: Dict[str, Any]) -> Optional[float]:
    """
    Rule-based heuristic fallback.
    """
    current_role = current_user.get('room/roomate', '').lower()
    cand_role = candidate.get('room/roomate', '').lower()
    
    if current_role == cand_role:
        return None
    
    # Gender
    current_pref = current_user.get('preferred_gender', '').lower()
    cand_gender = candidate.get('gender', '').lower()
    gender_score = 1.0 if not current_pref or current_pref in ['any', cand_gender] else 0.0
    
    # Locality
    loc_sim, loc_bonus = find_closest_locality(current_user.get('locality', ''), candidate.get('locality', ''))
    locality_score = loc_sim * 0.8 + loc_bonus
    
    # Budget
    current_min = current_user.get('budget_min', 0)
    current_max = current_user.get('budget_max', float('inf'))
    cand_price = candidate.get('Room_price', 0)
    budget_overlap = 1.0 if current_min <= cand_price <= current_max else max(0.0, 1 - abs(cand_price - (current_min + current_max)/2) / ((current_max - current_min) * 2 + 1))
    
    # Age
    age_score = 1.0
    if 'age' in current_user and 'age' in candidate and current_user['age'] and candidate['age']:
        age_diff = abs(float(current_user['age']) - float(candidate['age']))
        age_score = max(0.0, 1 - age_diff / 20.0)
    
    # Personality average similarity
    personality_cols = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism', 'cleanliness', 'noise_tolerance', 'guests']
    diffs = [abs(current_user.get(col, 0) - candidate.get(col, 0)) / 10.0 for col in personality_cols]
    personality_score = 1 - sum(diffs) / len(diffs) if diffs else 1.0
    
    total_score = (
        1.0 * 0.1 +
        gender_score * 0.15 +
        locality_score * 0.2 +
        budget_overlap * 0.25 +
        age_score * 0.1 +
        personality_score * 0.2
    )
    return min(1.0, total_score)

_model = None
_scaler = None

def load_mlr_model():
    global _model, _scaler
    try:
        _model = joblib.load('app/model.pkl')
        _scaler = joblib.load('app/scaler.pkl')
        print("MLR model loaded successfully")
    except FileNotFoundError:
        print("MLR model files not found, using heuristic")
        _model = None

def calculate_match(current_user: Dict[str, Any], candidate: Dict[str, Any]) -> Optional[float]:
    """
    Calculate match score: prefer MLR model, fallback to heuristic.
    """
    if _model is None:
        load_mlr_model()
    
    current_role = current_user.get('room/roomate', '').lower()
    cand_role = candidate.get('room/roomate', '').lower()
    if current_role == cand_role:
        return None
    
    if _model is not None:
        features = compute_feature_vector(current_user, candidate)
        features_scaled = _scaler.transform([features])
        mlr_score = float(_model.predict(features_scaled)[0])
        return max(0.0, min(1.0, mlr_score))
    
    # Fallback
    return heuristic_match_score(current_user, candidate)

