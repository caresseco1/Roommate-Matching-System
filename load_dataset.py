"""
load_dataset.py
===============
Run ONCE (or safely re-run; it skips already-loaded rows) to seed the
dataset_profiles table from dataset_-4.csv.

Usage:
    python load_dataset.py
"""

import csv
import os
import re

# ── Bootstrap the Flask app so we get DB access ──────────────────────────────
from app import app
from models import db, DatasetProfile, User
from werkzeug.security import generate_password_hash

WFH_NORM = {
    'never': 'Never',
    '0': 'Never',
    '1 day/week': '1 day/week',
    '2 days/week': '2 days/week',
    '3 days/week': '3 days/week',
    'full-time': 'Full-time',
    'full time': 'Full-time',
}

def normalise_wfh(val):
    if not val:
        return 'Never'
    return WFH_NORM.get(val.strip().lower(), val.strip())


def clean_budget(val):
    if not val:
        return None
    val = str(val).replace(',', '').replace('"', '').strip()
    try:
        return float(val)
    except ValueError:
        return None


DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset -4.csv')


def load():
    with app.app_context():
        db.create_all()
        with open(DATASET_PATH, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            loaded = 0
            skipped = 0
            for row in reader:
                # Skip empty rows (the tail of the CSV)
                if not row.get('user_id') or not row.get('name'):
                    continue

                uid = int(row['user_id'])
                if DatasetProfile.query.filter_by(dataset_row_id=uid).first():
                    skipped += 1
                    continue

                def r(key, default=None):
                    v = row.get(key, '').strip()
                    return v if v and v.lower() not in ('', 'none') else default

                email_val = r('email') or f"user{uid}@staymate.in"
                name_val = r('name') or f"User {uid}"

                # 1. Ensure the user exists in the registered User table
                user = User.query.filter_by(email=email_val).first()
                if not user:
                    user = User(
                        username=name_val,
                        email=email_val,
                        password_hash=generate_password_hash('password123'),
                        is_verified=True,
                        age=int(float(r('age', 25))),
                        gender=r('gender'),
                        occupation=r('occupation'),
                        city=r('city', 'Mumbai'),
                        locality=r('locality'),
                        phone_number=r('phone_number'),
                        sleep_schedule=r('sleep_schedule'),
                        cleanliness=int(float(r('cleanliness', 3))),
                        smoking=r('smoking'),
                        drinking=r('drinking'),
                        diet=r('diet'),
                        pets=r('pets', 'No'),
                        guests=r('guests'),
                        wfh_frequency=normalise_wfh(r('wfh_frequency')),
                        noise_tolerance=r('noise_tolerance'),
                        sharing_pref=r('sharing_pref'),
                        cooking=r('cooking', 'No'),
                        social_style=r('social_style'),
                        communication=r('communication'),
                        openness=int(float(r('openness', 5))),
                        conscientiousness=int(float(r('conscientiousness', 5))),
                        extraversion=int(float(r('extraversion', 5))),
                        agreeableness=int(float(r('agreeableness', 5))),
                        neuroticism=int(float(r('neuroticism', 5))),
                        budget_min=int(clean_budget(r('budget_min')) or 0) or None,
                        budget_max=int(clean_budget(r('budget_max')) or 0) or None,
                        accommodation_type=r('accommodation_type'),
                        preferred_gender=r('preferred_gender'),
                        looking_for=r('room/roomate', 'room')
                    )
                    db.session.add(user)
                    db.session.flush() # Flush to get user.id before assigning below

                # 2. Prevent UNIQUE constraint failure if CSV has duplicate emails
                if DatasetProfile.query.filter_by(original_user_id=user.id).first():
                    skipped += 1
                    continue

                profile = DatasetProfile(
                    dataset_row_id=uid,
                    original_user_id=user.id,
                    name=name_val,
                    email=email_val,
                    age=float(r('age', 25)),
                    gender=r('gender'),
                    occupation=r('occupation'),
                    city=r('city', 'Mumbai'),
                    locality=r('locality'),
                    phone_number=r('phone_number'),
                    sleep_schedule=r('sleep_schedule'),
                    cleanliness=float(r('cleanliness', 3)),
                    smoking=r('smoking'),
                    drinking=r('drinking'),
                    diet=r('diet'),
                    pets=r('pets', 'No'),
                    guests=r('guests'),
                    wfh_frequency=normalise_wfh(r('wfh_frequency')),
                    noise_tolerance=r('noise_tolerance'),
                    sharing_pref=r('sharing_pref'),
                    cooking=r('cooking', 'No'),
                    social_style=r('social_style'),
                    communication=r('communication'),
                    openness=float(r('openness', 5)),
                    conscientiousness=float(r('conscientiousness', 5)),
                    extraversion=float(r('extraversion', 5)),
                    agreeableness=float(r('agreeableness', 5)),
                    neuroticism=float(r('neuroticism', 5)),
                    budget_min=clean_budget(r('budget_min')),
                    budget_max=clean_budget(r('budget_max')),
                    accommodation_type=r('accommodation_type'),
                    preferred_gender=r('preferred_gender'),
                    looking_for=r('room/roomate', 'room'),
                    room_price=clean_budget(r('Room_price')),
                )
                db.session.add(profile)
                loaded += 1

            db.session.commit()
        print(f"✅ Dataset loaded: {loaded} new profiles, {skipped} already existed.")


if __name__ == '__main__':
    load()
