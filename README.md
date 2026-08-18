# ScrollSense 🎯

> **Identity-Aware Latent Skill Graph Recommender for Short-Form Content**
> A hackathon-scoped, modular monolith designed to escape the literal-topic recommendation trap.

---

## 📌 Problem & Novelty

Standard short-form recommenders (TikTok/Reels/Shorts) collapse latent signals into literal topic repetitions (e.g. watching a programming meme reel leads only to more memes or generic syntax tutorials).

**ScrollSense** solves this by:
1. **Inferring latent identity** from heterogeneous short-form content (varying tone, format, topics).
2. **Retrieving across identity boundaries** using an explicit, versioned **Identity / Skill Adjacency Graph**.
3. **Enforcing a 3-tier integrity gate** (Safety, Substance/Quality, Hype penalty) to prevent identity generalization from devolving into low-substance clickbait.

---

## 🏗️ Architecture Funnel

```
Reel Pool
  │
  ▼
Semantic Signal Layer (ReelSignal: topic, format, tone, depth, interest_evidence)
  │
  ▼
Interest State (Multi-dimensional: professional_identity, domains, goals, depth, content_pref)
  │
  ▼
Identity / Skill Graph (Versioned explicit JSON: nodes & weighted directed edges)
  │
  ▼
Multi-Source Retrieval (Topical, 1-hop Identity Adjacent, 2-hop Boundary Exploration, Reinforcement)
  │
  ▼
Cheap Ranking (Tag overlap + graph distance, no LLM)
  │
  ▼
Three-Tier Gate (Safety hard filter, Quality continuous score, Hype penalty floor)
  │
  ▼
Multi-Objective Ranking (Heuristic weights: topical, difficulty, contextual career relevance, novelty, quality, hype penalty)
  │
  ▼
Diversity Pass & Traceable Explanation
  │
  ▼
Output & Feedback Capture (Reinforces / decays InterestState)
```

---

## 📂 Project Structure

- `reel-recommender-architecture-v4 (1).md` — Full HLD/LLD specification.
- `data/` — Versioned Identity/Skill Graph, sample reels pool, trap regression cases.
- `src/` — Pipeline core, scoring modules, retrieval sources, 3-tier gate.
- `eval/` — Evaluation harness (ScrollSense vs Topic-Only vs Semantic-Similarity baselines).

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone repository
git clone https://github.com/ak-bharadwaj/scrollsense.git
cd scrollsense

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Running the Application
```bash
python -m uvicorn scrollsense.api.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser for the interactive vertical Reel Player & Interest Evolution timeline.
API documentation is available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

### 3. Running Verification & Quality Checks
```bash
# Run full unit & integration test suite (169 tests)
python -m pytest

# Run Ruff linter
ruff check src/ tests/

# Run Mypy static type checker
mypy src/
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health check. |
| `GET` | `/api/v1/feed` | Real verified playable video feed across all 8 problem topics. |
| `GET` | `/api/v1/reels/{id}` | Detailed reel metadata, transcript, and concept tags. |
| `POST` | `/api/v1/recommend` | End-to-end identity inference, graph retrieval, and ranking. |
| `GET` | `/media/accepted/{file}` | Binary MP4 video stream with range request support. |

---

## 🤖 Google Gemini AI Integration

ScrollSense supports optional semantic extraction via **Google AI Studio Gemini Free Tier** (`gemini-3.5-flash`).
If `GEMINI_API_KEY` is configured in `.env` or the environment, `ScrollSenseEngine` automatically utilizes `LLMStructuredSignalExtractor`. If absent, it gracefully uses the deterministic offline extractor.

See [`docs/gemini_configuration.md`](docs/gemini_configuration.md) for full configuration details.

---

## 🧪 Evaluation & Baselines

ScrollSense includes a trap regression harness comparing:
- **Baseline 0 (B0)**: Literal Topic-Only frequency matcher.
- **Baseline 1 (B1)**: Embedding semantic similarity nearest-neighbor.
- **ScrollSense (B2)**: Identity Graph multi-source funnel with 3-tier integrity gate.

