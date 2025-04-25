from flask import Flask, jsonify, request
from flask_cors import CORS
import os, json, random, datetime
import requests

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# === UTILS ===
def load_json(file):
    path = os.path.join(DATA_DIR, file)
    if not os.path.exists(path): return {}
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)

def save_json(data, file):
    path = os.path.join(DATA_DIR, file)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# === ENDPOINTS ===
@app.route("/users")
def get_users():
    history = load_json("history.json")
    return jsonify(sorted(set(entry['user_id'] for entry in history)))

@app.route("/profile/<user_id>")
def get_profile(user_id):
    default = {
        "languages": ["en"],
        "expertise_domains": ["fashion"],
        "complexity_level": 1
    }
    profile = load_json(f"{user_id}_profile.json") or load_json("user_profile.json")
    return jsonify({**default, **profile})

@app.route("/score/<user_id>")
def get_score(user_id):
    score = load_json("score.json")
    return jsonify(score)

@app.route("/leaderboard")
def leaderboard():
    score = load_json("score.json")
    return jsonify(sorted([
        {"user_id": k, "score": v} for k, v in score.items()
    ], key=lambda x: x["score"], reverse=True))

@app.route("/history/<user_id>")
def history(user_id):
    all_history = load_json("history.json")
    return jsonify([entry for entry in all_history if entry['user_id'] == user_id])

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic", "").strip()
    params["topic"] = topic.lower()

    completed = load_json("completed_tasks.json")
    user_done = set(completed.get(user_id, []))

    profile = load_profile(user_id)
    expertise_domains = profile.get("expertise_domains", [])
    complexity = profile.get("complexity_level", 1)

    if not topic and expertise_domains:
        topic = expertise_domains[0]  # fallback to user's expertise

    params = {
        "lang": lang,
        "category": "vqa",
        "type": "true-false",
        "complexity": complexity
    }
    if topic:
        params["topic"] = topic

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
def submit_task(task_id):
    data = request.json
    user_id = data.get("user_id")
    solution = data.get("solution")
    track_id = data.get("track_id")
    timestamp = request.headers.get("X-Timestamp") or datetime.datetime.utcnow().isoformat()

    headers = {"X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"}

    try:
        res = requests.post(
            f"https://crowdlabel.tii.ae/api/2025.2/tasks/{task_id}/submit",
            data={"track_id": track_id, "solution": solution},
            headers=headers,
            verify=False
        )
        if res.status_code != 200:
            return jsonify({"error": "Submission failed"}), 500
        result = res.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history = load_json("history.json")
    history.append({
        "user_id": user_id,
        "task_id": task_id,
        "question": data.get("question"),
        "label": solution,
        "confidence": result.get("confidence", 1.0),
        "timestamp": timestamp
    })
    save_json(history, "history.json")

    completed = load_json("completed_tasks.json")
    completed.setdefault(user_id, []).append(task_id)
    save_json(completed, "completed_tasks.json")

    score = load_json("score.json")
    score[user_id] = score.get(user_id, 0) + 10
    save_json(score, "score.json")

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
