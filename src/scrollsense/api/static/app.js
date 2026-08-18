// ScrollSense Frontend Interaction Controller

const API_BASE = window.location.origin;

let feedReels = [];
let currentReelIndex = 0;
let watchedHistory = [];
let dwellTimer = null;
let dwellStartTime = Date.now();

// DOM Elements
const feedCounter = document.getElementById("feed-counter");
const reelTitle = document.getElementById("reel-title");
const reelCreator = document.getElementById("reel-creator");
const reelCategory = document.getElementById("reel-category");
const reelDifficulty = document.getElementById("reel-difficulty");
const reelConcepts = document.getElementById("reel-concepts");
const dwellSeconds = document.getElementById("dwell-seconds");
const historyList = document.getElementById("history-list");
const historyCount = document.getElementById("history-count");

const topIdentityDisplay = document.getElementById("top-identity-display");
const interestWeightBadge = document.getElementById("interest-weight-badge");
const domainsChips = document.getElementById("domains-chips");

const btnPrev = document.getElementById("btn-prev-reel");
const btnNext = document.getElementById("btn-next-reel");
const btnInteract = document.getElementById("btn-interact-reel");
const btnFetchRec = document.getElementById("btn-fetch-rec");
const btnCanonicalDemo = document.getElementById("btn-canonical-demo");
const btnReset = document.getElementById("btn-reset");

const recLoading = document.getElementById("recommendation-loading");
const recConfidenceBadge = document.getElementById("rec-confidence-badge");
const fieldCurrentReel = document.getElementById("field-current-reel");
const fieldInterestDetected = document.getElementById("field-interest-detected");
const fieldWhy = document.getElementById("field-why");
const fieldCategory = document.getElementById("field-category");
const fieldDifficulty = document.getElementById("field-difficulty");
const fieldRecommendedReel = document.getElementById("field-recommended-reel");
const fieldWhyThisRec = document.getElementById("field-why-this-rec");
const traversalNodes = document.getElementById("traversal-nodes");

// Initialize Application
async function init() {
  await loadFeed();
  startDwellTimer();
  attachEventListeners();
}

async function loadFeed() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/feed?limit=25`);
    if (res.ok) {
      feedReels = await res.json();
      if (feedReels.length > 0) {
        renderCurrentReel();
      }
    }
  } catch (err) {
    console.error("Failed to load feed:", err);
  }
}

function startDwellTimer() {
  if (dwellTimer) clearInterval(dwellTimer);
  dwellStartTime = Date.now();
  dwellTimer = setInterval(() => {
    const elapsed = ((Date.now() - dwellStartTime) / 1000).toFixed(1);
    dwellSeconds.textContent = `${elapsed}s`;
  }, 100);
}

function renderCurrentReel() {
  if (!feedReels || feedReels.length === 0) return;
  const reel = feedReels[currentReelIndex];

  feedCounter.textContent = `Reel ${currentReelIndex + 1} of ${feedReels.length}`;
  reelTitle.textContent = reel.title;
  reelCreator.textContent = reel.creator ? `@${reel.creator}` : "@ScrollSense Creator";
  reelCategory.textContent = reel.category;
  reelDifficulty.textContent = reel.difficulty;

  // Render concept tags if available from detail
  fetchReelDetail(reel.reel_id);

  btnPrev.disabled = currentReelIndex === 0;
  btnNext.disabled = currentReelIndex === feedReels.length - 1;
  startDwellTimer();
}

async function fetchReelDetail(reelId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/reels/${reelId}`);
    if (res.ok) {
      const detail = await res.json();
      reelConcepts.innerHTML = "";
      if (detail.concept_tags && detail.concept_tags.length > 0) {
        detail.concept_tags.forEach(tag => {
          const pill = document.createElement("span");
          pill.className = "tag tag-concept";
          pill.textContent = `#${tag}`;
          reelConcepts.appendChild(pill);
        });
      }
    }
  } catch (err) {
    console.error("Failed to fetch detail for reel:", reelId, err);
  }
}

function recordInteraction(reel, dwellSec = 15.0) {
  const existing = watchedHistory.find(item => (typeof item === 'string' ? item : item.reel_id) === reel.reel_id);
  if (!existing) {
    watchedHistory.push({
      reel_id: reel.reel_id,
      event_type: "watch",
      watched_seconds: parseFloat(dwellSec),
      completion_ratio: 1.0,
      timestamp: new Date().toISOString()
    });
    updateHistoryUI(reel, dwellSec);
  }
}

function updateHistoryUI(reel, dwellSec) {
  if (watchedHistory.length === 1) {
    historyList.innerHTML = "";
  }
  historyCount.textContent = watchedHistory.length;

  const itemEl = document.createElement("div");
  itemEl.className = "history-item";
  itemEl.innerHTML = `
    <span><strong>${reel.title}</strong> (${reel.reel_id})</span>
    <span class="text-xs text-muted">${dwellSec}s</span>
  `;
  historyList.prepend(itemEl);
}

async function fetchRecommendation() {
  if (watchedHistory.length === 0) {
    alert("Please watch/interact with at least one Reel first.");
    return;
  }

  recLoading.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/v1/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: "demo_student_session",
        history: watchedHistory
      })
    });

    if (res.ok) {
      const data = await res.json();
      renderRecommendation(data);
    } else {
      const err = await res.json();
      alert(`Recommendation Error: ${err.detail || "Failed to generate"}`);
    }
  } catch (err) {
    console.error("Failed to generate recommendation:", err);
  } finally {
    recLoading.classList.add("hidden");
  }
}

function renderRecommendation(data) {
  const contract = data.official_contract;
  const explain = data.explainability;

  // 1. Official Required Contract Fields
  fieldCurrentReel.textContent = contract.current_reel;
  fieldInterestDetected.textContent = contract.interest_detected;
  fieldWhy.textContent = contract.why;
  fieldRecommendedReel.textContent = contract.recommended_tech_reel;
  fieldCategory.textContent = `CATEGORY: ${contract.category}`;
  fieldDifficulty.textContent = `DIFFICULTY: ${contract.difficulty}`;
  fieldWhyThisRec.textContent = contract.why_this_recommendation;

  recConfidenceBadge.textContent = `Confidence: ${contract.confidence}`;
  recConfidenceBadge.className = `badge ${contract.confidence === 'High' ? 'badge-success' : contract.confidence === 'Medium' ? 'badge-info' : 'badge-accent'}`;

  // 2. Inferred Persona & Radar
  if (explain.inferred_identities && Object.keys(explain.inferred_identities).length > 0) {
    const topIdent = Object.keys(explain.inferred_identities)[0];
    const topWeight = explain.inferred_identities[topIdent];
    topIdentityDisplay.textContent = topIdent.replace("_", " ").toUpperCase();
    interestWeightBadge.textContent = `Weight: ${topWeight.toFixed(2)}`;
  }

  // 3. Domain Chips
  domainsChips.innerHTML = "";
  if (explain.domains_breakdown) {
    Object.entries(explain.domains_breakdown).forEach(([dom, score]) => {
      const chip = document.createElement("span");
      chip.className = "tag tag-category";
      chip.textContent = `${dom}: ${(score * 100).toFixed(0)}%`;
      domainsChips.appendChild(chip);
    });
  }

  // 4. Graph Traversal Path
  traversalNodes.innerHTML = "";
  if (explain.graph_traversal && explain.graph_traversal.length > 0) {
    explain.graph_traversal.forEach((node, i) => {
      const pill = document.createElement("span");
      pill.className = "node-pill";
      pill.textContent = `${i + 1}. ${node}`;
      traversalNodes.appendChild(pill);
    });
  } else {
    traversalNodes.innerHTML = '<span class="node-pill">1-hop Identity Adjacent</span>';
  }
}

// Canonical SWE Trap Demo Scenario Runner
async function runCanonicalDemo() {
  resetSession();

  const canonicalIds = [
    "reel_java_meme",
    "reel_swe_lifestyle",
    "reel_interview_joke",
    "reel_laptop_comparison",
  ];

  for (const id of canonicalIds) {
    watchedHistory.push({
      reel_id: id,
      event_type: "watch",
      watched_seconds: 25.0,
      completion_ratio: 1.0,
      timestamp: new Date().toISOString()
    });
  }

  historyCount.textContent = watchedHistory.length;
  historyList.innerHTML = `
    <div class="history-item"><span><strong>M3 Max MacBook Dev</strong> (reel_laptop_comparison)</span><span class="text-xs text-muted">25s</span></div>
    <div class="history-item"><span><strong>Invert Binary Tree Joke</strong> (reel_interview_joke)</span><span class="text-xs text-muted">25s</span></div>
    <div class="history-item"><span><strong>Day in Life of Backend SWE</strong> (reel_swe_lifestyle)</span><span class="text-xs text-muted">25s</span></div>
    <div class="history-item"><span><strong>NullPointerException Meme</strong> (reel_java_meme)</span><span class="text-xs text-muted">25s</span></div>
  `;

  await fetchRecommendation();
}

function resetSession() {
  watchedHistory = [];
  historyCount.textContent = "0";
  historyList.innerHTML = '<p class="empty-hint">Interact with reels in the feed above to build your identity state.</p>';
  topIdentityDisplay.textContent = "No History Yet";
  interestWeightBadge.textContent = "Weight: 0.00";
  domainsChips.innerHTML = "";
  traversalNodes.innerHTML = '<span class="node-pill">Idle</span>';
  fieldCurrentReel.textContent = "-";
  fieldInterestDetected.textContent = "-";
  fieldWhy.textContent = "-";
  fieldRecommendedReel.textContent = "No Recommendation Generated";
  fieldCategory.textContent = "CATEGORY: -";
  fieldDifficulty.textContent = "DIFFICULTY: -";
  fieldWhyThisRec.textContent = "-";
  recConfidenceBadge.textContent = "Confidence: N/A";
  startDwellTimer();
}

function attachEventListeners() {
  btnNext.addEventListener("click", () => {
    if (currentReelIndex < feedReels.length - 1) {
      currentReelIndex++;
      renderCurrentReel();
    }
  });

  btnPrev.addEventListener("click", () => {
    if (currentReelIndex > 0) {
      currentReelIndex--;
      renderCurrentReel();
    }
  });

  btnInteract.addEventListener("click", () => {
    if (feedReels.length > 0) {
      const reel = feedReels[currentReelIndex];
      const dwell = ((Date.now() - dwellStartTime) / 1000).toFixed(1);
      recordInteraction(reel, Math.max(5.0, parseFloat(dwell)));
      if (currentReelIndex < feedReels.length - 1) {
        currentReelIndex++;
        renderCurrentReel();
      }
    }
  });

  btnFetchRec.addEventListener("click", fetchRecommendation);
  btnCanonicalDemo.addEventListener("click", runCanonicalDemo);
  btnReset.addEventListener("click", resetSession);

  // Global Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    if (e.code === "Space") {
      e.preventDefault();
      btnInteract.click();
    } else if (e.key === "ArrowDown" || e.key.toLowerCase() === "j") {
      e.preventDefault();
      if (!btnNext.disabled) btnNext.click();
    } else if (e.key === "ArrowUp" || e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (!btnPrev.disabled) btnPrev.click();
    } else if (e.key === "Enter" || e.key.toLowerCase() === "r") {
      e.preventDefault();
      btnFetchRec.click();
    } else if (e.key.toLowerCase() === "c") {
      e.preventDefault();
      btnCanonicalDemo.click();
    } else if (e.key === "Escape") {
      e.preventDefault();
      btnReset.click();
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
