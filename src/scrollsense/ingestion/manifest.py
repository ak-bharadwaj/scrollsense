"""Reel asset manifest and provenance tracking for licensed content ingestion."""

from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.reels import Reel


class HumanQCStatus(str, Enum):
    """Human Quality Control validation status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ValidationStatus(str, Enum):
    """Pipeline gate and review validation status."""

    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    REJECTED_GATE = "rejected_gate"
    REJECTED_QC = "rejected_qc"


class ReelAssetManifestItem(BaseModel):
    """Structured record of an ingested licensed Reel asset."""

    model_config = ConfigDict(extra="forbid")

    reel_id: str = Field(..., description="Deterministic unique reel identifier")
    asset_path: str = Field(..., description="Relative or absolute path to the stored media asset")
    source_url: str | None = Field(default=None, description="Original source URL or repository link")
    license: str = Field(..., description="Content license (e.g., CC-BY-4.0, MIT, Educational Fair Use)")
    creator: str = Field(..., description="Creator, channel, or copyright attribution")
    download_date: str = Field(..., description="ISO timestamp of asset acquisition/ingestion")
    title: str = Field(..., description="Content title")
    transcript: str = Field(..., description="Verbatim or summarized text transcript")
    category: str = Field(..., description="Primary topic category")
    concepts: list[str] = Field(..., description="Extracted technical concepts and tags")
    difficulty: DepthLevel = Field(..., description="Estimated technical depth level")
    quality: float = Field(..., ge=0.0, le=1.0, description="Evaluated substance/quality score")
    hype: float = Field(..., ge=0.0, le=1.0, description="Evaluated hype penalty score")
    safety: bool = Field(..., description="Whether content passed strict safety policy")
    validation_status: ValidationStatus = Field(..., description="Overall ingestion validation status")
    human_qc_status: HumanQCStatus = Field(default=HumanQCStatus.PENDING, description="Human QC review status")
    provenance: dict[str, Any] = Field(default_factory=dict, description="Audit trace of extractor and gate results")
    file_sha256: str | None = Field(default=None, description="SHA256 checksum of raw binary asset")

    def to_domain_reel(self) -> Reel:
        """Convert manifest item to core Reel domain entity."""
        return Reel(
            reel_id=self.reel_id,
            title=self.title,
            category=self.category,
            format="tutorial",
            tone="instructional",
            depth=self.difficulty,
            concept_tags=self.concepts,
            transcript=self.transcript,
        )


class AssetManifest(BaseModel):
    """Collection of all ingested assets and checksum index."""

    model_config = ConfigDict(extra="forbid")

    items: dict[str, ReelAssetManifestItem] = Field(
        default_factory=dict,
        description="Map of reel_id to ReelAssetManifestItem",
    )
    by_sha256: dict[str, str] = Field(
        default_factory=dict,
        description="Map of file sha256 checksum to reel_id for deduplication",
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of last manifest modification",
    )

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> "AssetManifest":
        """Load manifest from JSON file, initializing empty manifest if file does not exist."""
        path = Path(file_path)
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return cls.model_validate(raw_data)

    def save_to_json(self, file_path: str | Path) -> None:
        """Persist manifest to JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2)

    def add_or_update_item(self, item: ReelAssetManifestItem) -> None:
        """Record or update an asset item and update sha256 index."""
        self.items[item.reel_id] = item
        if item.file_sha256:
            self.by_sha256[item.file_sha256] = item.reel_id

    def get_by_reel_id(self, reel_id: str) -> ReelAssetManifestItem | None:
        return self.items.get(reel_id)

    def get_by_sha256(self, sha256_hash: str) -> ReelAssetManifestItem | None:
        reel_id = self.by_sha256.get(sha256_hash)
        if reel_id:
            return self.items.get(reel_id)
        return None

    def get_accepted_candidate_reels(self) -> list[Reel]:
        """Return list of Reel entities for all assets with ACCEPTED status and ACCEPTED human QC."""
        accepted: list[Reel] = []
        for item in self.items.values():
            if item.validation_status == ValidationStatus.ACCEPTED and item.human_qc_status == HumanQCStatus.ACCEPTED:
                accepted.append(item.to_domain_reel())
        return sorted(accepted, key=lambda r: r.reel_id)
