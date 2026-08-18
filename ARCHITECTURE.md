# ScrollSense v4 Architecture & Module Boundaries

## Overview
ScrollSense v4 is a modular monolith recommender designed to infer latent professional identity from short-form content and retrieve along an explicit, versioned Identity/Skill graph while filtering out hype and low-substance content.

## Architectural Rules & Invariants
1. **Single-Process Monolith**: No internal microservices, RPCs, or network boundaries between stages.
2. **Domain Contract Communication**: All modules communicate strictly via explicit domain models and data contracts defined in `scrollsense.domain`. Modules do not share internal private state or bypass domain schemas.
3. **No Hidden Logic in Retrieval**: The Identity/Skill Graph is an explicit, inspectable data structure loaded into memory, not buried inside ad-hoc logic.
4. **Three-Tier Separation**: Safety (hard filter), Substance/Quality (continuous score), and Hype (penalty score) are computed independently before combining into the ranking objective.

## Module Boundaries (`src/scrollsense/`)

| Module | Boundary & Responsibility |
| :--- | :--- |
| `domain` | Core data schemas, domain entities, and data contracts (`ReelSignal`, `InterestState`, `IdentitySkillGraph`, `FeedbackEvent`, etc.). |
| `graph` | Identity/Skill Graph representation, validation, loading, and graph traversal (1-hop adjacent, 2-hop boundary). |
| `signals` | Semantic signal extraction and caching for reels. |
| `persona` | Multi-dimensional `InterestState` synthesis, state maintenance, and updates. |
| `retrieval` | Multi-source candidate generation (Topical, 1-hop Identity Adjacent, 2-hop Boundary Exploration, Reinforcement). |
| `ranking` | Multi-objective scoring (`topical`, `difficulty`, contextual `career_relevance`, `novelty`, `quality`, `hype_penalty`) and diversity pass. |
| `gates` | 3-tier integrity checks: Safety policy gate, Substance/Quality evaluator, and Hype/Promotional penalty calculator. |
| `feedback` | Feedback event ingestion, outcome recording, and `InterestState` reinforcement/decay. |
| `evaluation` | Internal trap regression test harness and baseline comparisons (Topic-Only, Semantic Similarity, ScrollSense). |
| `api` | Monolithic application endpoints and interface contracts. |
