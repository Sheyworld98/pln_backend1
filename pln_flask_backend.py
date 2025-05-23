﻿from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/users")
def users():
    users_data = load_json("user_profile.json")
    return jsonify(list(users_data.keys()))

@app.route("/profile/<user_id>")
def profile(user_id):
    profiles = load_json("user_profile.json")
    return jsonify(profiles.get(user_id, {}))

@app.route("/profile/update/<user_id>", methods=["POST"])
def update_profile(user_id):
    profiles = load_json("user_profile.json")
    data = request.get_json()
    profiles.setdefault(user_id, {})
    profiles[user_id]["languages"] = [data.get("lang", "en")]
    profiles[user_id]["expertise_domains"] = [data.get("expertise", "general")]
    profiles[user_id]["complexity_level"] = int(data.get("complexity", 1))
    save_json("user_profile.json", profiles)
    return jsonify({"message": "Profile updated."})

@app.route("/score/<user_id>")
def score(user_id):
    history = load_json("user_history.json")
    return jsonify({user_id: len(history.get(user_id, [])) * 20})

@app.route("/leaderboard")
def leaderboard():
    history = load_json("user_history.json")
    scores = [{"user_id": u, "score": len(h) * 20} for u, h in history.items()]
    scores.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(scores)

@app.route("/history/<user_id>")
def history(user_id):
    history = load_json("user_history.json")
    return jsonify(history.get(user_id, []))

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic", None)
    complexity = request.args.get("complexity", None)

    completed = load_json("completed_tasks.json")
    user_done = set(completed.get(user_id, []))

    params = {"lang": lang}
    if topic: params["topic"] = topic
    if complexity: params["complexity"] = complexity

    headers = {"X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"}

    try:
        res = requests.get("https://crowdlabel.tii.ae/api/2025.2/tasks/pick", params=params, headers=headers, verify=False)
        if res.status_code != 200:
            return jsonify({"error": "Failed to fetch task"}), 500
        task_list = res.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    task = next((t for t in task_list if t['id'] not in user_done), None)
    if not task:
        return jsonify({"error": "No new task available"})

    return jsonify(task)

@app.route("/task/submit/<task_id>", methods=["POST"])
def submit_answer(task_id):
    data = request.get_json()
    user_id = data["user_id"]
    solution = data["solution"]
    question = data["question"]
    track_id = data["track_id"]

    submission = {
        "id": task_id,
        "track_id": track_id,
        "question": question,
        "label": solution,
        "confidence": 1.0,
        "timestamp": datetime.utcnow().isoformat()
    }

    completed = load_json("completed_tasks.json")
    completed.setdefault(user_id, []).append(task_id)
    save_json("completed_tasks.json", completed)

    history = load_json("user_history.json")
    history.setdefault(user_id, []).append(submission)
    save_json("user_history.json", history)

    # 🏅 Gamification Logic
    total_tasks = len(history[user_id])
    badge = None
    reward = None

    if total_tasks == 3:
        badge = "silver"
    elif total_tasks == 6:
        badge = "gold"
    elif total_tasks >= 12:
        reward = "https://chatbot.example.com/free-access"

    return jsonify({
        "message": "Answer recorded",
        "confidence": 1.0,
        "badge": badge,
        "reward": reward
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
