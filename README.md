# ScrollSense 🎯

> **Identity-Aware Latent Skill Graph Recommender for Short-Form Content**  
> Escaping the literal-topic recommendation trap using graph traversal, latent identity inference, and integrity-gated multi-objective ranking.

[![CI](https://github.com/ak-bharadwaj/scrollsense/actions/workflows/ci.yml/badge.svg)](https://github.com/ak-bharadwaj/scrollsense/actions/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-scrollsense--qdhg.onrender.com-blue)](https://scrollsense-qdhg.onrender.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌐 Live Demo

**[https://scrollsense-qdhg.onrender.com](https://scrollsense-qdhg.onrender.com)**

- Interactive vertical reel player with real playable MP4 videos
- Live identity inference & domain affinity profiling
- Real-time recommendation contract output after every reel interaction
- Full explainability: graph traversal path, contributing evidence, confidence level
- Press **`C`** for the canonical **SWE Trap Demo** — watches 4 programmer lifestyle reels and infers latent Software Engineer identity in real-time

---

## 📌 Problem & Novelty

Standard short-form recommenders (TikTok/Reels/Shorts) collapse latent signals into **literal topic repetition** — watching a programming meme leads only to more memes or generic syntax tutorials.

**ScrollSense** solves this by:

1. **Inferring latent identity** from heterogeneous short-form content (varying tone, format, topics)
2. **Retrieving across identity boundaries** using an explicit, versioned **Identity / Skill Adjacency Graph**
3. **Enforcing a 3-tier integrity gate** (Safety → Quality → Hype Penalty) to prevent clickbait amplification

### The SWE Trap
> A user watches: *NullPointerException meme → Day in the life of a backend SWE → Invert binary tree joke → M3 MacBook vs ThinkPad for Docker*
>
> **Topic-only recommender** → more memes, more lifestyle vlogs  
> **ScrollSense** → detects latent `software_engineer` identity (weight 0.94) → traverses to `system_design`, `ai_engineering` → recommends *"Kubernetes Pod Lifecycle & Microservices Networking Explained"* (Intermediate, quality 0.82)

---

## 🏗️ Architecture Funnel

```
Reel Pool
  │
  ▼
Semantic Signal Layer
  (ReelSignal: topic, format, tone, depth, interest_evidence[])
  │
  ▼
Interest State Accumulator
  (professional_identity, domains, goals, depth_preference, content_pref)
  │
  ▼
Identity / Skill Graph
  (Versioned explicit JSON: nodes + weighted directed edges)
  │
  ▼
Multi-Source Retrieval
  ├── Topical match
  ├── 1-hop Identity Adjacent (same persona, adjacent domain)
  ├── 2-hop Boundary Exploration (stretch goal, identity expansion)
  └── Reinforcement (rewatched / liked history)
  │
  ▼
Candidate Pre-filter (Tag overlap + graph distance, no LLM)
  │
  ▼
Three-Tier Integrity Gate
  ├── Tier 1: Safety hard filter (block unsafe content)
  ├── Tier 2: Quality continuous score (substance threshold)
  └── Tier 3: Hype penalty floor (penalize clickbait)
  │
  ▼
Multi-Objective Ranking
  (topical, difficulty, contextual career relevance, novelty, quality, hype penalty)
  │
  ▼
Diversity Pass + Traceable Explanation
  │
  ▼
Output + Feedback Capture
  (Reinforces / decays InterestState on next interaction)
```

---

## 📂 Project Structure

```
scrollsense/
├── src/scrollsense/
│   ├── api/               # FastAPI app, routes, schemas, static frontend
│   │   └── static/        # index.html, app.js, style.css
│   ├── domain/            # Core domain models (Reel, InterestState, etc.)
│   ├── engine/            # ScrollSenseEngine orchestrator
│   ├── graph/             # Identity/Skill Graph loader & traversal
│   ├── ingestion/         # Asset manifest, ingestion pipeline, QC gates
│   ├── ranking/           # Multi-objective ranking, diversity pass
│   ├── retrieval/         # Multi-source candidate retrieval
│   └── signals/           # Signal extraction (rule-based + Gemini LLM)
├── data/
│   ├── identity_skill_graph.json   # Versioned skill graph
│   ├── inputs.json                 # Fixture reels pool (25 reels)
│   ├── candidates.json             # Candidate reel repository
│   └── content/
│       ├── manifest.json           # Verified asset manifest (11 accepted MP4s)
│       └── accepted/               # Real licensed MP4 video files (Mixkit)
├── tests/                          # 168 unit + integration tests
├── render.yaml                     # Render.com deployment config
├── pyproject.toml                  # Project config, ruff, mypy settings
└── requirements.txt                # Runtime dependencies
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/ak-bharadwaj/scrollsense.git
cd scrollsense

pip install -r requirements.txt
pip install -e .
```

### 2. Run Locally

```bash
python -m uvicorn scrollsense.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** — interactive reel player with live identity inference.  
API docs: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

### 3. Optional: Gemini AI Signal Extraction

```bash
# Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env
```

If `GEMINI_API_KEY` is set, the engine uses `LLMStructuredSignalExtractor` (Gemini Flash) for richer concept extraction. Without it, the deterministic rule-based extractor runs offline with zero latency.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health check |
| `GET` | `/api/v1/feed` | Verified playable reel feed (`include_fixtures=true` for full 25-reel set) |
| `GET` | `/api/v1/reels/{id}` | Reel detail: metadata, transcript, concept tags |
| `POST` | `/api/v1/recommend` | Full identity inference → graph traversal → ranked recommendation |
| `GET` | `/media/accepted/{file}` | MP4 video stream for accepted content |
| `GET` | `/docs` | Interactive Swagger UI |

### Recommendation Request Example

```bash
curl -X POST https://scrollsense-qdhg.onrender.com/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_user",
    "history": [
      {"reel_id": "reel_java_meme", "event_type": "watch", "watched_seconds": 25.0},
      {"reel_id": "reel_swe_lifestyle", "event_type": "watch", "watched_seconds": 22.0}
    ]
  }'
```

### Recommendation Response (Official Contract)

```json
{
  "official_contract": {
    "current_reel": "reel_swe_lifestyle — Day in the life of a backend engineer",
    "interest_detected": "Software Engineer",
    "why": "Detected latent 'Software Engineer' identity (weight 0.94)...",
    "recommended_tech_reel": "Kubernetes Pod Lifecycle & Microservices Networking Explained",
    "category": "cloud_infrastructure",
    "difficulty": "Intermediate",
    "why_this_recommendation": "1-hop identity-adjacent traversal (software_engineer → cloud_infrastructure)...",
    "confidence": "High"
  },
  "explainability": {
    "inferred_identities": {"software_engineer": 0.94},
    "domains_breakdown": {"cloud_infrastructure": 0.66, "backend": 0.65},
    "graph_traversal": ["software_engineer", "cloud_infrastructure"],
    "contributing_evidence": ["reel_java_meme", "reel_swe_lifestyle"]
  }
}
```

---

## ✅ Code Quality & Test Coverage

| Metric | Value |
| :--- | :--- |
| **Test Suite** | 169 tests across 16 test modules |
| **Test Pass Rate** | 168 passed, 1 skipped — **0 failures** |
| **Source Modules** | 42 Python source files |
| **Linting** | `ruff` — zero lint errors (`E`, `F`, `W` rules) |
| **Type Safety** | `mypy` — configured, `ignore_missing_imports`, `warn_unused_configs` |
| **CI** | GitHub Actions — runs `pytest` + `ruff` on every push |
| **Recommendation Latency** | **< 20ms** per `/api/v1/recommend` call (pure Python, no LLM in hot path) |
| **Zero External Dependency in Hot Path** | Graph traversal + ranking runs fully offline — no API calls required |
| **Graceful Degradation** | Gemini AI optional — falls back to deterministic rule-based extractor if key absent |

```bash
python -m pytest          # 168 passed, 1 skipped, 0 failed
ruff check src/ tests/    # All checks passed!
mypy src/                 # Clean with configured rules
```

---

## 🧪 Tests & Quality

```bash
# Full test suite (168 tests, 1 skipped)
python -m pytest

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

**CI**: GitHub Actions runs `pytest` + `ruff` on every push to `main`. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## 🤖 Gemini AI Integration

ScrollSense uses **Google AI Studio Gemini** (`gemini-2.0-flash`) for optional structured signal extraction from reel transcripts.

| Mode | Behaviour |
| :--- | :--- |
| `GEMINI_API_KEY` set | `LLMStructuredSignalExtractor` — richer concept tagging via Gemini |
| No key | Rule-based offline extractor — zero latency, deterministic |

See [`docs/gemini_configuration.md`](docs/gemini_configuration.md) for setup details.

---

## 🛡️ Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities and responsible disclosure.  
API keys must never be committed. Use `.env` (git-ignored) or environment variables only.

---

## 📄 License

[MIT License](LICENSE) — © 2026 ScrollSense Contributors
