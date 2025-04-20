
# ---------- pln_flask_backend.py ----------
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Helper function to load JSON
def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route("/profile/<user_id>")
def profile(user_id):
    try:
        data = load_json("user_profile.json")
        if data.get("user_id") == user_id:
            return jsonify(data)
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/score/<user_id>")
def score(user_id):
    try:
        data = load_json("score.json")
        return jsonify({user_id: data.get(user_id, 0)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/leaderboard")
def leaderboard():
    try:
        data = load_json("leaderboard.json")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history/<user_id>")
def history(user_id):
    try:
        data = load_json("history.json")
        filtered = [item for item in data if item.get("user_id") == user_id]
        return jsonify(filtered)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


