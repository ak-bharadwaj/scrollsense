"""Deterministic persona inferencer aggregating ReelSignals into InterestState."""

from collections import Counter
from datetime import datetime, timezone
import math
from typing import Sequence

from scrollsense.domain.enums import DepthLevel, EvidenceType
from scrollsense.domain.persona import InterestState
from scrollsense.domain.reels import ReelSignal
from scrollsense.persona.policy import InferencePolicy

DEPTH_RANK: dict[DepthLevel, int] = {
    DepthLevel.BEGINNER: 1,
    DepthLevel.INTERMEDIATE: 2,
    DepthLevel.ADVANCED: 3,
}


class PersonaInferencer:
    """Infers a multi-dimensional InterestState from a sequence of ReelSignals."""

    def __init__(self, policy: InferencePolicy | None = None) -> None:
        self.policy = policy or InferencePolicy()

    def infer_interest_state(
        self,
        student_id: str,
        reel_signals: Sequence[ReelSignal],
        updated_at: datetime | None = None,
    ) -> InterestState:
        """Aggregate atomic ReelSignal evidence across interaction history into a validated InterestState."""
        timestamp = updated_at or datetime.now(timezone.utc)

        if not reel_signals:
            return InterestState(
                student_id=student_id,
                professional_identity={},
                domains={},
                goals={},
                depth={},
                content_preference={},
                evidence=[],
                updated_at=timestamp,
            )

        # 1. Track unique contributing reel IDs preserving order of first appearance
        evidence_reel_ids: list[str] = []
        for signal in reel_signals:
            if signal.reel_id not in evidence_reel_ids:
                evidence_reel_ids.append(signal.reel_id)

        # 2. Aggregate evidence by distinct reels to avoid same-reel double counting
        identity_by_reel: dict[str, dict[str, float]] = {}
        domain_by_reel: dict[str, dict[str, float]] = {}
        goal_by_reel: dict[str, dict[str, float]] = {}
        depth_by_domain: dict[str, DepthLevel] = {}

        format_counter: Counter[str] = Counter()
        tone_counter: Counter[str] = Counter()

        for signal in reel_signals:
            r_id = signal.reel_id
            identity_by_reel.setdefault(r_id, {})
            domain_by_reel.setdefault(r_id, {})
            goal_by_reel.setdefault(r_id, {})

            format_counter[signal.format.lower()] += 1
            tone_counter[signal.tone.lower()] += 1

            for ev in signal.interest_evidence:
                weight = ev.weight if ev.weight is not None else 0.5

                if ev.evidence_type in (
                    EvidenceType.TOPIC_IMPLIES_IDENTITY,
                    EvidenceType.PROFESSIONAL_IDENTITY_SIGNAL,
                ):
                    curr = identity_by_reel[r_id].get(ev.value, 0.0)
                    identity_by_reel[r_id][ev.value] = max(curr, weight)

                elif ev.evidence_type == EvidenceType.DOMAIN_SIGNAL:
                    curr = domain_by_reel[r_id].get(ev.value, 0.0)
                    domain_by_reel[r_id][ev.value] = max(curr, weight)

                    # Track observed depth for this domain
                    current_depth = depth_by_domain.get(ev.value, DepthLevel.BEGINNER)
                    if DEPTH_RANK[signal.depth] > DEPTH_RANK[current_depth]:
                        depth_by_domain[ev.value] = signal.depth
                    elif ev.value not in depth_by_domain:
                        depth_by_domain[ev.value] = signal.depth

                elif ev.evidence_type == EvidenceType.GOAL_SIGNAL:
                    curr = goal_by_reel[r_id].get(ev.value, 0.0)
                    goal_by_reel[r_id][ev.value] = max(curr, weight)

                elif ev.evidence_type == EvidenceType.CAREER_STAGE_SIGNAL:
                    # Candidate career stage inherently supports career_prep goal
                    if ev.value == "candidate":
                        curr = goal_by_reel[r_id].get("career_prep", 0.0)
                        goal_by_reel[r_id]["career_prep"] = max(curr, weight * 0.9)

        # 3. Calculate multi-reel saturated weights bounded in [0, 1]
        prof_identity = self._combine_multi_reel_evidence(
            identity_by_reel, self.policy.identity_evidence_scale
        )
        domains = self._combine_multi_reel_evidence(
            domain_by_reel, self.policy.domain_evidence_scale
        )
        goals = self._combine_multi_reel_evidence(
            goal_by_reel, self.policy.goal_evidence_scale
        )

        # 4. Calculate content preferences from repeated observations
        content_pref = self._calculate_content_preferences(
            format_counter, tone_counter, len(reel_signals)
        )

        return InterestState(
            student_id=student_id,
            professional_identity=prof_identity,
            domains=domains,
            goals=goals,
            depth=depth_by_domain,
            content_preference=content_pref,
            evidence=evidence_reel_ids,
            updated_at=timestamp,
        )

    def _combine_multi_reel_evidence(
        self,
        evidence_by_reel: dict[str, dict[str, float]],
        scale_factor: float,
    ) -> dict[str, float]:
        """Combine per-reel max weights into an asymptotically saturated composite weight in [0, 1]."""
        weights_by_key: dict[str, list[float]] = {}

        for r_id, ev_dict in evidence_by_reel.items():
            for key, weight in ev_dict.items():
                weights_by_key.setdefault(key, []).append(weight)

        combined: dict[str, float] = {}
        for key, weights in weights_by_key.items():
            # Asymptotic combination: 1 - prod(1 - scale * w_i)
            complement_prod = 1.0
            for w in weights:
                effective_w = min(1.0, max(0.0, w * scale_factor))
                complement_prod *= (1.0 - effective_w)

            raw_score = 1.0 - complement_prod
            final_weight = min(self.policy.max_weight_cap, max(0.0, round(raw_score, 4)))
            combined[key] = final_weight

        # Sort deterministically: descending weight, ascending key
        return dict(sorted(combined.items(), key=lambda item: (-item[1], item[0])))

    def _calculate_content_preferences(
        self,
        format_counter: Counter[str],
        tone_counter: Counter[str],
        total_signals: int,
    ) -> dict[str, float]:
        """Aggregate observed format and tone preferences requiring multiple observations."""
        if total_signals == 0:
            return {}

        prefs: dict[str, float] = {}
        min_obs = self.policy.min_content_preference_observations

        # Formats
        for fmt, count in format_counter.items():
            if count >= min_obs:
                freq = count / total_signals
                prefs[fmt] = round(min(1.0, freq), 4)

        # Tones
        for tone, count in tone_counter.items():
            if count >= min_obs:
                freq = count / total_signals
                prefs[tone] = round(min(1.0, freq), 4)

        # Sort deterministically: descending weight, ascending key
        return dict(sorted(prefs.items(), key=lambda item: (-item[1], item[0])))
