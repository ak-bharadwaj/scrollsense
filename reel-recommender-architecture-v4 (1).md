# ScrollSense — Architecture v4
### Monolith, hackathon-scoped, critique-integrated — HLD + LLD only

v3's funnel shape was right. The critique's core objection was correct: **Source B (identity-adjacent retrieval) was doing all the intellectual work, and it was hand-waved as "a curated adjacency map."** That's the actual product of this system — everything else is standard-pattern plumbing around it. v4 fixes that honestly, fixes the muddled integrity gate, and drops every service-boundary pretense in favor of one buildable process.

---

## 0. What changed, and why — mapped directly to the critique

| Critique point | Change made in v4 | Why this is the right scope for a hackathon (not more, not less) |
|---|---|---|
| §3–6: adjacency map is the load-bearing part and it's hand-written | Promoted to a first-class, **versioned, explicit data structure** (Identity/Skill Graph) instead of an implicit lookup buried in "Source B." Still hand-authored — but now the hand-authoring is the visible artifact, not a hidden implementation detail. | We cannot learn this graph from data in a hackathon — no interaction logs exist yet. The honest move is to make the graph a named, inspectable, versioned thing, not to pretend it's learned. |
| §6: persona shouldn't be one label | `PersonaVector.broad_interest` (single string) replaced with a small multi-dimensional `InterestState` (identity / domains / goals / depth / content_preference) | Kept small (5 dimensions, not the full MIND/ComiRec-style multi-vector model) — enough to stop collapsing signal into one label, not enough to need a real multi-interest training pipeline we don't have time for. |
| §9: integrity/quality/hype conflated | Split into three explicit, differently-treated scores: **Safety** (hard reject), **Quality/Substance** (soft, continuous), **Hype/Promotional** (soft penalty, not auto-disqualifying) | This directly fixes the false-rejection risk the critique names ("10 AI tools worth learning" could still be useful) while keeping a real floor so pure hype-with-no-substance still can't win. |
| §10: career_relevance(reel) is the wrong signature | Changed to `career_relevance(reel, interest_state.goals, interest_state.depth)` | Cheap to do — it's just passing two more fields into an existing scoring function — and it fixes a genuine correctness bug, not just a nice-to-have. |
| §11: confidence has no calibration | Confidence is no longer a raw float. It's a **rule-derived bucket** (High/Med/Low) based on evidence count + cross-signal consistency, matching the required output schema anyway | We can't calibrate against ground truth we don't have (§23). But we can stop exposing fake precision — a deterministic bucketing rule is honest and still useful. |
| §8: "signal cached forever" too strong | `ReelSignal` now carries `signal_version` / `ontology_version` / `generated_at` | Free to add, and it's a real correctness issue, not a nitpick — silently changed content is nice UX but a system claim of "cached forever" was ok. Actually wait: |
| §15: exploration is random, not boundary-aware | Source C now walks **one hop beyond** the matched region of the Identity/Skill Graph, not an unrelated random category | Still cheap graph traversal, no new infra — just uses the graph we're already building for Source B. |
| §16–17: no negative feedback, no feedback loop | Added a minimal **feedback capture stub**:每 shown recommendation is logged with an outcome slot (`accepted / skipped / not_interested`), and accepted outcomes lightly reinforce the matching `InterestState` dimension | This is the one place I'm keeping genuinely small: a working stub with a clear extension point, not a real bias-corrected exploration policy (§17's harder claim). That's explicitly future work below. |
| §22–23: no ground truth, no evaluation harness | Added a small **hand-labeled trap test-set** (a handful of watch-sequences with an expected `broad_interest`/`identity` label) used only to sanity-check our own pipeline before the demo | This is *not* a user study and doesn't claim to be. It's internal regression testing, labeled honestly as that — not scientific validation. |
| §18: scoring weights aren't research-grade | Weights explicitly labeled `HEURISTIC_WEIGHTS_V1` in the data model, with a comment that they're a starting point for sensitivity analysis, not a tuned result | Costs nothing, prevents an easy credibility hit if a judge asks "how did you get these numbers." |
| §7: don't call it distillation | Already fixed in v3, kept: "two-speed persona inference," not distillation | — |
| §19: needs a goal/intent layer, and a real feedback→update loop | Partially adopted — `InterestState.goals` exists; the full closed loop (goal inference, controlled exploration correcting exposure bias) is named explicitly as future work, not built | Building the full loop needs real interaction data over time, which a hackathon demo structurally cannot produce in one session. Faking it would be worse than naming the gap. |
| Your instruction: no microservices | **Everything below is one process.** No service boundaries, no network calls between stages — "services" in v2/v3 are now just modules/functions in a single monolith app. | Correct call — this needs to *work*, not scale. Service boundaries were premature architecture for a system with one instance and no distributed load. |

---

## 1. Scope Boundary (say this before anyone asks)

**In scope, built and demoable:**
- Full funnel (signal extraction → identity graph retrieval → cheap ranking → 3-tier gate → multi-objective rank → diversity pass → explanation)
- Versioned, hand-authored Identity/Skill Graph (small, covering the sample dataset's domains)
- Multi-dimensional InterestState with decay/reinforcement
- Feedback capture stub with basic reinforcement (not full bias-corrected exploration)
- Internal trap-case regression test-set

**Explicitly out of scope, named as future work, never claimed as built:**
- Learning the Identity/Skill Graph from data (needs interaction logs we don't have)
- Real trained embeddings / real knowledge distillation (needs training data and time)
- Exposure-bias-corrected controlled exploration (needs a live user base over time)
- Confidence calibration against independent ground truth (needs a user study, §23)
- Weight learning / sensitivity analysis as a rigorous result (needs offline eval infra + logged data)

This split is the actual answer to the critique's "biggest technical risk" and "biggest scientific risk" sections — not by solving them, but by not pretending they're solved.

---

## 2. Revised Conceptual Model

```
REEL
 │
 ▼
Semantic Signal Layer        (per-reel, versioned, cached)
 │
 ▼
Interest Evidence            (what this reel implies about the viewer,
 │                            not just what it's about)
 ▼
Identity / Skill Graph        (versioned, hand-authored for v1,
 │   lookup + 1-2 hop walk      explicitly named as such)
 ▼
Multi-Source Retrieval        (topic / identity / boundary-exploration /
 │                             reinforcement — all graph-aware now)
 ▼
Cheap Ranking                 (tag overlap + graph-distance, no LLM)
 │
 ▼
Safety Gate  →  Quality Score  →  Hype Score     (three separate signals,
 │                                                 not one conflated "integrity")
 ▼
Multi-Objective Rank          (topical_fit, difficulty_match,
 │                             career_relevance(user,reel,goal), novelty,
 │                             quality, hype_penalty — all explicit terms)
 ▼
Diversity / Novelty Pass
 │
 ▼
Explanation (traceable to the above, not LLM-invented after the fact)
 │
 ▼
Output  →  Feedback Capture (stub)  →  InterestState update
```

---

## 3. High-Level Architecture (HLD) — single process, modular monolith

```
┌───────────────────────────────────────────────────────────────────┐
│                        SCROLLSENSE (one process)                      │
│                                                                       │
│  ┌───────────────┐   ┌────────────────────┐   ┌──────────────────┐  │
│  │ Content Store   │   │ Identity/Skill      │   │ Persona Store     │  │
│  │ (reel pool +    │   │ Graph               │   │ (InterestState    │  │
│  │  ReelSignal      │   │ (versioned JSON,     │   │  per student,      │  │
│  │  cache)          │◄──┤  loaded in memory)    │◄──┤  simple file/     │  │
│  │  → SQLite or      │   │                     │   │  SQLite table)     │  │
│  │    JSON file       │   └────────────────────┘   └──────────────────┘  │
│  └───────┬────────┘                                        ▲            │
│          │                                                  │            │
│          ▼                                                  │            │
│  ┌───────────────────────────────────────────────────┐      │            │
│  │  PIPELINE MODULE (plain function calls, no network)  │      │            │
│  │                                                       │      │            │
│  │  signal_extract() → persona_update() → retrieve()     │──────┘            │
│  │  → cheap_rank() → gate() → objective_rank()            │                   │
│  │  → diversify() → explain()                             │                   │
│  └───────────────────────────┬───────────────────────┘                   │
│                              ▼                                          │
│                    ┌──────────────────┐                                  │
│                    │ Output Formatter   │  → required schema              │
│                    └──────────────────┘                                  │
│                              │                                          │
│                              ▼                                          │
│                    ┌──────────────────┐                                  │
│                    │ Feedback Capture   │  → writes back to Persona Store │
│                    │ (stub)              │                                 │
│                    └──────────────────┘                                  │
│                                                                       │
│  External calls (only two, both simple HTTP, not "services"):          │
│  - LLM API call: signal extraction (per reel, cached after first call) │
│  - LLM API call: interest-state deep synthesis + hype-judge (small set) │
└───────────────────────────────────────────────────────────────────┘
```

**No internal service boundaries.** Content Store, Identity/Skill Graph, and Persona Store are just files/tables the single process reads and writes directly — not separate services with their own APIs. The only network calls in the whole system are the two LLM API calls; everything else is in-process function calls. This is the direct fix for your instruction: this needs to *work* in hackathon time, and a monolith with two external calls is something one person can build and debug in a day, where a multi-service version would burn the hackathon on plumbing instead of the actual hard problem (the graph and the gate).

---

## 4. Low-Level Design (LLD)

### 4.1 ReelSignal (versioned)

```
ReelSignal
├── reel_id
├── signal_version          # bump when extraction logic changes
├── ontology_version         # bump when Identity/Skill Graph schema changes
├── model_version             # which LLM/prompt version produced this
├── generated_at
├── topic
├── format
├── tone
├── depth
├── concept_tags[]
└── interest_evidence[]      # NEW — not just "what it's about" but
                              # "what watching this implies," e.g.
                              # {evidence_type: "career_stage_signal",
                              #  value: "candidate/early-career"}
                              # {evidence_type: "professional_identity",
                              #  value: "developer"}
```
This directly implements the critique's §5 example (interview-joke reel → `career_stage_signal=candidate`, `professional_identity=SWE`; laptop reel → `professional_identity=developer`) — the graph traversal in retrieval reads `interest_evidence`, not just `topic`.

### 4.2 Identity/Skill Graph (versioned, hand-authored, explicit)

```
IdentitySkillGraph
├── version
├── nodes[]                  # typed: topic | skill | professional_identity |
│                             #        career_stage | domain
└── edges[]                  # typed relations, each directional + weighted:
      ├── from_node
      ├── to_node
      ├── relation_type       # "topic_implies_identity" |
      │                       # "identity_adjacent_skill" |
      │                       # "skill_implies_role" | ...
      └── weight               # hand-set confidence for v1, learnable later

Example fragment (the actual trap-escape data):
  (java, topic_implies_identity, software_engineer, 0.6)
  (interview_humor, career_stage_signal, candidate, 0.7)
  (swe_lifestyle, topic_implies_identity, software_engineer, 0.8)
  (laptop_comparison, professional_identity_signal, developer, 0.5)
  (software_engineer, identity_adjacent_skill, system_design, 0.75)
  (software_engineer, identity_adjacent_skill, dsa, 0.7)
  (software_engineer, identity_adjacent_skill, cybersecurity, 0.5)
  (software_engineer, identity_adjacent_skill, cloud, 0.55)
```
**This is the artifact the whole pitch actually rests on, per the critique — so it's built as a visible, versioned, inspectable file, not buried logic.** Retrieval Source B is now literally "traverse this graph 1 hop from matched identity nodes" — a specific, demoable, editable thing, not a black box.

### 4.3 InterestState (multi-dimensional, replaces single `broad_interest`)

```
InterestState
├── student_id
├── professional_identity{}   # label → weight, e.g. {software_engineer: 0.86}
├── domains{}                 # label → weight, e.g. {backend: 0.7, ai: 0.3}
├── goals{}                   # label → weight, e.g. {career_prep: 0.8}
├── depth{}                    # domain → Beginner|Intermediate|Advanced
├── content_preference{}       # format → weight, e.g. {humor: 0.6, tutorial: 0.7}
├── evidence[]                 # reel_ids driving current state
└── updated_at
```
Kept to five dimensions on purpose — enough to stop the "one label" flattening the critique correctly objects to, small enough that the Deep Path LLM call can populate it in one structured-JSON call rather than needing a trained multi-vector model.

### 4.4 Three-Tier Gate (replaces the conflated "integrity" gate)

```
SafetyResult      # hard pass/fail, rare trigger, policy-violation only
├── passed          # true unless genuinely unsafe/prohibited content
└── reason

QualityScore       # continuous, soft — feeds ranking, doesn't auto-reject
├── concept_anchor_score   # LLM-judged: does this name a real, checkable concept?
└── depth_score              # surface vs conceptual vs technical, from tags

HypeScore          # continuous, soft — penalty term, doesn't auto-reject alone
├── pattern_penalty          # cheap regex: listicles, urgency, "will get you a job"
└── promotional_language_score

# Combined floor (this is where "avoid blindly recommending hype" actually lives):
effective_reject = SafetyResult.passed == False
                    OR (QualityScore.concept_anchor_score < 0.3
                        AND HypeScore.pattern_penalty > 0.7)
```
This directly fixes the critique's §9 example: "10 AI tools worth learning" has *some* concept-anchor signal (it names real tools), so it survives on quality even with a hype penalty — but "10 AI Tools That Will Get You a Job in 2026" with zero named concepts and maximal urgency language hits the combined floor and is rejected. Hype alone doesn't kill a candidate; **hype combined with zero substance does** — which is the honest version of the requirement, not a blunt keyword ban.

### 4.5 Multi-Source Retrieval (graph-aware)

```
Source A — Topical:               direct match on InterestState.domains
Source B — 1-hop identity-adjacent: walk from InterestState.professional_identity
                                   nodes across `identity_adjacent_skill` edges
Source C — 2-hop boundary exploration: walk one further hop past Source B's nodes
                                   (adjacent-to-adjacent), NOT random — this is the
                                   §15 fix: exploration stays on the graph's boundary,
                                   not an unrelated domain
Source D — Reinforcement:          highest-weight InterestState.domains entry, direct match

Naming standardized: "Source B" always means the 1-hop walk, "Source C" always means
the 2-hop walk starting from Source B's result set — not from the original identity
node. This removes the ambiguity flagged in review (the two were previously described
inconsistently as "one hop beyond" vs. "2-hop walk").
```

### 4.6 Objective Scoring (career_relevance now contextualized)

```
career_relevance(reel, interest_state) =
    f(reel.category, interest_state.goals, interest_state.depth)
    # e.g. a Cloud reel scores high career_relevance only if goals include
    # career_prep AND depth in that domain is below Advanced (still room to grow)

final_score = HEURISTIC_WEIGHTS_V1.topical      * topical_fit
            + HEURISTIC_WEIGHTS_V1.difficulty    * difficulty_match
            + HEURISTIC_WEIGHTS_V1.career         * career_relevance(reel, state)
            + HEURISTIC_WEIGHTS_V1.novelty         * novelty
            + HEURISTIC_WEIGHTS_V1.quality          * QualityScore.concept_anchor_score
            - HEURISTIC_WEIGHTS_V1.hype_penalty      * HypeScore.pattern_penalty

# HEURISTIC_WEIGHTS_V1 is a named, versioned constant — explicitly labeled
# heuristic, not tuned, with a comment pointing at future sensitivity analysis
```

### 4.7 Confidence Bucketing (replaces raw float)

```
def confidence_bucket(interest_state, evidence):
    if len(evidence) >= 3 and cross_signal_consistency(evidence) > 0.7:
        return "High"
    elif len(evidence) >= 2:
        return "Medium"
    else:
        return "Low"
```
`cross_signal_consistency` = simple agreement measure across `interest_evidence` types (e.g., do career_stage_signal, professional_identity_signal, and topic_implies_identity edges all point the same direction?) — deterministic, inspectable, not a fake confidence number pulled from an LLM.

### 4.8 Feedback Capture (stub, explicitly not the full loop)

```
FeedbackEvent
├── recommendation_id
├── student_id
├── outcome           # accepted | skipped | not_interested
└── observed_at

on FeedbackEvent(outcome=accepted):
    reinforce matching InterestState dimension (small weight bump)
on FeedbackEvent(outcome=not_interested):
    decay matching dimension faster than passive time-decay would

NOT built: exposure-bias correction, controlled exploration policy,
           long-run drift monitoring — named in §1 as future work
```

### 4.9 Internal Trap Regression Set (not a user study — say this explicitly)

```
trap_test_cases.json:
[
  {
    "watched": ["java_meme", "swe_lifestyle_vlog", "interview_joke", "laptop_comparison"],
    "expected_identity": "software_engineer",
    "expected_not": ["java"]   # pipeline should NOT collapse back to literal topic
  },
  ... a handful more, covering AI-hype dataset, gaming-only dataset (should NOT
      falsely infer SWE identity from gaming alone), etc.
]
```
Used only to catch regressions in our own pipeline before the demo. Explicitly not claimed as validating that the system "discovered a true identity" — that would need the independent user-declared-interest study the critique correctly says we don't have (§23).

---

## 5. Trap Case, Walked Through v4

1. **Signal extraction** on all 4 reels produces `interest_evidence` entries (career_stage_signal=candidate, professional_identity_signal=developer, topic_implies_identity edges toward software_engineer) — not just topic labels.
2. **InterestState** (Deep Path LLM call) sets `professional_identity.software_engineer = 0.8+`, `goals.career_prep` high, `depth` mostly Beginner–Intermediate.
3. **Source B** walks the graph 1 hop from `software_engineer` → returns HLD/DSA/Cybersecurity/Cloud candidates. This is now a literal, inspectable graph traversal, not implicit logic.
4. **Source C** (boundary exploration) walks 1 more hop — e.g. from `system_design` → `distributed_systems` — offering something adjacent-to-adjacent, not random.
5. **Gate**: a planted hype reel with zero concept-anchor score and high urgency language hits the combined floor → rejected. A borderline "10 AI tools worth learning" (if present) survives on quality but gets penalized in ranking, not auto-killed — matches the critique's §9 fix.
6. **Ranking** uses the contextualized `career_relevance(reel, interest_state)` — a System Design reel scores high specifically because `goals.career_prep` is high and `depth.systems` is still Beginner, i.e., there's real room to grow, not just topical adjacency.
7. **Confidence** bucketed as High — 3+ evidence types (career_stage, professional_identity, topic-implies-identity) agree.
8. **Feedback stub** logs whatever happens next in the demo and lightly reinforces `InterestState`, visibly changing on a second pass if you re-run the demo with the same student — a concrete way to show the state is real, not decorative.

---

## 6. Sharpened Framing (per critique §20–21)

Don't pitch this as "we use an LLM to understand users" — that's not novel anymore. The defensible claim is narrower and stronger:

> We infer latent professional identity from heterogeneous short-form content (differing format, tone, and topic) and use an explicit, versioned identity-adjacency graph to deliberately retrieve *across* that identity boundary — escaping literal-topic recommendation — while a separated quality/hype scoring layer prevents that generalization from defaulting to hype content.

The engineering is standard-pattern (funnel, multi-source retrieval, separated gate — all established, per the critique's own table). The one honestly-novel-for-this-context piece is: **treating "topic → identity → adjacent skill" as an explicit, inspectable graph that retrieval walks, specifically to solve the topic-vs-identity trap** — and being upfront that the graph is hand-authored v1, not learned, with a clear extension path.

**One precise distinction to hold onto under questioning:** the *identity* (e.g. "this person is a software engineer") is genuinely *inferred* by the Deep Path LLM from heterogeneous evidence — that inference is real. The *identity → adjacent-skill edges* (e.g. "software_engineer implies system_design") are *authored*, not discovered — we wrote those weights in. So the honest claim is "the graph didn't discover this relationship, the graph retrieves along a relationship we encoded, applied to an identity the system inferred." Don't claim discovery of latent relationships; claim inference of latent identity plus retrieval along an authored (not learned) adjacency structure. That's a smaller, truer, and — under a knowledgeable reviewer's questions — much more defensible claim than the bigger one.

---

## 7. Evaluation Harness + Baselines (final addition — then stop touching the architecture)

The trap regression set in §4.9 only proves ScrollSense does what it was designed to do. It doesn't prove that against simpler alternatives, which is the actual question a judge or reviewer will ask. Fix: run the same trap cases through three systems, not one.

```
                    ┌───────────────────────┐
                    │   Evaluation Harness    │
                    │                        │
                    │  Trap Test Cases (§4.9) │
                    │  + a few non-trap cases │
                    │    (should NOT trigger  │
                    │    identity generalization,
                    │    e.g. gaming-only history
                    │    should stay gaming-adjacent,
                    │    not become "SWE")     │
                    └───────────┬────────────┘
                                ▼
              Run the same watched-reel sequences through:

  Baseline 1 — Topic-only:        most frequent literal topic, recommend more of it
  Baseline 2 — Semantic similarity: embed all reels, recommend nearest-neighbor by
                                    content similarity alone (no identity graph)
  ScrollSense — Identity-graph retrieval (this system, full v4 pipeline)

                                ▼
                    Compare on, per test case:
  - Trap Escape Rate       (did it generalize to identity, not just repeat topic?)
  - Hype Rejection          (did it reject the planted hype candidate?)
  - False-Positive Rate     (did the non-trap cases wrongly over-generalize?)
  - Relevance (qualitative)  (is the recommendation still on-topic-enough to make sense?)
```

**Why this is small enough to actually build:** Baseline 1 is a five-line function (mode of watched topics). Baseline 2 needs nothing new — it's Source A run alone, with Sources B/C/D and the gate disabled, which the pipeline already supports as components. Neither baseline needs new infrastructure; they're subsets of what's already built. This is the difference between "a cool hackathon system" and "something you can defend as a real comparison" — and it costs almost nothing on top of what's already in v4.

**What this does and doesn't claim:** this is a small internal comparison on a handful of hand-built cases, not a statistically powered study — say that plainly if asked. It's enough to show the direction of the effect (identity-graph retrieval escapes the trap where the baselines structurally can't), not enough to claim a validated effect size.

---

Architecture is stable at v4 + this section. Per the last review: stop revising HLD/LLD here — next concrete artifacts are the Identity/Skill Graph fragment, the 6–8 sample reels (including the trap and non-trap sequences), and the trap regression set with the two baselines wired in.
