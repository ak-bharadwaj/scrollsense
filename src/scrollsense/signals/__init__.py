"""ReelSignal semantic extraction module for ScrollSense v4.

Architecture Roles:
- DeterministicSignalExtractor: baseline heuristic & regression oracle.
- LLMStructuredSignalExtractor: semantic production & demo extraction path.
"""

from scrollsense.signals.extractor import (
    MODEL_VERSION,
    ONTOLOGY_VERSION,
    SIGNAL_VERSION,
    DeterministicSignalExtractor,
    SignalExtractor,
)
from scrollsense.signals.llm_extractor import (
    ExtractionError,
    ExtractionValidationError,
    LLMStructuredSignalExtractor,
)
from scrollsense.signals.prompt import (
    StructuredExtractionPayload,
    format_extraction_prompt,
)
from scrollsense.signals.provider import (
    LLMConfig,
    LLMProvider,
    LLMProviderError,
)

__all__ = [
    "DeterministicSignalExtractor",
    "ExtractionError",
    "ExtractionValidationError",
    "LLMConfig",
    "LLMProvider",
    "LLMProviderError",
    "LLMStructuredSignalExtractor",
    "MODEL_VERSION",
    "ONTOLOGY_VERSION",
    "SIGNAL_VERSION",
    "SignalExtractor",
    "StructuredExtractionPayload",
    "format_extraction_prompt",
]
