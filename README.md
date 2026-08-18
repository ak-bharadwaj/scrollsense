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

## 🧪 Evaluation & Baselines

ScrollSense includes a trap regression harness comparing:
- **Baseline 1**: Topic-Only frequency matcher.
- **Baseline 2**: Semantic similarity nearest-neighbor.
- **ScrollSense**: Identity Graph multi-source funnel with 3-tier gate.
