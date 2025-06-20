from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

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
    return jsonify({user_id: 0})  # No longer tracked

@app.route("/leaderboard")
def leaderboard():
    return jsonify([])  # No leaderboard logic needed

@app.route("/history/<user_id>")
def history(user_id):
    return jsonify([])  # No local history

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic", None)
    complexity = request.args.get("complexity", None)

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
            verify=False
        )
        if res.status_code != 200:
            return jsonify({"error": "Failed to fetch task"}), 500
        task_list = res.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Just return the first task (no filtering)
    if not task_list:
        return jsonify({"error": "No new task available"})

    return jsonify(task_list[0])

@app.route("/task/<task_id>/submit", methods=["POST", "OPTIONS"])
def submit_answer(task_id):
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS preflight OK"}), 200

    try:
        data = request.get_json(force=True)
        print("Received data:", json.dumps(data, indent=2))

        user_id = data["user_id"]
        solution = data["solution"]
        question = data["question"]
        track_id = data["track_id"]
    except Exception as e:
        print("Error reading JSON body:", str(e))
        return jsonify({"error": "Invalid JSON body"}), 400

    submission = {
        "id": task_id,
        "track_id": track_id,
        "question": question,
        "label": solution,
        "confidence": 1.0,
        "timestamp": datetime.utcnow().isoformat()
    }

    print("Submission payload:", submission)

    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"
        }
        res = requests.post(
    f"https://crowdlabel.tii.ae/api/2025.2/tasks/{task_id}/submit",
    headers=headers,
    json=submission,
    verify=False
)

print("CrowdLabel submission response:", res.status_code, res.text)  # 👈 Add this

if res.status_code != 200:
    print("CrowdLabel submission failed:", res.status_code, res.text)
    return jsonify({"error": "Failed to submit to CrowdLabel"}), 500


    return jsonify({
        "message": "Answer submitted successfully!",
        "confidence": 1.0
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
