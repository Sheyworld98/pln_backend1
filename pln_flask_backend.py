import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load or initialize data files
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

completed_tasks = load_json("completed_tasks.json")
user_profiles = load_json("user_profiles.json")
labeling_history = load_json("labeling_history.json")

# API settings
API_URL = "https://crowdlabel.tii.ae/api/2025.2"
API_KEY = "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"

@app.route("/users")
def get_users():
    return jsonify(list(user_profiles.keys()))

@app.route("/profile/<user_id>")
def get_profile(user_id):
    return jsonify(user_profiles.get(user_id, {}))

@app.route("/score/<user_id>")
def get_score(user_id):
    return jsonify({user_id: len(completed_tasks.get(user_id, [])) * 10})

@app.route("/leaderboard")
def leaderboard():
    lb = [{"user_id": uid, "score": len(tlist) * 10} for uid, tlist in completed_tasks.items()]
    lb.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(lb)

@app.route("/history/<user_id>")
def history(user_id):
    return jsonify(labeling_history.get(user_id, []))

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic", None)
    complexity = request.args.get("complexity", None)

    completed = load_json("completed_tasks.json")
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

        # Find a task not completed yet
        task = next((t for t in task_list if t['id'] not in user_done), None)
        if not task:
            return jsonify({"error": "No new task available"}), 200  # Important: Still return 200, not 500

        return jsonify(task)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/task/submit/<task_id>", methods=["POST"])
def submit_task(task_id):
    data = request.get_json()
    user_id = data.get("user_id")
    solution = data.get("solution")
    question = data.get("question")
    track_id = data.get("track_id")

    if not user_id or not solution or not track_id:
        return jsonify({"error": "Missing fields"}), 400

    headers = {"X-API-Key": API_KEY}
    payload = {"track_id": track_id, "solution": solution}

    try:
        res = requests.post(f"{API_URL}/tasks/{task_id}/submit", data=payload, headers=headers, verify=False)
        if res.status_code != 200:
            return jsonify({"error": "Submission failed"}), 500
        result = res.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Save completed task
    completed_tasks.setdefault(user_id, []).append(task_id)
    save_json("completed_tasks.json", completed_tasks)

    # Save labeling history
    labeling_history.setdefault(user_id, []).append({
        "timestamp": str(requests.get("https://worldtimeapi.org/api/timezone/Etc/UTC").json()["utc_datetime"]),
        "question": question,
        "label": solution,
        "confidence": result.get("confidence", 1.0)
    })
    save_json("labeling_history.json", labeling_history)

    return jsonify(result)

@app.route("/update_profile/<user_id>", methods=["POST"])
def update_profile(user_id):
    data = request.get_json()
    languages = data.get("languages", ["en"])
    expertise = data.get("expertise", [])
    complexity = data.get("complexity", None)

    user_profiles[user_id] = {
        "languages": languages,
        "expertise_domains": expertise,
        "complexity_level": complexity
    }
    save_json("user_profiles.json", user_profiles)

    return jsonify({"status": "Profile updated"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


