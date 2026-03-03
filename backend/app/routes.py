from flask import Blueprint, jsonify
from app.data_loader import get_data
from app.matching_service import calculate_match

match_bp = Blueprint("match_bp", __name__)

@match_bp.route("/matches/<int:user_id>", methods=["GET"])
def get_matches(user_id):

    df = get_data()

    if user_id not in df["user_id"].values:
        return jsonify({"error": "User not found"}), 404

    current_user = df[df["user_id"] == user_id].iloc[0]

    results = []

    for _, candidate in df.iterrows():

        if candidate["user_id"] == user_id:
            continue

        score = calculate_match(current_user, candidate)

        if score is not None:
            results.append({
                "user_id": int(candidate["user_id"]),
                "name": candidate["name"],
                "city": candidate["city"],
                "locality": candidate["locality"],
                "room_price": candidate.get("Room_price", None),
                "score": score
            })

    top_matches = sorted(results, key=lambda x: x["score"], reverse=True)[:10]

    return jsonify(top_matches)