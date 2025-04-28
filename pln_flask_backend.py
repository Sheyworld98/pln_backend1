from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# File paths
data_dir = "data"
os.makedirs(data_dir, exist_ok=True)
users_file = os.path.join(data_dir, "users.json")
history_file = os.path.join(data_dir, "history.json")
profile_file = os.path.join(data_dir, "profiles.json")
completed_tasks_file = os.path.join(data_dir, "completed_tasks.json")

# Utility functions
def load_json(path, default={}):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    else:
        return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

@app.route("/users")
def get_users():
    users = load_json(users_file, [])
    return jsonify(users)

@app.route("/profile/<user_id>")
def get_profile(user_id):
    profiles = load_json(profile_file)
    return jsonify(profiles.get(user_id, {}))

@app.route("/profile/update/<user_id>", methods=["POST"])
def update_profile(user_id):
    profiles = load_json(profile_file)
    data = request.json
    profile = profiles.get(user_id, {})
    profile["languages"] = [data.get("lang", "en")]
    profile["expertise_domains"] = [data.get("expertise", "")]
    profile["complexity_level"] = data.get("complexity", 1)
    profiles[user_id] = profile
    save_json(profile_file, profiles)
    return jsonify({"status": "Profile updated"})

@app.route("/leaderboard")
def leaderboard():
    history = load_json(history_file)
    scores = {}
    for user, records in history.items():
        scores[user] = len(records) * 10
    sorted_lb = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return jsonify([{"user_id": u, "score": s} for u, s in sorted_lb])

@app.route("/history/<user_id>")
def user_history(user_id):
    history = load_json(history_file)
    return jsonify(history.get(user_id, []))

@app.route("/score/<user_id>")
def get_score(user_id):
    history = load_json(history_file)
    score = len(history.get(user_id, [])) * 10
    return jsonify({user_id: score})

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic")
    complexity = request.args.get("complexity")

    completed = load_json(completed_tasks_file)
    user_done = set(completed.get(user_id, []))

    params = {"lang": lang}
    if topic:
        params["topic"] = topic.lower()
    if complexity:
        params["complexity"] = complexity

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
        "timestamp": datetime.utcnow().isoformat()  # <-- Save UTC timestamp here
    }

    headers = {"X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"}

    res = requests.post(f"https://crowdlabel.tii.ae/api/2025.2/tasks/{task_id}/submit", data={"track_id": track_id, "solution": solution}, headers=headers, verify=False)
    if res.status_code != 200:
        return jsonify({"error": "Failed to submit task"}), 500

    completed = load_json(completed_tasks_file)
    if user_id not in completed:
        completed[user_id] = []
    completed[user_id].append(task_id)
    save_json(completed_tasks_file, completed)

    history = load_json(history_file)
    if user_id not in history:
        history[user_id] = []
    history[user_id].append({
        "timestamp": request.headers.get("Date", "N/A"),
        "question": question,
        "label": solution,
        "confidence": res.json().get("confidence", 1.0)
    })
    save_json(history_file, history)

    return jsonify(res.json())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
