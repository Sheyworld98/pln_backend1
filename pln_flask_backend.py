from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

SUPPORTED_LANGUAGES = {"en", "ar"}
SUPPORTED_TOPICS = {
    "animals", "construction-site", "fashion", "garage-workshop",
    "kitchen", "living-room", "medical-field", "music", "office",
    "school", "uae", "underwater"
}
SUPPORTED_COMPLEXITY = {"1", "2", "3", "4"}

# --- Utility Functions ---
def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# --- User Endpoints ---
@app.route("/users")
def users():
    return jsonify(list(load_json("user_profile.json").keys()))

@app.route("/profile/<user_id>")
def profile(user_id):
    return jsonify(load_json("user_profile.json").get(user_id, {}))

@app.route("/profile/update/<user_id>", methods=["POST"])
def update_profile(user_id):
    profiles = load_json("user_profile.json")
    data = request.get_json(force=True)
    profiles.setdefault(user_id, {})
    profiles[user_id]["languages"] = [data.get("lang", "en")]
    profiles[user_id]["expertise_domains"] = [data.get("expertise", "general")]
    profiles[user_id]["complexity_level"] = int(data.get("complexity", 1))
    save_json("user_profile.json", profiles)
    return jsonify({"message": "Profile updated."})

@app.route("/score/<user_id>")
def score(user_id):
    return jsonify({user_id: len(load_json("user_history.json").get(user_id, [])) * 20})

@app.route("/leaderboard")
def leaderboard():
    history = load_json("user_history.json")
    scores = [{"user_id": u, "score": len(h) * 20} for u, h in history.items()]
    scores.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(scores)

@app.route("/history/<user_id>")
def history(user_id):
    return jsonify(load_json("user_history.json").get(user_id, []))

# --- Task Fetching ---
@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic", None)
    complexity = request.args.get("complexity", None)

    # Validate inputs
    if lang not in SUPPORTED_LANGUAGES:
        return jsonify({"error": f"Unsupported language: {lang}"}), 400
    if topic and topic not in SUPPORTED_TOPICS:
        return jsonify({"error": f"Unsupported topic: {topic}"}), 400
    if complexity and complexity not in SUPPORTED_COMPLEXITY:
        return jsonify({"error": f"Unsupported complexity: {complexity}"}), 400

    completed = load_json("completed_tasks.json")
    user_done = set(completed.get(user_id, []))

    params = {"lang": lang}
    if topic:
        params["topic"] = topic
    if complexity:
        params["complexity"] = complexity

    headers = {"X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"}

    try:
        res = requests.get(
            "https://crowdlabel.tii.ae/api/2025.2/tasks/pick",
            params=params,
            headers=headers,
            verify=False  # or certifi.where()
        )
        print("CROWDLABEL RAW RESPONSE:", res.status_code, res.text)

        if res.status_code != 200:
            return jsonify({"error": "Failed to fetch task", "details": res.text}), 500

        task_list = res.json()

        if not isinstance(task_list, list) or not task_list:
            return jsonify({"error": "No tasks available or API issue"}), 500

        task = next((t for t in task_list if t['id'] not in user_done), None)
        if not task:
            return jsonify({"error": "No new task available"}), 200

        return jsonify(task)

    except Exception as e:
        return jsonify({"error": "Exception occurred while fetching task", "details": str(e)}), 500

# --- Task Submission ---
@app.route("/task/<task_id>/submit", methods=["POST"])
def submit_answer(task_id):
    try:
        data = request.get_json(force=True)
        user_id = data["user_id"]
        solution = data["solution"]
        track_id = data["track_id"]
        question = data.get("question", "")

        submission = {
            "track_id": track_id,
            "solution": solution,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d",
        }

        res = requests.post(
            f"https://crowdlabel.tii.ae/api/2025.2/tasks/{task_id}/submit",
            headers=headers,
            data=submission,
            timeout=10,
            verify=False  # SSL bypassed for dev
        )

        if res.status_code != 200:
            return jsonify({
                "error": "Failed to submit to CrowdLabel",
                "details": res.text
            }), 500

        result = res.json()
        confidence = result.get("confidence", 1.0)

        history = load_json("user_history.json")
        history.setdefault(user_id, []).append({
            "id": task_id,
            "track_id": track_id,
            "question": question,
            "label": solution,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        save_json("user_history.json", history)

        completed = load_json("completed_tasks.json")
        completed.setdefault(user_id, []).append(task_id)
        save_json("completed_tasks.json", completed)

        return jsonify({
            "message": "Answer submitted successfully.",
            "confidence": confidence
        })

    except Exception as e:
        return jsonify({
            "error": "Something went wrong",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
