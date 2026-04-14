

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error

# ── Encoding maps ────────────────────────────────────────────────────────────

SLEEP_MAP = {'Early bird': 0, 'Flexible': 1, 'Night owl': 2}
NOISE_MAP = {'Low': 0, 'Medium': 1, 'High': 2}
SOCIAL_MAP = {'Introvert': 0, 'Ambivert': 1, 'Extrovert': 2}
COMM_MAP = {'Polite': 0, 'Clear': 1, 'Friendly': 2, 'Direct': 3}
SMOKING_MAP = {'No': 0, 'Occasionally': 1, 'Yes': 2}
DRINKING_MAP = {'Never': 0, 'Socially': 1, 'Often': 2, 'Social': 1, 'Occasionally': 1}
DIET_MAP = {'Veg': 0, 'Vegan': 1, 'Non-Veg': 2}
GUESTS_MAP = {'Rarely': 0, 'Sometimes': 1, 'Often': 2, 'Occasionally': 1}
SHARING_MAP = {'Private': 0, 'Shared': 1}
WFH_MAP = {'Never': 0, '1 day/week': 1, '2 days/week': 2,
           '3 days/week': 3, 'Full-time': 4}
GENDER_MAP = {'Male': 0, 'Female': 1, 'Non-binary': 2}
BOOL_MAP = {'Yes': 1, 'No': 0, 'yes': 1, 'no': 0}


def _safe(mapping, val, default=0):
    if val is None:
        return default
    return mapping.get(str(val).strip(), default)


def encode_profile(p) -> np.ndarray:
    """
    Turn a DatasetProfile ORM object (or dict) into a fixed-length
    numeric feature vector.

    Feature order (28 dims):
      0  age (raw)
      1  gender
      2  sleep_schedule
      3  cleanliness
      4  smoking
      5  drinking
      6  diet
      7  pets
      8  guests
      9  wfh_frequency
      10 noise_tolerance
      11 sharing_pref
      12 cooking
      13 social_style
      14 communication
      15 openness
      16 conscientiousness
      17 extraversion
      18 agreeableness
      19 neuroticism
      20 budget_min  (normalised /100000)
      21 budget_max  (normalised /100000)
      22 same_city   (always 1 for Mumbai dataset; kept for extensibility)
    """
    def g(attr, default=None):
        if isinstance(p, dict):
            return p.get(attr, default)
        return getattr(p, attr, default)

    vec = [
        float(g('age') or 25),
        _safe(GENDER_MAP, g('gender')),
        _safe(SLEEP_MAP, g('sleep_schedule')),
        float(g('cleanliness') or 3),
        _safe(SMOKING_MAP, g('smoking')),
        _safe(DRINKING_MAP, g('drinking')),
        _safe(DIET_MAP, g('diet')),
        _safe(BOOL_MAP, g('pets'), 0),
        _safe(GUESTS_MAP, g('guests')),
        _safe(WFH_MAP, g('wfh_frequency')),
        _safe(NOISE_MAP, g('noise_tolerance')),
        _safe(SHARING_MAP, g('sharing_pref')),
        _safe(BOOL_MAP, g('cooking'), 0),
        _safe(SOCIAL_MAP, g('social_style')),
        _safe(COMM_MAP, g('communication')),
        float(g('openness') or 5),
        float(g('conscientiousness') or 5),
        float(g('extraversion') or 5),
        float(g('agreeableness') or 5),
        float(g('neuroticism') or 5),
        float(g('budget_min') or 10000) / 100000.0,
        float(g('budget_max') or 30000) / 100000.0,
        1.0,   # same_city placeholder
    ]
    return np.array(vec, dtype=float)


def _build_label(va: np.ndarray, vb: np.ndarray, p_a=None, p_b=None):
    """
    Synthetic ground-truth compatibility label (0-1) used to train MLR.
    Combines domain-knowledge rules across feature dimensions.
    """
    # Age: penalise >10 yr gap
    age_diff = abs(va[0] - vb[0])
    age_score = max(0.0, 1 - age_diff / 20.0)

    loc_a = (p_a.locality or '').strip().lower() if p_a else ''
    loc_b = (p_b.locality or '').strip().lower() if p_b else ''
    loc_score = 1.0 if loc_a and loc_b and loc_a == loc_b else 0.0
    pref_gender_score = 1.0 if p_b and p_a and p_b.preferred_gender == p_a.gender else 0.0
    rev_pref_gender_score = 1.0 if p_a and p_b and p_a.preferred_gender == p_b.gender else 0.0
    pref_gender_avg = (pref_gender_score + rev_pref_gender_score) / 2.0

    # Sleep schedule compatibility (exact match = 1, adjacent = 0.5, opposite = 0)
    sleep_diff = abs(va[2] - vb[2])
    sleep_score = [1.0, 0.5, 0.0][int(min(sleep_diff, 2))]

    # Lifestyle factors (3-12): mean of 1 - |diff| / max_range
    ranges = [2, 2, 2, 1, 2, 4, 2, 1, 1, 3, 1]  # max possible diffs
    lifestyle_scores = []
    for i, max_r in zip(range(3, 14), ranges):
        d = abs(va[i] - vb[i])
        lifestyle_scores.append(max(0.0, 1 - d / max_r))
    lifestyle_score = float(np.mean(lifestyle_scores))

    # Big Five (15-19): Pearson-like similarity
    big5_a = va[15:20]
    big5_b = vb[15:20]
    big5_score = float(np.mean(np.maximum(0, 1 - np.abs(big5_a - big5_b) / 10.0)))

    # Budget overlap
    bmin_a, bmax_a = va[20] * 100000, va[21] * 100000
    bmin_b, bmax_b = vb[20] * 100000, vb[21] * 100000
    overlap = max(0, min(bmax_a, bmax_b) - max(bmin_a, bmin_b))
    budget_range = max(bmax_a - bmin_a, bmax_b - bmin_b, 1)
    budget_score = min(1.0, overlap / budget_range)

    # Weighted combination for MLR training.
    # We remove loc_score and pref_gender_score because they are categorical dealbreakers
    # already handled perfectly in get_matches(), and are not encoded in the feature vector.
    label = (
        0.20 * budget_score +      # 20%
        0.40 * lifestyle_score +   # 40%
        0.40 * big5_score          # 40%
    )

    return float(np.clip(label, 0, 1))


# ── Model cache ──────────────────────────────────────────────────────────────

_mlr_model: LinearRegression | None = None
_scaler: MinMaxScaler | None = None
_dataset_vectors: list[tuple] | None = None   # list of (profile, np.ndarray)


def _get_model_and_data(profiles):
    """
    Lazily train / return the cached MLR model.
    profiles: list of DatasetProfile ORM objects
    """
    global _mlr_model, _scaler, _dataset_vectors

    if _mlr_model is not None and _dataset_vectors is not None:
        return _mlr_model, _scaler, _dataset_vectors

    vecs = [(p, encode_profile(p)) for p in profiles]

    # Build pairwise training data
    X_train, y_train = [], []
    n = len(vecs)
    # Use up to 5000 pairs to keep training fast
    import random
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    if len(pairs) > 5000:
        pairs = random.sample(pairs, 5000)

    for i, j in pairs:
        pa, va = vecs[i]
        pb, vb = vecs[j]
        diff_vec = np.abs(va - vb)
        label = _build_label(va, vb, p_a=pa, p_b=pb)
        X_train.append(diff_vec)
        y_train.append(label)

    X = np.array(X_train)
    y = np.array(y_train)

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    # Calculate and log the R^2 (Accuracy) score
    r2 = model.score(X_scaled, y)
    
    # Calculate Mean Absolute Error to see the actual % error margin
    mae = mean_absolute_error(y, model.predict(X_scaled))
    print(f"[Matching Engine] MLR Model trained on {len(X_scaled)} pairs. R^2 Score: {r2:.4f} | MAE: {mae:.4f}")

    _mlr_model = model
    _scaler = scaler
    _dataset_vectors = vecs
    return model, scaler, vecs


def _pearson_sim(va: np.ndarray, vb: np.ndarray) -> float:
    """Pearson correlation clipped to [0, 1]."""
    if np.std(va) == 0 or np.std(vb) == 0:
        return 0.5
    r, _ = pearsonr(va, vb)
    return float(np.clip((r + 1) / 2, 0, 1))   # map [-1,1] → [0,1]


def get_matches(current_user, profiles, top_n=20, sort_by='compatibility'):
    """
    Return top_n matches for current_user from profiles list.

    Each match is a dict:
      {
        'profile':  DatasetProfile ORM object,
        'mlr_score': float 0-1,
        'pearson_score': float 0-1,
        'final_score': float 0-100 (percent),
        'breakdown': dict of per-category scores
      }
    """
    if not profiles:
        return []

    model, scaler, dataset_vecs = _get_model_and_data(profiles)

    user_vec = encode_profile(current_user)
    results = []

    # Pre-extract user dealbreaker fields
    user_bmin = float(current_user.budget_min or 0)
    user_bmax = float(current_user.budget_max or 1000000)
    user_pref_gen = (current_user.preferred_gender or 'Any').strip().lower()
    user_gen = (current_user.gender or '').strip().lower()
    user_looking = (current_user.looking_for or 'room').strip().lower()

    for profile, pvec in dataset_vecs:
        # Skip self
        if (hasattr(profile, 'original_user_id') and
                profile.original_user_id == current_user.id):
            continue

        # --- STRICT DEALBREAKER FILTERS ---
        # 1. Budget Overlap Check
        p_bmin = float(profile.budget_min or 0)
        p_bmax = float(profile.budget_max or 1000000)
        if min(user_bmax, p_bmax) < max(user_bmin, p_bmin):
            continue  # No budget overlap
            
        # 2. Gender Preference Check
        p_pref_gen = (profile.preferred_gender or 'Any').strip().lower()
        p_gen = (profile.gender or '').strip().lower()
        if user_pref_gen not in ['any', ''] and user_pref_gen != p_gen:
            continue
        if p_pref_gen not in ['any', ''] and p_pref_gen != user_gen:
            continue
            
        # 3. Looking For Check (Prevents two people who already have rooms from matching)
        p_looking = (profile.looking_for or 'room').strip().lower()
        if user_looking == 'roomate' and p_looking == 'roomate':
            continue

        diff_vec = np.abs(user_vec - pvec)
        diff_scaled = scaler.transform([diff_vec])
        mlr_raw = float(model.predict(diff_scaled)[0])
        mlr_score = float(np.clip(mlr_raw, 0, 1))

        pearson_score = _pearson_sim(user_vec, pvec)

# Combined: 40% MLR, 60% Pearson (user requested)
        final = 0.40 * mlr_score + 0.60 * pearson_score

        # Per-category breakdown for UI display
        breakdown = _breakdown(current_user, profile)

        results.append({
            'profile': profile,
            'mlr_score': round(mlr_score * 100, 1),
            'pearson_score': round(pearson_score * 100, 1),
            'final_score': round(final * 100, 1),
            'breakdown': breakdown,
        })

    results.sort(key=lambda x: x['final_score'], reverse=True)
    
    user_loc = (current_user.locality or '').strip().lower()
    
    high_score_local = []
    high_score_other = []
    
    for m in results:
        if m['final_score'] >= 60:
            m_loc = (m['profile'].locality or '').strip().lower()
            if user_loc and m_loc == user_loc:
                high_score_local.append(m)
            else:
                high_score_other.append(m)
                
    combined_matches = high_score_local + high_score_other
    
    if not combined_matches:
        combined_matches = results
        limit = 10 if top_n > 10 else top_n
    else:
        limit = top_n
        
    # Apply sorting
    if sort_by == 'score_high':
        combined_matches.sort(key=lambda x: x['final_score'], reverse=True)
    elif sort_by == 'score_low':
        combined_matches.sort(key=lambda x: x['final_score'])
    elif sort_by == 'budget_low':
        combined_matches.sort(key=lambda x: float(x['profile'].budget_min or 0))
    elif sort_by == 'budget_high':
        combined_matches.sort(key=lambda x: float(x['profile'].budget_max or 0), reverse=True)
    elif sort_by == 'age_closest':
        user_age = float(current_user.age or 25)
        combined_matches.sort(key=lambda x: abs(float(x['profile'].age or 25) - user_age))
        
    return combined_matches[:limit]


def get_compatibility(user_a, user_b, profiles=None) -> dict:
    """Full compatibility report between two users (for profile view page)."""
    va = encode_profile(user_a)
    vb = encode_profile(user_b)
    diff_vec = np.abs(va - vb)

    # Use the trained MLR model to ensure scores match the dashboard exactly
    global _mlr_model, _scaler
    if _mlr_model is not None and _scaler is not None:
        diff_scaled = _scaler.transform([diff_vec])
        mlr_score = float(np.clip(float(_mlr_model.predict(diff_scaled)[0]), 0, 1))
    elif profiles is not None:
        model, scaler, _ = _get_model_and_data(profiles)
        diff_scaled = scaler.transform([diff_vec])
        mlr_score = float(np.clip(float(model.predict(diff_scaled)[0]), 0, 1))
    else:
        # Fallback: pure rule-based
        mlr_score = _build_label(va, vb, p_a=user_a, p_b=user_b)

    pearson = _pearson_sim(va, vb)
    final = 0.40 * mlr_score + 0.60 * pearson

    breakdown = _breakdown(user_a, user_b)
    return {
        'mlr_score': round(mlr_score * 100, 1),
        'pearson_score': round(pearson * 100, 1),
        'final_score': round(final * 100, 1),
        'breakdown': breakdown,
    }


def _breakdown(a, b) -> dict:
    """Human-readable per-category compatibility breakdown."""
    def g(obj, attr, default=None):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    # Age
    age_diff = abs((g(a, 'age') or 25) - (g(b, 'age') or 25))
    age_score = max(0, 100 - age_diff * 5)

    # Lifestyle
    lifestyle_fields = [
        ('sleep_schedule', SLEEP_MAP, 2),
        ('smoking', SMOKING_MAP, 2),
        ('drinking', DRINKING_MAP, 2),
        ('diet', DIET_MAP, 2),
        ('guests', GUESTS_MAP, 2),
        ('noise_tolerance', NOISE_MAP, 2),
        ('wfh_frequency', WFH_MAP, 4),
    ]
    ls_scores = []
    for field, mapping, max_r in lifestyle_fields:
        va_v = _safe(mapping, g(a, field))
        vb_v = _safe(mapping, g(b, field))
        ls_scores.append(max(0, 1 - abs(va_v - vb_v) / max_r))
    lifestyle_score = round(float(np.mean(ls_scores)) * 100, 1)

    # Personality Big Five
    big5 = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    b5_scores = []
    for trait in big5:
        va_v = float(g(a, trait) or 5)
        vb_v = float(g(b, trait) or 5)
        b5_scores.append(max(0, 1 - abs(va_v - vb_v) / 10))
    personality_score = round(float(np.mean(b5_scores)) * 100, 1)

    # Budget
    bmin_a = float(g(a, 'budget_min') or 10000)
    bmax_a = float(g(a, 'budget_max') or 30000)
    bmin_b = float(g(b, 'budget_min') or 10000)
    bmax_b = float(g(b, 'budget_max') or 30000)
    overlap = max(0, min(bmax_a, bmax_b) - max(bmin_a, bmin_b))
    budget_range = max(bmax_a - bmin_a, bmax_b - bmin_b, 1)
    budget_score = round(min(1.0, overlap / budget_range) * 100, 1)

    # Locality bonus
    loc_a = (g(a, 'locality') or '').strip().lower()
    loc_b = (g(b, 'locality') or '').strip().lower()
    loc_score = 100.0 if loc_a and loc_b and loc_a == loc_b else 50.0

    return {
        'age': age_score,
        'lifestyle': lifestyle_score,
        'personality': personality_score,
        'budget': budget_score,
        'location': loc_score,
    }


def invalidate_cache():
    """Call this when new profiles are added so model is re-trained."""
    global _mlr_model, _scaler, _dataset_vectors
    _mlr_model = None
    _scaler = None
    _dataset_vectors = None
