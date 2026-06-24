"""
SkillRadar prototype - Flask app.

Run with:  python app.py
Then open: http://localhost:5000

This mirrors the architecture from the SkillRadar pitch deck:
  Query -> Query Expansion -> Vector Search -> Location Filter -> AI Intro Draft

No OpenAI API key or Slack webhook is required - matching uses a real
TF-IDF + cosine similarity search (see matcher.py), and the "Ping" step
shows the AI-drafted message in the UI rather than sending it anywhere.
See matcher.py's module docstring for how to swap in real embeddings
and a real webhook later.
"""

from flask import Flask, render_template, request, jsonify
from matcher import search, describe_distance, draft_intro_message, _load_employees

app = Flask(__name__)

BUILDINGS = ["A", "B", "C"]
FLOORS = [1, 2, 3, 4]


@app.route("/")
def index():
    return render_template("index.html", buildings=BUILDINGS, floors=FLOORS)


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    requester_name = (data.get("name") or "Alice").strip()
    user_building = data.get("building", "A")
    try:
        user_floor = int(data.get("floor", 3))
    except (TypeError, ValueError):
        user_floor = 3

    if not query:
        return jsonify({"error": "Please describe what you're stuck on."}), 400

    results, expanded_query = search(query, user_building=user_building, user_floor=user_floor, top_n=3)

    enriched = []
    for r in results:
        enriched.append({
            **r,
            "distance_label": describe_distance(r, user_building, user_floor),
            "intro_message": draft_intro_message(requester_name, query, r),
        })

    return jsonify({
        "query": query,
        "expanded_terms": [t for t in expanded_query.split() if t.lower() not in query.lower()],
        "results": enriched,
    })


@app.route("/api/employees")
def api_employees():
    """Lets the UI show the underlying mock directory for transparency."""
    return jsonify(_load_employees())


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
