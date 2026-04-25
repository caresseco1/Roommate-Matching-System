#  StayMate — AI-Powered roomate Matching

> Multiple Linear Regression + Pearson Correlation matching engine,
> trained on 300+ Mumbai profiles from your dataset.

---

## 📁 Project Structure

```
staymate/
├── app.py               # Flask app — all routes
├── models.py            # SQLAlchemy models (User, DatasetProfile, Message, etc.)
├── matching.py          # MLR + Pearson correlation engine
├── forms.py             # WTForms
├── load_dataset.py      # Seeds DatasetProfile table from CSV
├── dataset_-4.csv       # Your dataset (place in root)
├── requirements.txt
├── .env.example         # Rename to .env and fill in credentials
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── welcome.html
    ├── signup.html
    ├── login.html
    ├── verify.html
    ├── looking_for.html
    ├── registration.html
    ├── edit_profile.html
    ├── dashboard.html
    ├── matches.html
    ├── profile_dataset.html
    ├── profile.html
    ├── messages.html
    ├── chat.html
    ├── room_requests.html
    ├── notifications.html
    ├── feedback.html
    └── admin_feedback.html
```

---

## 🚀 Setup (First Time)

```bash
# 1. Clone / unzip the project
cd staymate

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your SECRET_KEY and Gmail credentials

# 5. Place your dataset CSV in the project root
#    (it should be named: dataset_-4.csv)

# 6. Create tables and seed the dataset
python load_dataset.py

# 7. Run the app
python app.py
# Visit: http://localhost:5000
```

---

## How the Matching Engine Works

### Step 1 — Feature Encoding (`matching.py → encode_profile`)
Every profile (dataset row or registered user) is encoded into a **23-dimensional numeric vector**:
- Age, gender, sleep schedule, cleanliness, smoking, drinking, diet, pets, guests, WFH, noise tolerance, sharing preference, cooking
- Social style, communication style
- Big Five personality traits (openness, conscientiousness, extraversion, agreeableness, neuroticism)
- Budget min/max (normalised)

### Step 2 — Synthetic Labels for MLR Training
For every pair of profiles, a ground-truth compatibility label (0–1) is generated using domain rules:
- Age gap penalty (>10 years reduces score)
- Sleep schedule overlap
- Lifestyle factor similarity (11 factors)
- Big Five personality closeness
- Budget range overlap

### Step 3 — Multiple Linear Regression
`sklearn.LinearRegression` is fitted on ~5000 random pairwise samples (|vector_A − vector_B| → compatibility label). This lets the model **learn the relative weight of each feature** from the data rather than hardcoding them.

### Step 4 — Pearson Correlation
For each candidate, we compute **Pearson r** between the query user's full feature vector and the candidate's, then map it from [−1, 1] → [0, 1].

### Step 5 — Combined Score
```
final_score = 0.60 × MLR_score + 0.40 × Pearson_score
```

The per-category breakdown (Age / Lifestyle / Personality / Budget / Location) is shown on every profile page.

### Cache Invalidation
The model is cached in memory per process. When a registered user updates their profile, `matching.invalidate_cache()` is called so the next match request re-trains on the full updated dataset.

---

## 🔑 Features

| Feature | Status |
|---|---|
| Email OTP verification | ✅ |
| 5-step onboarding | ✅ |
| MLR + Pearson matching | ✅ |
| 300+ dataset profiles as pool | ✅ |
| Registered users merged into pool | ✅ |
| Full profile pages with score breakdown | ✅ |
| In-app messaging + unread count | ✅ |
| Room requests (send / accept / decline / unmatch) | ✅ |
| Notifications | ✅ |
| Feedback + admin panel | ✅ |
| Responsive mobile design | ✅ |

---

## 🔧 Configuration Notes

- **Mail**: If MAIL_USERNAME / MAIL_PASSWORD are not set, emails are printed to the console (app still works).
- **Dataset**: `load_dataset.py` is idempotent — safe to run multiple times (skips already-loaded rows).
- **Admin panel**: `/admin/feedback` — no auth by default; add `@login_required` if needed.
