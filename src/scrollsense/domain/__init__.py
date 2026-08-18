"""Domain models, enums, and data contracts for ScrollSense v4."""

from scrollsense.domain.candidates import Candidate
from scrollsense.domain.enums import (
    ConfidenceBucket,
    DepthLevel,
    FeedbackOutcome,
    NodeType,
    RelationType,
    RetrievalSource,
)
from scrollsense.domain.feedback import FeedbackEvent
from scrollsense.domain.gates import (
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
from scrollsense.domain.recommendation import Recommendation
from scrollsense.domain.reels import (
    InterestEvidence,
    Reel,
    ReelSignal,
)

__all__ = [
    "Candidate",
    "ConfidenceBucket",
    "DepthLevel",
    "FeedbackEvent",
    "FeedbackOutcome",
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
    "Reel",
    "ReelSignal",
    "RelationType",
    "RetrievalSource",
    "SafetyResult",
]
