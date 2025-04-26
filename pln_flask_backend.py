from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import requests

app = Flask(__name__)
CORS(app)

DATA_DIR = "./"
API_KEY = "OkYLZD1-ZF0e9WV1wI5Naela5HhyVC6d"
CROWDLABEL_BASE = "https://crowdlabel.tii.ae/api/2025.2"


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@app.route("/users")
def get_users():
    return jsonify(list(load_json("user_profile.json").keys()))


@app.route("/profile/<user_id>")
def get_profile(user_id):
    filename = "user_profile.json"
    return jsonify(load_json(filename).get(user_id, {}))


@app.route("/score/<user_id>")
def get_score(user_id):
    scores = load_json("user_scores.json")
    return jsonify({user_id: scores.get(user_id, 0)})


@app.route("/leaderboard")
def leaderboard():
    scores = load_json("user_scores.json")
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return jsonify([{"user_id": uid, "score": score} for uid, score in sorted_scores])


@app.route("/history/<user_id>")
def history(user_id):
    history = load_json("labeling_history.json")
    return jsonify(history.get(user_id, []))


@app.route("/task/fetch/<user_id>")
def fetch_task(user_id):
    lang = request.args.get("lang", "en")
    topic = request.args.get("topic")
    complexity = request.args.get("complexity")

    profile = load_json("user_profile.json").get(user_id, {})
    completed = load_json("completed_tasks.json")
    user_done = set(completed.get(user_id, []))

    params = {"lang": lang}
    if topic:
        params["topic"] = topic.lower()
    elif profile.get("expertise_domains"):
        params["topic"] = profile["expertise_domains"][0].lower()

    if complexity:
        try:
            params["complexity"] = int(complexity)
        except ValueError:
            pass
    elif profile.get("complexity_level"):
        params["complexity"] = profile["complexity_level"]

    headers = {"X-API-Key": API_KEY}

    try:
        res = requests.get(f"{CROWDLABEL_BASE}/tasks/pick", params=params, headers=headers, verify=False)
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
    question = data.get("question")
    track_id = data.get("track_id")

    headers = {"X-API-Key": API_KEY}
    payload = {"solution": solution, "track_id": track_id}
    try:
        res = requests.post(f"{CROWDLABEL_BASE}/tasks/{task_id}/submit", data=payload, headers=headers, verify=False)
        result = res.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Save history
    history = load_json("labeling_history.json")
    user_hist = history.setdefault(user_id, [])
    user_hist.append({"timestamp": request.date, "question": question, "label": solution, "confidence": result.get("confidence", 0)})
    save_json("labeling_history.json", history)

    # Save completed tasks
    completed = load_json("completed_tasks.json")
    completed.setdefault(user_id, []).append(task_id)
    save_json("completed_tasks.json", completed)

    # Update score
    scores = load_json("user_scores.json")
    scores[user_id] = scores.get(user_id, 0) + int(result.get("confidence", 0) * 100)
    save_json("user_scores.json", scores)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

