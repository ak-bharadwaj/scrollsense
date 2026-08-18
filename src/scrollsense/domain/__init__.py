"""Domain models, enums, and data contracts for ScrollSense v4."""

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import (
    ConfidenceBucket,
    DepthLevel,
    EvidenceType,
    FeedbackOutcome,
    NodeType,
    RelationType,
    RetrievalSource,
    TechCategory,
)
from scrollsense.domain.feedback import FeedbackEvent
from scrollsense.domain.gates import (
    GateResult,
    HypeScore,
    QualityScore,
    SafetyResult,
)
from scrollsense.domain.graph import (
    GraphEdge,
    GraphNode,
    IdentitySkillGraph,
)
from scrollsense.domain.persona import InterestState
from scrollsense.domain.ranking import ObjectiveScores
from scrollsense.domain.recommendation import (
    Recommendation,
    RecommendationOutput,
)
from scrollsense.domain.reels import (
    InterestEvidence,
    Reel,
    ReelSignal,
)

__all__ = [
    "Candidate",
    "ConfidenceBucket",
    "DepthLevel",
    "EvidenceType",
    "FeedbackEvent",
    "FeedbackOutcome",
    "GateResult",
    "GraphEdge",
    "GraphNode",
    "HypeScore",
    "IdentitySkillGraph",
    "InterestEvidence",
    "InterestState",
    "NodeType",
    "ObjectiveScores",
    "QualityScore",
    "Recommendation",
    "RecommendationOutput",
    "Reel",
    "ReelSignal",
    "RelationType",
    "RetrievalSource",
    "SafetyResult",
    "TechCategory",
]
