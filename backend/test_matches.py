"""
Test script to find matches for a user using the matching algorithm.
Shows quality breakdown: L=Locality%, B=Budget%, P=Personality%, G=Gender match.
"""
import pandas as pd
from app.data_loader import load_dataset, get_data
from app.matching_service import calculate_match, find_closest_locality

def find_matches_for_user(user_id, top_n=10):
    """
    Find the top N matches for a given user_id.
    """
    # Load data
    load_dataset()
    df = get_data()
    
    # Find the current user
    if user_id not in df["user_id"].values:
        print(f"User with user_id {user_id} not found!")
        return
    
    current_user = df[df["user_id"] == user_id].iloc[0]
    
    print(f"\n{'='*80}")
    print(f"Finding MLR matches for: {current_user['name']}")
    print(f"User ID: {current_user['user_id']}")
    print(f"City: {current_user['city']}")
    print(f"Locality: {current_user['locality']}")
    print(f"Role: {current_user['room/roomate']} (looking for {current_user['room/roomate'] == 'room' and 'roommate' or 'room'})")
    print(f"Budget: {current_user['budget_min']} - {current_user['budget_max']}")
    print(f"Preferred Gender: {current_user['preferred_gender']}")
    print(f"{'='*80}\n")
    
    results = []
    
    for _, candidate in df.iterrows():
        # Skip the same user
        if candidate["user_id"] == user_id:
            continue
        
        # Calculate match score
        score = calculate_match(current_user, candidate)
        
        if score is not None:
            results.append({
                "user_id": int(candidate["user_id"]),
                "name": candidate["name"],
                "city": candidate["city"],
                "locality": candidate["locality"],
                "room_price": candidate.get("Room_price", None),
                "role": candidate["room/roomate"],
                "score": score
            })
    
    # Sort by score (highest first)
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    
    # Print top matches with breakdown
    print(f"Top {top_n} MLR Matches (L=Locality% B=Budget% P=Personality% G=Gender):\n")
    print(f"{'Rank':<5} {'Name':<25} {'Locality':<20} {'Role':<10} {'Price':<12} {'Score':<8} {'Breakdown':<25}")
    print("-" * 110)
    
    for i, match in enumerate(results[:top_n], 1):
        price = f"₹{match['room_price']:,.0f}" if match['room_price'] else "N/A"
        cand_data = df[df['user_id'] == match['user_id']].iloc[0]
        
        # Breakdown calculations
        loc_sim, _ = find_closest_locality(current_user['locality'], match['locality'])
        loc_pct = loc_sim * 100
        
        current_min = current_user['budget_min']
        current_max = current_user['budget_max']
        budget_match = 1.0
        if match['room_price'] is not None:
            if current_min <= match['room_price'] <= current_max:
                budget_match = 1.0
            else:
                budget_match = max(0, 1 - abs(match['room_price'] - (current_min + current_max)/2) / ((current_max - current_min) * 0.5 + 1000))
        budget_pct = budget_match * 100
        
        # Personality similarity
        pers_cols = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism', 'cleanliness', 'noise_tolerance', 'guests']
        pers_sim = 0
        for col in pers_cols:
            v1 = current_user.get(col, 5)
            v2 = cand_data.get(col, 5)
            pers_sim += (10 - abs(v1 - v2)) / 10
        pers_sim /= len(pers_cols)
        pers_pct = pers_sim * 100
        
        # Gender
        gender_match = 'Yes' if current_user.get('preferred_gender', 'Any') in ['Any', cand_data.get('gender', '')] else 'No'
        
        breakdown = f"L:{loc_pct:2.0f}% B:{budget_pct:2.0f}% P:{pers_pct:2.0f}% G:{gender_match}"
        print(f"{i:<5} {match['name']:<25} {match['locality']:<20} {match['role']:<10} {price:<12} {match['score']:<8.2f} {breakdown:<25}")
    
    print(f"\n{'='*80}")
    print(f"Total candidates evaluated: {len(results)} (MLR model used)")
    print(f"{'='*80}")
    
    return results[:top_n]

if __name__ == "__main__":
    # Ask user for user_id input
    user_id_input = input("Enter user ID to find matches: ")
    
    try:
        user_id = int(user_id_input)
    except ValueError:
        print("Invalid user ID. Please enter a numeric value.")
        exit(1)
    
    matches = find_matches_for_user(user_id=user_id, top_n=15)

