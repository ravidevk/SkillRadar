// SkillRadar prototype frontend logic.
// Calls /api/search (Flask backend) and renders ranked matches.
// The "Ping" button opens a modal showing the AI-drafted message —
// no real send happens here (see app.py / matcher.py docstrings for
// where to wire in a real Slack/Teams webhook).

const form = document.getElementById("search-form");
const queryEl = document.getElementById("query");
const nameEl = document.getElementById("name");
const buildingEl = document.getElementById("building");
const floorEl = document.getElementById("floor");
const searchBtn = document.getElementById("search-btn");

const resultsSection = document.getElementById("results-section");
const resultsList = document.getElementById("results-list");
const resultsMeta = document.getElementById("results-meta");
const expandedTermsEl = document.getElementById("expanded-terms");
const emptyState = document.getElementById("empty-state");

const modal = document.getElementById("ping-modal");
const modalMessage = document.getElementById("modal-message");
const modalTitle = document.getElementById("modal-title");
const modalClose = document.getElementById("modal-close");
const modalCopy = document.getElementById("modal-copy");

document.querySelectorAll(".example-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    queryEl.value = chip.dataset.example;
    queryEl.focus();
  });
});

function statusClass(status) {
  return "status-" + status.replace(/\s+/g, "-");
}

function scoreBar(label, pct) {
  return `
    <div class="score-bar-group">
      ${label}
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${pct}%"></div></div>
    </div>`;
}

function renderResults(data) {
  resultsList.innerHTML = "";

  if (!data.results || data.results.length === 0) {
    resultsList.innerHTML = `<div class="error-banner">No matches found in the directory for that query.</div>`;
    return;
  }

  resultsMeta.textContent = `${data.results.length} matches for "${data.query}"`;

  if (data.expanded_terms && data.expanded_terms.length > 0) {
    expandedTermsEl.hidden = false;
    expandedTermsEl.innerHTML =
      "Query expanded with: " +
      data.expanded_terms
        .slice(0, 8)
        .map((t) => `<span class="term">${t}</span>`)
        .join("");
  } else {
    expandedTermsEl.hidden = true;
  }

  data.results.forEach((r, i) => {
    const simPct = Math.round(Math.min(r.similarity * 250, 100));
    const proxPct = Math.round((1 / (1 + r.distance)) * 100);

    const card = document.createElement("div");
    card.className = "result-card" + (i === 0 ? " is-top" : "");
    card.innerHTML = `
      <div class="rank-badge">${i + 1}</div>
      <div class="result-main">
        <div class="result-name-row">
          <span class="result-name">${r.name}</span>
          <span class="result-dept">${r.department}</span>
          <span class="status-pill ${statusClass(r.status)}">${r.status}</span>
        </div>
        <p class="result-bio">${r.bio}</p>
        <div class="result-meta-row">
          <span class="pin">&#128205; ${r.distance_label}</span>
          <span>Desk ${r.desk_number}</span>
        </div>
        <div class="score-bars">
          ${scoreBar("Semantic match", simPct)}
          ${scoreBar("Proximity", proxPct)}
        </div>
      </div>
      <div class="result-action">
        <button class="ping-btn" data-idx="${i}">Ping ${r.name.split(" ")[0]} &rarr;</button>
        <span class="final-score-label">score ${r.final_score}</span>
      </div>
    `;
    resultsList.appendChild(card);

    card.querySelector(".ping-btn").addEventListener("click", () => {
      openPingModal(r);
    });
  });
}

function openPingModal(result) {
  modalTitle.textContent = `Ping ${result.name.split(" ")[0]}`;
  modalMessage.textContent = result.intro_message;
  modal.hidden = false;
  modalCopy.dataset.message = result.intro_message;
  modalCopy.textContent = "Copy message";
}

function closeModal() {
  modal.hidden = true;
}
modalClose.addEventListener("click", closeModal);
modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});

modalCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(modalCopy.dataset.message || "");
    modalCopy.textContent = "Copied!";
    setTimeout(() => (modalCopy.textContent = "Copy message"), 1500);
  } catch (e) {
    modalCopy.textContent = "Copy failed — select manually";
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = queryEl.value.trim();
  if (!query) {
    queryEl.focus();
    return;
  }

  emptyState.hidden = true;
  resultsSection.hidden = false;
  resultsList.innerHTML = `<div class="loading-row"><div class="spinner"></div> Searching the directory&hellip;</div>`;
  searchBtn.disabled = true;

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        name: nameEl.value.trim() || "Alice",
        building: buildingEl.value,
        floor: floorEl.value,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      resultsList.innerHTML = `<div class="error-banner">${data.error || "Something went wrong."}</div>`;
      return;
    }

    renderResults(data);
  } catch (err) {
    resultsList.innerHTML = `<div class="error-banner">Could not reach the SkillRadar backend. Is the Flask server running?</div>`;
  } finally {
    searchBtn.disabled = false;
  }
});
