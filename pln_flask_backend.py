from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(filename, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_json(filename, data):
    with open(os.path.join(DATA_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@app.route("/users")
def get_users():
    history = load_json("history.json")
    return jsonify(list({entry["user_id"] for entry in history}))

@app.route("/profile/<user_id>")
def get_profile(user_id):
    filename = f"{user_id}_profile.json"
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return jsonify(load_json(filename))
    return jsonify({
        "languages": [],
        "expertise_domains": [],
        "complexity_level": "N/A"
    })

@app.route("/score/<user_id>")
def get_score(user_id):
    return jsonify(load_json("score.json"))

@app.route("/leaderboard")
def get_leaderboard():
    score = load_json("score.json")
    return jsonify([
        {"user_id": uid, "score": pts} for uid, pts in sorted(score.items(), key=lambda x: -x[1])
    ])

@app.route("/history/<user_id>")
def get_history(user_id):
    history = load_json("history.json")
    return jsonify([entry for entry in history if entry["user_id"] == user_id])

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    # Simulate task fetch
    return jsonify({
        "id": "example_task_1",
        "track_id": "track123",
        "task": {
            "text": "Is this image related to fashion?",
            "choices": [{"key": "a", "value": "Yes"}, {"key": "b", "value": "No"}]
        },
        "content": {
            "image": {
                "url": "https://via.placeholder.com/300"
            }
        }
    })

@app.route("/task/submit/<task_id>", methods=["POST"])
def submit_task(task_id):
    data = request.get_json()
    history = load_json("history.json")
    entry = {
        "user_id": data["user_id"],
        "timestamp": request.headers.get("X-Timestamp", datetime.now().isoformat()),
        "task_id": task_id,
        "question": "Is this image related to fashion?",
        "label": data["solution"],
        "confidence": 0.99
    }
    history.append(entry)
    save_json("history.json", history)

    score = load_json("score.json")
    score[data["user_id"]] = score.get(data["user_id"], 0) + 10
    save_json("score.json", score)

    return jsonify({"task_id": task_id, "confidence": 0.99})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
