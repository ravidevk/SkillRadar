"""
SkillRadar matching engine.

Mirrors the architecture from the pitch deck:
  Query -> Query Expansion (lightweight synonym expansion) -> Vector Search
  (TF-IDF + cosine similarity, standing in for embeddings) -> Location Filter
  (re-rank by floor/building distance + availability) -> ranked results.

No external API calls are made here. This is a real, working semantic
search (not a hardcoded lookup) - it builds an actual TF-IDF vector space
over employee bios + skills and ranks by cosine similarity, then blends
that with a proximity score. Swap in OpenAI embeddings + a vector DB later
by replacing `embed_corpus` / `score_query` with API calls - the rest of
the pipeline (location re-ranking, message drafting) stays the same.
"""

import json
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = os.path.join(os.path.dirname(__file__), "employees.json")

# Lightweight domain synonym expansion - this stands in for the "LLM query
# expansion" step. A real build would call an LLM to expand intent; this
# gives the same functional behavior (query -> richer query) without an
# API key, using a small hand-built domain glossary relevant to this corpus.
SYNONYM_GROUPS = [
    {"docker", "container", "containers", "containerization", "k8s", "kubernetes",
     "orchestration", "crash", "crashloop", "crash-loop", "pod", "deployment"},
    {"react", "frontend", "typescript", "javascript", "ui", "web", "accessibility"},
    {"go", "golang", "backend", "microservice", "microservices", "database", "postgres", "postgresql"},
    {"security", "vulnerability", "pentest", "penetration", "appsec", "threat"},
    {"figma", "design", "ux", "prototyping", "usability"},
    {"terraform", "ansible", "devops", "incident", "outage", "oncall", "on-call", "production"},
    {"sql", "etl", "airflow", "pipeline", "warehouse", "data engineering"},
    {"ml", "machine learning", "model", "forecasting", "pandas", "python"},
    {"swift", "ios", "mobile", "offline", "sync"},
    {"observability", "monitoring", "uptime", "alert", "sre", "reliability"},
    {"contract", "legal", "compliance", "privacy", "negotiation"},
    {"sales", "demo", "discovery call", "crm", "prospect"},
    {"onboarding", "hris", "internal mobility", "people ops"},
    {"design system", "component library", "tokens"},
    {"procurement", "vendor", "budget", "finance"},
    {"product", "roadmap", "spec", "user story"},
]


def _load_employees():
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def _corpus_text(emp):
    """Flatten an employee record into the text we embed/match against."""
    return f"{emp['bio']} {' '.join(emp['skills'])} {emp['department']}"


def expand_query(query):
    """Cheap stand-in for an LLM query-expansion step.

    Appends related terms from any synonym group the query touches, so a
    query about 'crash loop' and 'Docker' also pulls in 'Kubernetes',
    'orchestration', 'container', etc. - the same intent-broadening effect
    an LLM call would have, without requiring an API key.
    """
    q_lower = query.lower()

    # Word-boundary matching - plain substring checks would false-positive
    # (e.g. "ui" inside "building"), so each term/phrase must match as a
    # whole word or whole phrase.
    def term_in_query(term):
        if " " in term or "-" in term:
            return term in q_lower
        return re.search(r"\b" + re.escape(term) + r"\b", q_lower) is not None

    extra_terms = set()
    for group in SYNONYM_GROUPS:
        if any(term_in_query(term) for term in group):
            extra_terms.update(group)
    expanded = query + " " + " ".join(extra_terms)
    return expanded


def _floor_distance(emp_building, emp_floor, user_building, user_floor):
    """Simple campus distance score: 0 (best) upward."""
    if emp_building != user_building:
        return 10  # different building penalty dominates
    return abs(emp_floor - user_floor)


def _availability_bonus(status):
    return {"Available": 1.0, "In Meeting": 0.4, "Deep Work": 0.2}.get(status, 0.5)


def search(query, user_building="A", user_floor=3, top_n=3):
    """Run the full SkillRadar pipeline and return ranked matches.

    Returns a list of dicts, each augmented with:
      - similarity:   0-1 semantic match score (TF-IDF cosine similarity)
      - distance:     floor-distance proxy (0 = same floor, 10+ = different building)
      - availability: 0-1 availability weight
      - final_score:  blended ranking score actually used to sort results
    """
    employees = _load_employees()
    corpus = [_corpus_text(e) for e in employees]

    expanded_query = expand_query(query)

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus + [expanded_query])
    query_vec = tfidf_matrix[-1]
    doc_vecs = tfidf_matrix[:-1]

    similarities = cosine_similarity(query_vec, doc_vecs)[0]

    results = []
    for emp, sim in zip(employees, similarities):
        dist = _floor_distance(emp["building"], emp["floor"], user_building, user_floor)
        avail = _availability_bonus(emp["status"])

        # Blend: semantic match is a gate, not just a weight. Proximity
        # and availability can re-rank among genuinely relevant matches
        # (pull a "good enough, nearby" match above a "perfect but far
        # away" one - the slide 3 / slide 5 logic from the pitch deck),
        # but they can never promote someone with no real skill relevance
        # over someone who actually matches, just because they're close.
        proximity_score = 1.0 / (1.0 + dist)  # 1.0 same floor, decays with distance
        if sim <= 0.0:
            final_score = 0.0001 * proximity_score  # irrelevant match, floor it
        else:
            final_score = (0.7 * sim) + (0.22 * proximity_score) + (0.08 * avail)

        results.append({
            **emp,
            "similarity": round(float(sim), 4),
            "distance": int(dist),
            "availability_weight": avail,
            "final_score": round(float(final_score), 4),
        })

    results.sort(key=lambda r: r["final_score"], reverse=True)
    return results[:top_n], expanded_query


def describe_distance(emp, user_building, user_floor):
    """Human-readable proximity description for the UI."""
    if emp["building"] != user_building:
        return f"Building {emp['building']} \u2014 different building"
    diff = emp["floor"] - user_floor
    if diff == 0:
        return f"Building {emp['building']}, Floor {emp['floor']} \u2014 same floor"
    direction = "up" if diff > 0 else "down"
    n = abs(diff)
    floor_word = "floor" if n == 1 else "floors"
    return f"Building {emp['building']}, Floor {emp['floor']} \u2014 {n} {floor_word} {direction}"


def draft_intro_message(requester_name, query, match):
    """Stand-in for the 'LLM drafts intro message' step.

    Template-based here (no API key); swap for an OpenAI chat completion
    call later using this same signature.
    """
    first_name = match["name"].split()[0]
    requester_first = requester_name.split()[0] if requester_name else "there"
    # Pull a short topic phrase out of the query for a natural-sounding ping
    topic = re.sub(r"[?.!]+$", "", query.strip())
    if len(topic) > 90:
        topic = topic[:90].rsplit(" ", 1)[0] + "..."
    return (
        f"Hi {first_name}, SkillRadar matched us! I'm {requester_first}, "
        f"and I'm stuck on: \u201C{topic}\u201D. "
        f"Saw you're nearby and available \u2014 got 5 mins for a quick chat?"
    )
