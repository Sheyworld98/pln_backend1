from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import requests

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CROWD_API = "https://crowdlabel.tii.ae/api/2025.2"

# Utils

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
<<<<<<< HEAD
    if not os.path.exists(path):
        return {}
    with open(filename, "r", encoding="utf-8-sig") as f:
=======
    with open(path, encoding="utf-8-sig") as f:
>>>>>>> 0105341 (Integrated CrowdLabel task fetch and submission)
        return json.load(f)

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Routes

@app.route("/users")
def get_users():
    try:
        files = os.listdir(DATA_DIR)
        user_files = [f.replace("_profile.json", "") for f in files if f.endswith("_profile.json")]
        return jsonify(user_files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/profile/<user_id>")
def get_profile(user_id):
    try:
        return jsonify(load_json(f"{user_id}_profile.json"))
    except Exception as e:
        return jsonify({"complexity_level": "N/A", "languages": [], "expertise_domains": []})

@app.route("/score/<user_id>")
def get_score(user_id):
    try:
        data = load_json("score.json")
        return jsonify(data)
    except:
        return jsonify({})

@app.route("/leaderboard")
def get_leaderboard():
    try:
        return jsonify(load_json("leaderboard.json"))
    except:
        return jsonify([])

@app.route("/history/<user_id>")
def get_history(user_id):
    try:
        history = load_json("history.json")
        return jsonify([h for h in history if h.get("user_id") == user_id])
    except:
        return jsonify([])

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    try:
        r = requests.get(f"{CROWD_API}/tasks/pick", params={"lang": "en", "category": "vqa", "type": "true-false"})
        task = r.json()[0]
        task["fetched_by"] = user_id
        return jsonify(task)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/task/submit/<task_id>", methods=["POST"])
def submit_task(task_id):
    try:
        data = request.get_json()
        payload = {
            "track_id": data["track_id"],
            "solution": data["solution"]
        }
        r = requests.post(f"{CROWD_API}/tasks/{task_id}/submit", data=payload)
        result = r.json()

        # Save to history
        history = load_json("history.json")
        history.append({
            "user_id": data["user_id"],
            "timestamp": request.headers.get("X-Timestamp"),
            "question": data.get("question", "N/A"),
            "label": data["solution"],
            "confidence": result.get("confidence", 0),
        })
        save_json("history.json", history)

        # Update score
        score = load_json("score.json")
        score[data["user_id"]] = score.get(data["user_id"], 0) + 10
        save_json("score.json", score)

        # Update leaderboard
        leaderboard = load_json("leaderboard.json")
        updated = False
        for entry in leaderboard:
            if entry["user_id"] == data["user_id"]:
                entry["score"] = score[data["user_id"]]
                updated = True
        if not updated:
            leaderboard.append({"user_id": data["user_id"], "score": score[data["user_id"]]})
        save_json("leaderboard.json", leaderboard)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)





