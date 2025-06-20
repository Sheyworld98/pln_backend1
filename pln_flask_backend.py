from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests
import certifi  # for correct SSL certificate verification

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
    user_id = user_id.strip()
    profiles = load_json("user_profile.json")
    return jsonify(profiles.get(user_id, {}))

@app.route("/profile/update/<user_id>", methods=["POST"])
def update_profile(user_id):
    user_id = user_id.strip()
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
    user_id = user_id.strip()
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
    user_id = user_id.strip()
    history = load_json("user_history.json")
    return jsonify(history.get(user_id, []))

@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    import certifi
    import traceback

    lang = request.args.get("lang", "en")
    topic = request.args.get("topic", None)
    complexity = request.args.get("complexity", None)

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
            verify=certifi.where()
        )
        print("➡️ Fetch task status code:", res.status_code)
        print("➡️ Response text:", res.text)

        if res.status_code != 200:
            return jsonify({"error": "Failed to fetch task", "details": res.text}), 500

        task_list = res.json()

    except Exception as e:
        print("❌ Exception during task fetch:")
        traceback.print_exc()
        return jsonify({"error": "Fetch task exception", "details": str(e)}), 500

    task = next((t for t in task_list if t['id'] not in user_done), None)
    if not task:
        return jsonify({"error": "No new task available"})

    return jsonify(task)


@app.route("/task/<task_id>/submit", methods=["POST", "OPTIONS"])
def submit_answer(task_id):
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS preflight OK"}), 200

    try:
        data = request.get_json(force=True)
        print("Received data:", json.dumps(data, indent=2))

        user_id = data["user_id"].strip()
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

        print("Submission payload:", submission)

    except Exception as e:
        print("Error reading JSON body:", str(e))
        return jsonify({"error": "Invalid JSON body", "details": str(e)}), 400

    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"
        }
        res = requests.post(
            f"https://crowdlabel.tii.ae/api/2025.2/tasks/{task_id}/submit",
            headers=headers,
            json=submission,
            timeout=10,
            verify=certifi.where()
        )

        print("CrowdLabel response status:", res.status_code)
        print("CrowdLabel response text:", res.text)

        if res.status_code != 200:
            return jsonify({
                "error": "Failed to submit to CrowdLabel",
                "details": res.text
            }), 500

        # Save submission locally
        history = load_json("user_history.json")
        history.setdefault(user_id, []).append(submission)
        save_json("user_history.json", history)

        completed = load_json("completed_tasks.json")
        completed.setdefault(user_id, []).append(task_id)
        save_json("completed_tasks.json", completed)

    except requests.exceptions.SSLError as ssl_err:
        print("SSL error:", ssl_err)
        return jsonify({
            "error": "SSL verification failed",
            "details": str(ssl_err)
        }), 500

    except Exception as e:
        print("General submission error:", str(e))
        return jsonify({
            "error": "Submission exception",
            "details": str(e)
        }), 500

    return jsonify({
        "message": "Answer submitted successfully!",
        "confidence": 1.0
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
