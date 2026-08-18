"""Candidate quality, integrity, and safety gates evaluator."""

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.gates import GateResult, HypeScore, QualityScore, SafetyResult
from scrollsense.domain.reels import Reel

# Prohibited unsafe indicators
UNSAFE_TAGS = {"malware", "hate_speech", "academic_fraud", "harassment", "dangerous_exploit"}

# Grounded substantive technical concept anchors
SUBSTANTIVE_CONCEPTS = {
    "redis",
    "cache_invalidation",
    "distributed_systems",
    "system_design",
    "binary_trees",
    "dynamic_programming",
    "dsa",
    "kubernetes",
    "cloud_networking",
    "docker",
    "oauth2",
    "jwt",
    "api_security",
    "cybersecurity",
    "transformers",
    "neural_networks",
    "attention_mechanism",
    "ai_architecture",
    "records",
    "sealed_classes",
    "pattern_matching",
    "serverless",
}

# Exaggerated promotional / hype tags
HYPE_TAGS = {"ai_hype", "get_rich_quick", "career_shortcuts", "guaranteed_job", "instant_wealth"}

# Problem-driven text patterns for explicit high-hype claims
EXPLICIT_HYPE_PHRASES = {
    "guarantee a job",
    "guaranteed job",
    "get you hired",
    "will get you a job",
    "instant wealth",
    "make $200k",
    "make 200k",
    "replace all programmers",
    "replace programmers",
    "career guaranteed",
    "get rich quick",
    "10x your salary",
    "100k in 30 days",
}


class CandidateGateEvaluator:
    """Evaluates candidates across Safety, Quality/Substance, and Hype tiers."""

    def __init__(
        self,
        substance_rejection_threshold: float = 0.38,
        hype_rejection_threshold: float = 0.65,
    ) -> None:
        if not (0.0 <= substance_rejection_threshold <= 1.0):
            raise ValueError(
                f"substance_rejection_threshold must be in [0, 1], got {substance_rejection_threshold}"
            )
        if not (0.0 <= hype_rejection_threshold <= 1.0):
            raise ValueError(
                f"hype_rejection_threshold must be in [0, 1], got {hype_rejection_threshold}"
            )

        self.substance_threshold = substance_rejection_threshold
        self.hype_threshold = hype_rejection_threshold

    def evaluate(self, candidate_or_reel: Reel) -> GateResult:
        """Evaluate a candidate reel across all 3 tiers and determine pass/reject decision."""
        reel = candidate_or_reel

        # 1. Safety Gate
        safety = self.evaluate_safety(reel)
        quality = self.evaluate_quality(reel)
        hype = self.evaluate_hype(reel)

        if not safety.passed:
            return GateResult(
                candidate_id=reel.reel_id,
                passed=False,
                safety=safety,
                quality=quality,
                hype=hype,
                rejection_reason=f"safety_violation: {safety.reason}",
            )

        # 2. Combined Substance & Hype Decision: Reject ONLY when low substance AND high hype
        is_low_substance = quality.overall < self.substance_threshold
        is_high_hype = hype.overall >= self.hype_threshold

        if is_low_substance and is_high_hype:
            return GateResult(
                candidate_id=reel.reel_id,
                passed=False,
                safety=safety,
                quality=quality,
                hype=hype,
                rejection_reason="low_substance_high_hype",
            )

        return GateResult(
            candidate_id=reel.reel_id,
            passed=True,
            safety=safety,
            quality=quality,
            hype=hype,
            rejection_reason=None,
        )

    def evaluate_safety(self, reel: Reel) -> SafetyResult:
        """Evaluate whether candidate contains prohibited/unsafe content."""
        tags = set(t.lower() for t in reel.concept_tags)
        text_content = f"{reel.title} {reel.transcript or ''}".lower()

        for unsafe_tag in UNSAFE_TAGS:
            if unsafe_tag in tags or unsafe_tag in text_content:
                return SafetyResult(
                    passed=False,
                    reason=f"Detected prohibited content: {unsafe_tag}",
                )

        return SafetyResult(passed=True, reason=None)

    def evaluate_quality(self, reel: Reel) -> QualityScore:
        """Produce continuous normalized [0, 1] substance and technical depth score."""
        tags = set(t.lower() for t in reel.concept_tags)
        text_content = f"{reel.title} {reel.transcript or ''}".lower()
        matched_text_hype = any(phrase in text_content for phrase in EXPLICIT_HYPE_PHRASES)

        # Concept anchor score: evaluate checkable real concepts
        matched_substantive = tags.intersection(SUBSTANTIVE_CONCEPTS)
        if len(matched_substantive) >= 2:
            concept_score = 0.95
        elif len(matched_substantive) == 1:
            concept_score = 0.75
        elif "gaming_setup" in tags or "fps_gaming" in tags or "mechanical_keyboards" in tags or "career_prep" in tags:
            concept_score = 0.60
        elif tags.intersection(HYPE_TAGS) or matched_text_hype:
            concept_score = 0.15
        else:
            concept_score = 0.40

        # Depth score based on declared depth and content format
        if reel.depth == DepthLevel.ADVANCED:
            depth_score = 0.90
        elif reel.depth == DepthLevel.INTERMEDIATE:
            depth_score = 0.70
        else:  # BEGINNER
            if tags.intersection(HYPE_TAGS) or matched_text_hype or reel.format == "listicle":
                depth_score = 0.20
            else:
                depth_score = 0.45

        return QualityScore(
            concept_anchor_score=round(concept_score, 4),
            depth_score=round(depth_score, 4),
        )

    def evaluate_hype(self, reel: Reel) -> HypeScore:
        """Produce continuous normalized [0, 1] hype and promotional language score."""
        tags = set(t.lower() for t in reel.concept_tags)
        tone = (reel.tone or "").lower()
        fmt = (reel.format or "").lower()
        text_content = f"{reel.title} {reel.transcript or ''}".lower()

        # Check explicit text hype phrases independent of pre-authored tags
        matched_text_hype = any(phrase in text_content for phrase in EXPLICIT_HYPE_PHRASES)

        # Pattern penalty: clickbait, guaranteed shortcuts, exaggerated claims
        matched_hype_tags = tags.intersection(HYPE_TAGS)
        if len(matched_hype_tags) >= 2 or (matched_text_hype and len(matched_hype_tags) >= 1):
            pattern_penalty = 0.95
        elif len(matched_hype_tags) == 1 or matched_text_hype:
            pattern_penalty = 0.85
        elif fmt == "listicle" and tone == "promotional":
            pattern_penalty = 0.70
        elif fmt == "hardware_comparison" or fmt == "vlog":
            pattern_penalty = 0.30
        else:
            pattern_penalty = 0.10

        # Promotional language score
        if tone == "promotional":
            promotional_score = 0.85
        elif tone == "humorous":
            promotional_score = 0.30
        elif tone in ("technical", "educational", "informative"):
            promotional_score = 0.10
        else:
            promotional_score = 0.25

        return HypeScore(
            pattern_penalty=round(pattern_penalty, 4),
            promotional_language_score=round(promotional_score, 4),
        )
