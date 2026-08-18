// ScrollSense Interactive Short-Form Reel Application Controller

const API_BASE = window.location.origin;

let feedReels = [];
let currentReelIndex = 0;
let watchedHistory = [];
let dwellTimer = null;
let dwellStartTime = Date.now();
let likeStates = new Map(); // reel_id -> boolean

// DOM Elements
const feedPositionPill = document.getElementById("feed-position-pill");
const dwellDisplay = document.getElementById("dwell-display");
const reelMainTitle = document.getElementById("reel-main-title");
const reelCreatorHandle = document.getElementById("reel-creator-handle");
const reelCatChip = document.getElementById("reel-cat-chip");
const reelDiffChip = document.getElementById("reel-diff-chip");
const reelConceptChips = document.getElementById("reel-concept-chips");
const videoMediaContainer = document.getElementById("video-media-container");
const playbackProgressFill = document.getElementById("playback-progress-fill");

const actionLike = document.getElementById("action-like");
const actionWatch = document.getElementById("action-watch");
const actionWhy = document.getElementById("action-why");
const actionNext = document.getElementById("action-next");
const likeCount = document.getElementById("like-count");

const primaryIdentityName = document.getElementById("primary-identity-name");
const identityStrengthBadge = document.getElementById("identity-strength-badge");
const domainAffinityBars = document.getElementById("domain-affinity-bars");

const recConfidencePill = document.getElementById("rec-confidence-pill");
const recSpinner = document.getElementById("rec-spinner");
const contractFieldsBody = document.getElementById("contract-fields-body");
const outCurrentReel = document.getElementById("out-current-reel");
const outInterestDetected = document.getElementById("out-interest-detected");
const outWhy = document.getElementById("out-why");
const outCategory = document.getElementById("out-category");
const outDifficulty = document.getElementById("out-difficulty");
const outRecommendedReel = document.getElementById("out-recommended-reel");
const outWhyThisRec = document.getElementById("out-why-this-rec");

const historyCounter = document.getElementById("history-counter");
const historyScrollList = document.getElementById("history-scroll-list");

const explainBackdrop = document.getElementById("explain-backdrop");
const btnCloseSheet = document.getElementById("btn-close-sheet");
const sheetCloseHandle = document.getElementById("sheet-close-handle");
const explainGraphPath = document.getElementById("explain-graph-path");
const explainEvidenceList = document.getElementById("explain-evidence-list");

const btnCanonicalDemo = document.getElementById("btn-canonical-demo");
const btnFetchRecNav = document.getElementById("btn-fetch-rec-nav");
const btnReset = document.getElementById("btn-reset");

// Initialize Application
async function init() {
  await loadFeed();
  attachEventListeners();
  startDwellTimer();
}

async function loadFeed() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/feed?limit=25&include_fixtures=true`);
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
    dwellDisplay.textContent = `${elapsed}s`;

    // Progress bar up to 30s
    const pct = Math.min(100, (parseFloat(elapsed) / 30.0) * 100);
    playbackProgressFill.style.width = `${pct}%`;
  }, 100);
}

function renderCurrentReel() {
  if (!feedReels || feedReels.length === 0) return;
  const reel = feedReels[currentReelIndex];

  feedPositionPill.textContent = `Reel ${currentReelIndex + 1} of ${feedReels.length}`;
  reelMainTitle.textContent = reel.title;
  reelCreatorHandle.textContent = reel.creator ? `@${reel.creator}` : "@[SYNTHETIC_FIXTURE]";
  reelCatChip.textContent = reel.category;
  reelDiffChip.textContent = reel.difficulty;

  // Like button state
  const isLiked = likeStates.get(reel.reel_id) || false;
  likeCount.textContent = isLiked ? "Liked" : "Like";
  actionLike.style.color = isLiked ? "#fb7185" : "#fff";

  // Video container rendering: Native <video> if available, else synthetic fixture UI
  if (reel.video_url) {
    videoMediaContainer.innerHTML = `
      <video src="${reel.video_url}" controls autoplay muted loop playsinline></video>
    `;
  } else {
    videoMediaContainer.innerHTML = `
      <div class="fixture-visualizer">
        <div class="sound-wave-bars" aria-hidden="true">
          <span></span><span></span><span></span><span></span><span></span>
        </div>
        <div class="fixture-tag-notice">[SYNTHETIC FIXTURE]</div>
      </div>
    `;
  }

  // Fetch full detail for concept tags
  fetchReelDetail(reel.reel_id);
  startDwellTimer();
}

async function fetchReelDetail(reelId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/reels/${reelId}`);
    if (res.ok) {
      const detail = await res.json();
      reelConceptChips.innerHTML = "";
      if (detail.concept_tags && detail.concept_tags.length > 0) {
        detail.concept_tags.forEach(tag => {
          const pill = document.createElement("span");
          pill.className = "tag-concept";
          pill.textContent = `#${tag}`;
          reelConceptChips.appendChild(pill);
        });
      }
    }
  } catch (err) {
    console.error("Failed to fetch detail for reel:", reelId, err);
  }
}

function recordInteraction(reel, dwellSec = 15.0) {
  const existing = watchedHistory.find(item => (typeof item === "string" ? item : item.reel_id) === reel.reel_id);
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
    historyScrollList.innerHTML = "";
  }
  historyCounter.textContent = watchedHistory.length;

  const itemEl = document.createElement("div");
  itemEl.className = "history-entry";
  itemEl.innerHTML = `
    <span><strong>${reel.title.replace(" [SYNTHETIC_FIXTURE]", "")}</strong> (${reel.reel_id})</span>
    <span class="mono-val">${dwellSec}s</span>
  `;
  historyScrollList.prepend(itemEl);
}

async function fetchRecommendation() {
  if (watchedHistory.length === 0) {
    alert("Please watch/interact with at least one Reel first, or click 'Run SWE Trap Demo'.");
    return;
  }

  recSpinner.classList.remove("hidden");
  contractFieldsBody.style.opacity = "0.3";

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
      alert(`Recommendation Error: ${err.detail || "Failed to generate recommendation"}`);
    }
  } catch (err) {
    console.error("Failed to generate recommendation:", err);
  } finally {
    recSpinner.classList.add("hidden");
    contractFieldsBody.style.opacity = "1";
  }
}

function renderRecommendation(data) {
  const contract = data.official_contract;
  const explain = data.explainability;

  // 1. Populate Official 8 Required Fields
  outCurrentReel.textContent = contract.current_reel;
  outInterestDetected.textContent = contract.interest_detected;
  outWhy.textContent = contract.why;
  outRecommendedReel.textContent = contract.recommended_tech_reel;
  outCategory.textContent = `CATEGORY: ${contract.category}`;
  outDifficulty.textContent = `DIFFICULTY: ${contract.difficulty}`;
  outWhyThisRec.textContent = contract.why_this_recommendation;

  recConfidencePill.textContent = `Confidence: ${contract.confidence}`;
  recConfidencePill.className = `badge-confidence ${contract.confidence === 'High' ? 'conf-high' : 'conf-medium'}`;

  // 2. Inferred Latent Identity State
  if (explain.inferred_identities && Object.keys(explain.inferred_identities).length > 0) {
    const topIdent = Object.keys(explain.inferred_identities)[0];
    const topWeight = explain.inferred_identities[topIdent];
    primaryIdentityName.textContent = topIdent.replace("_", " ").toUpperCase();
    identityStrengthBadge.textContent = `Strength: ${topWeight.toFixed(2)}`;
  }

  // 3. Domain Affinities
  domainAffinityBars.innerHTML = "";
  if (explain.domains_breakdown) {
    Object.entries(explain.domains_breakdown).forEach(([dom, score]) => {
      const chip = document.createElement("div");
      chip.className = "affinity-chip";
      chip.textContent = `${dom}: ${(score * 100).toFixed(0)}%`;
      domainAffinityBars.appendChild(chip);
    });
  }

  // 4. Graph Traversal Path
  explainGraphPath.innerHTML = "";
  if (explain.graph_traversal && explain.graph_traversal.length > 0) {
    explain.graph_traversal.forEach((node, i) => {
      if (i > 0) {
        const arrow = document.createElement("span");
        arrow.className = "path-arrow";
        arrow.textContent = "→";
        explainGraphPath.appendChild(arrow);
      }
      const pill = document.createElement("span");
      pill.className = "node-badge";
      pill.textContent = `${i + 1}. ${node}`;
      explainGraphPath.appendChild(pill);
    });
  } else {
    explainGraphPath.innerHTML = '<span class="node-badge">1. software_engineer → 2. system_design</span>';
  }

  // 5. Contributing Evidence Cards
  explainEvidenceList.innerHTML = "";
  if (explain.contributing_evidence && explain.contributing_evidence.length > 0) {
    explain.contributing_evidence.forEach(ev => {
      const card = document.createElement("div");
      card.className = "evidence-card-item";
      card.textContent = `Watched: ${ev}`;
      explainEvidenceList.appendChild(card);
    });
  }
}

// Canonical SWE Trap Demo Scenario
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

  historyCounter.textContent = watchedHistory.length;
  historyScrollList.innerHTML = `
    <div class="history-entry"><span><strong>M3 Max MacBook Dev</strong> (reel_laptop_comparison)</span><span class="mono-val">25.0s</span></div>
    <div class="history-entry"><span><strong>Invert Binary Tree Joke</strong> (reel_interview_joke)</span><span class="mono-val">25.0s</span></div>
    <div class="history-entry"><span><strong>Day in Life of Backend SWE</strong> (reel_swe_lifestyle)</span><span class="mono-val">25.0s</span></div>
    <div class="history-entry"><span><strong>NullPointerException Meme</strong> (reel_java_meme)</span><span class="mono-val">25.0s</span></div>
  `;

  await fetchRecommendation();
}

function resetSession() {
  watchedHistory = [];
  likeStates.clear();
  historyCounter.textContent = "0";
  historyScrollList.innerHTML = '<p class="empty-hint">Interacted reels will appear here with dwell times.</p>';
  primaryIdentityName.textContent = "No History Yet";
  identityStrengthBadge.textContent = "Strength: 0.00";
  domainAffinityBars.innerHTML = '<p class="empty-hint">Interact with reels in the feed to build your interest profile.</p>';
  explainGraphPath.innerHTML = '<span class="node-badge">Idle</span>';
  explainEvidenceList.innerHTML = '';
  outCurrentReel.textContent = "-";
  outInterestDetected.textContent = "-";
  outWhy.textContent = "-";
  outRecommendedReel.textContent = "No Recommendation Generated";
  outCategory.textContent = "CATEGORY: -";
  outDifficulty.textContent = "DIFFICULTY: -";
  outWhyThisRec.textContent = 'Watch reels and click "Get Recommendation" or press "C" for the canonical demo.';
  recConfidencePill.textContent = "Confidence: N/A";
  recConfidencePill.className = "badge-confidence";
  closeExplainSheet();
  startDwellTimer();
}

function openExplainSheet() {
  explainBackdrop.classList.remove("hidden");
}

function closeExplainSheet() {
  explainBackdrop.classList.add("hidden");
}

function attachEventListeners() {
  actionNext.addEventListener("click", () => {
    if (feedReels.length > 0) {
      currentReelIndex = (currentReelIndex + 1) % feedReels.length;
      renderCurrentReel();
    }
  });

  actionWatch.addEventListener("click", () => {
    if (feedReels.length > 0) {
      const reel = feedReels[currentReelIndex];
      const elapsed = ((Date.now() - dwellStartTime) / 1000).toFixed(1);
      recordInteraction(reel, Math.max(10.0, parseFloat(elapsed)));
      currentReelIndex = (currentReelIndex + 1) % feedReels.length;
      renderCurrentReel();
    }
  });

  actionLike.addEventListener("click", () => {
    if (feedReels.length > 0) {
      const reel = feedReels[currentReelIndex];
      const currentLiked = likeStates.get(reel.reel_id) || false;
      likeStates.set(reel.reel_id, !currentLiked);
      const elapsed = ((Date.now() - dwellStartTime) / 1000).toFixed(1);
      recordInteraction(reel, Math.max(5.0, parseFloat(elapsed)));
      renderCurrentReel();
    }
  });

  actionWhy.addEventListener("click", openExplainSheet);
  btnCloseSheet.addEventListener("click", closeExplainSheet);
  sheetCloseHandle.addEventListener("click", closeExplainSheet);

  explainBackdrop.addEventListener("click", (e) => {
    if (e.target === explainBackdrop) closeExplainSheet();
  });

  btnFetchRecNav.addEventListener("click", fetchRecommendation);
  btnCanonicalDemo.addEventListener("click", runCanonicalDemo);
  btnReset.addEventListener("click", resetSession);

  // Global Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    if (e.code === "Space") {
      e.preventDefault();
      actionWatch.click();
    } else if (e.key === "ArrowDown" || e.key.toLowerCase() === "j") {
      e.preventDefault();
      actionNext.click();
    } else if (e.key === "ArrowUp" || e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (feedReels.length > 0) {
        currentReelIndex = (currentReelIndex - 1 + feedReels.length) % feedReels.length;
        renderCurrentReel();
      }
    } else if (e.key.toLowerCase() === "l") {
      e.preventDefault();
      actionLike.click();
    } else if (e.key.toLowerCase() === "w") {
      e.preventDefault();
      if (explainBackdrop.classList.contains("hidden")) {
        openExplainSheet();
      } else {
        closeExplainSheet();
      }
    } else if (e.key === "Enter" || e.key.toLowerCase() === "r") {
      e.preventDefault();
      btnFetchRecNav.click();
    } else if (e.key.toLowerCase() === "c") {
      e.preventDefault();
      btnCanonicalDemo.click();
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (!explainBackdrop.classList.contains("hidden")) {
        closeExplainSheet();
      } else {
        btnReset.click();
      }
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
