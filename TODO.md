# TODO: Update Roommate Matching System Backend

## Steps to complete:

1. [x] Update requirements.txt - Add Flask-Cors and numpy
2. [x] Update app/__init__.py - Use Flask-Cors, load_dataset(), and match_bp
3. [x] Update app/data_loader.py - Use simple global function approach
4. [x] Update app/matching_service.py - Use calculate_match function
5. [x] Update app/routes.py - Use /matches/<user_id> endpoint
6. [x] Install dependencies: pip install -r requirements.txt
7. [x] Test the application: python run.py

## Additional Improvements Made:

1. [x] Normalize Lifestyle Score - Using proper max differences for each feature (27 total)
2. [x] Add Age Difference Penalty - 10% weight with max(age_score, 0)
3. [x] Penalize Extreme Price Differences More - Using mid_budget * 0.5 divisor
4. [x] Updated Final Score Formula:
   - 35% personality_score
   - 30% lifestyle_score
   - 20% price_score
   - 15% age_score

