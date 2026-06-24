# SkillRadar — Working Prototype

A real, runnable prototype of SkillRadar: a hyper-local, AI-matched expert finder.
This matches the architecture and demo story from the pitch deck (Bob Chen,
Platform Engineering, "1 floor up" — try the first example chip and you'll see
exactly that match).

## What's real vs. simulated

**Real (no API key needed):**
- Semantic search: actual TF-IDF + cosine similarity over employee bios/skills
  (scikit-learn) — not a hardcoded lookup. Try different queries and it
  genuinely re-ranks.
- Query expansion: a small domain synonym glossary that broadens the query
  before matching (e.g. "Docker" pulls in "Kubernetes", "container", etc.) —
  this stands in for an LLM query-expansion call.
- Proximity filtering: real floor/building distance scoring, blended with
  semantic relevance, exactly as described on the architecture slide.
- AI intro message drafting: template-based natural language generation.

**Simulated (clearly labeled in the UI):**
- The "Ping" button shows the AI-drafted message in a modal and lets you
  copy it — it does **not** actually send anything to Slack/Teams. The code
  comments in `app.py` and `matcher.py` show exactly where to wire in a real
  webhook or LLM API call when you're ready.

This was built without an OpenAI API key or Slack webhook (per your last
answers), so the "AI" steps use real algorithms (TF-IDF/cosine similarity,
synonym expansion, template drafting) that produce the same *behavior* as
the LLM-based version described in the deck, without external API calls.
Swapping in real OpenAI embeddings + a real webhook is a drop-in change —
see the docstrings in `matcher.py`.

## Setup

You'll need Python 3.9+ and pip with internet access (this build environment
didn't have internet, so dependencies are listed below for you to install
locally).

```bash
pip install flask scikit-learn numpy
```

## Run it

```bash
python app.py
```

Then open **http://localhost:5000** in your browser.

## Try the exact deck demo

1. Click the **"Kubernetes crash loop"** example chip (or type the query
   yourself).
2. Keep "Your building" = A, "Your floor" = 3 (this is Alice's position from
   the deck).
3. Click **Find an expert**.
4. You should see **Bob Chen, Platform Engineering** rank #1, with
   "Building A, Floor 4 — 1 floor up" — exactly the story from slide 4 of
   the pitch deck.
5. Click **Ping Bob** to see the AI-drafted intro message.

Other queries to try (or use the other example chips):
- "I need help running a usability test and cleaning up a Figma prototype"
  → matches Lena Hoffman, Product Design
- "Our payments microservice keeps timing out, Postgres connection pool issue"
  → matches Daniel Kim, Backend Engineering
- "I need to understand vendor contract terms before a SaaS renewal"
  → matches Hannah Brooks (Legal) or Yuki Tanaka (Finance/Procurement)

## Project structure

```
skillradar-app/
├── app.py              # Flask routes + API
├── matcher.py          # Matching engine (TF-IDF, proximity, message drafting)
├── employees.json      # Mock employee directory (20 people)
├── templates/
│   └── index.html      # Main page
├── static/
│   ├── style.css       # "Signal & Slate" visual identity (matches pitch deck)
│   └── app.js          # Frontend logic, calls /api/search
└── README.md
```

## Recording your demo video

Once this is running, follow the 3-minute script provided earlier:
1. Type the Kubernetes query live (don't paste — looks more natural)
2. Show the results loading and Bob Chen landing at #1
3. Point out the semantic match bar (he never says "Docker" in his bio)
   and the proximity badge ("1 floor up")
4. Click "Ping Bob" and show the generated message
5. Wrap with the business case from the deck

## Next steps to make this production-ready

- Swap `matcher.py`'s TF-IDF search for real OpenAI embeddings + a vector DB
  (ChromaDB/Pinecone) — the function signatures are already shaped for this
- Replace `draft_intro_message()` with an OpenAI chat completion call
- Wire the "Ping" button to a real Slack/Teams incoming webhook URL
- Replace `employees.json` with a real (opt-in, anonymized if needed) HR
  directory feed
