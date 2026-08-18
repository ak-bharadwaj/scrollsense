"""ScrollSense v4: Identity-Aware Latent Skill Graph Recommender."""

from scrollsense.engine import (
    EngineResult,
    NoEligibleCandidatesError,
    ScrollSenseEngine,
)

__version__ = "0.1.0"

__all__ = [
    "EngineResult",
    "NoEligibleCandidatesError",
    "ScrollSenseEngine",
    "__version__",
]
