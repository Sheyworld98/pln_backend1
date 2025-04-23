from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
from datetime import datetime
import random

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def read_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return default or {}

@app.route("/profile/<user_id>")
def get_profile(user_id):
    filename = f"{user_id}_profile.json"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({
            "languages": [],
            "expertise_domains": [],
            "complexity_level": "N/A"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/score/<user_id>")
def get_score(user_id):
    scores = read_json("score.json", {})
    return jsonify({user_id: scores.get(user_id, 0)})

@app.route("/leaderboard")
def get_leaderboard():
    data = read_json("leaderboard.json", [])
    return jsonify(sorted(data, key=lambda x: -x["score"]))

@app.route("/history/<user_id>")
def get_history(user_id):
    all_history = read_json("history.json", [])
    user_history = [h for h in all_history if h.get("user_id") == user_id]
    return jsonify(user_history)

@app.route("/users")
def list_users():
    files = os.listdir(DATA_DIR)
    user_ids = [f.replace("_profile.json", "") for f in files if f.endswith("_profile.json")]
    return jsonify(user_ids)

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    # Simulated sample task since API isn't available
    task = {
        "id": "example-task-123",
        "track_id": "track-abc",
        "category": "vqa",
        "complexity": 1,
        "type": "true-false",
        "topic": "fashion",
        "language": "en",
        "content": {
            "image": {
                "url": "https://via.placeholder.com/300x200"
            }
        },
        "task": {
            "text": "Is this image related to fashion?",
            "choices": [
                {"key": "a", "value": "Yes"},
                {"key": "b", "value": "No"}
            ]
        }
    }
    return jsonify(task)

@app.route("/task/submit/<task_id>", methods=["POST"])
def submit_task(task_id):
    data = request.json
    user_id = data.get("user_id")
    solution = data.get("solution")
    track_id = data.get("track_id")
    confidence = round(random.uniform(0.95, 1.0), 2)

    new_entry = {
        "user_id": user_id,
        "task_id": task_id,
        "track_id": track_id,
        "label": solution,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
        "question": "Is this image related to fashion?"  # Optional for frontend
    }

    history = read_json("history.json", [])
    history.append(new_entry)
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    score = read_json("score.json", {})
    score[user_id] = score.get(user_id, 0) + 10
    with open("score.json", "w", encoding="utf-8") as f:
        json.dump(score, f, indent=2)

    leaderboard = read_json("leaderboard.json", [])
    found = False
    for entry in leaderboard:
        if entry["user_id"] == user_id:
            entry["score"] = score[user_id]
            found = True
            break
    if not found:
        leaderboard.append({"user_id": user_id, "score": score[user_id]})
    with open("leaderboard.json", "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)

    return jsonify({"task_id": task_id, "confidence": confidence})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

