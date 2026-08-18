"""Domain models for feedback capture."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import FeedbackOutcome


class FeedbackEvent(BaseModel):
    """Logged user interaction outcome on a recommendation."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(..., min_length=1, description="Target recommendation ID")
    student_id: str = Field(..., min_length=1, description="Student / viewer ID")
    outcome: FeedbackOutcome = Field(..., description="Observed outcome: accepted, skipped, or not_interested")
    observed_at: datetime = Field(..., description="Timestamp when interaction was observed")
