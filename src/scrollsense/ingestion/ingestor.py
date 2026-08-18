"""Deterministic pipeline for ingesting, validating, and cataloging licensed Reel media assets."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.gates import GateResult
from scrollsense.domain.reels import Reel
from scrollsense.gates.evaluator import CandidateGateEvaluator
from scrollsense.ingestion.manifest import (
    AssetManifest,
    HumanQCStatus,
    ReelAssetManifestItem,
    ValidationStatus,
)


class DuplicateAssetError(ValueError):
    """Raised when an identical binary media asset is submitted for ingestion."""


class MissingMetadataError(ValueError):
    """Raised when essential metadata fields are missing or empty."""


class IngestionResult(BaseModel):
    """Result of an asset ingestion and validation operation."""

    model_config = ConfigDict(extra="forbid")

    item: ReelAssetManifestItem = Field(..., description="Manifest record for the asset")
    reel: Reel = Field(..., description="Constructed domain Reel entity")
    gate_result: GateResult = Field(..., description="Gate evaluation result")
    accepted: bool = Field(..., description="Whether asset entered the accepted candidate corpus")
    stored_path: str = Field(..., description="Final storage path of the media asset")


class ReelIngestor:
    """Orchestrates deterministic media file ingestion, gate validation, and cataloging."""

    def __init__(
        self,
        content_dir: Path | str,
        gate_evaluator: CandidateGateEvaluator | None = None,
        manifest_path: Path | str | None = None,
    ) -> None:
        self.content_dir = Path(content_dir)
        self.incoming_dir = self.content_dir / "incoming"
        self.processed_dir = self.content_dir / "processed"
        self.accepted_dir = self.content_dir / "accepted"
        self.rejected_dir = self.content_dir / "rejected"

        for d in (self.incoming_dir, self.processed_dir, self.accepted_dir, self.rejected_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.gate_evaluator = gate_evaluator or CandidateGateEvaluator()
        self.manifest_path = Path(manifest_path) if manifest_path else self.content_dir / "manifest.json"
        self.manifest = AssetManifest.load_from_json(self.manifest_path)

    @staticmethod
    def compute_file_sha256(file_path: Path) -> str:
        """Compute SHA256 hexadecimal checksum of a local file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def generate_deterministic_reel_id(title: str, creator: str, file_hash: str) -> str:
        """Generate a deterministic, slugged reel identifier."""
        clean_title = "".join(c if c.isalnum() else "_" for c in title.lower())[:24].strip("_")
        clean_creator = "".join(c if c.isalnum() else "_" for c in creator.lower())[:12].strip("_")
        hash_suffix = file_hash[:8]
        return f"reel_{clean_creator}_{clean_title}_{hash_suffix}"

    def ingest_asset(
        self,
        file_path: Path | str,
        title: str,
        transcript: str,
        category: str,
        concepts: list[str],
        license: str,
        creator: str,
        difficulty: DepthLevel = DepthLevel.INTERMEDIATE,
        source_url: str | None = None,
        human_qc_status: HumanQCStatus = HumanQCStatus.PENDING,
        allow_duplicate: bool = False,
    ) -> IngestionResult:
        """Ingest a raw local media asset, evaluate gates, and store in appropriate corpus directory."""
        asset_file = Path(file_path)
        if not asset_file.exists() or not asset_file.is_file():
            raise FileNotFoundError(f"Source media asset file not found: {asset_file}")

        # 1. Validate mandatory metadata
        if not title or not title.strip():
            raise MissingMetadataError("Asset title is required and cannot be empty")
        if not transcript or not transcript.strip():
            raise MissingMetadataError("Asset transcript is required and cannot be empty")
        if not category or not category.strip():
            raise MissingMetadataError("Asset category is required and cannot be empty")
        if not license or not license.strip():
            raise MissingMetadataError("Asset license is required and cannot be empty")
        if not creator or not creator.strip():
            raise MissingMetadataError("Asset creator attribution is required and cannot be empty")

        # 2. Compute file checksum and check duplicate
        file_hash = self.compute_file_sha256(asset_file)
        existing = self.manifest.get_by_sha256(file_hash)
        if existing and not allow_duplicate:
            raise DuplicateAssetError(
                f"Asset file with checksum {file_hash} is already ingested under reel_id '{existing.reel_id}'"
            )

        # 3. Generate deterministic reel_id and domain Reel
        reel_id = self.generate_deterministic_reel_id(title, creator, file_hash)
        reel = Reel(
            reel_id=reel_id,
            title=title.strip(),
            category=category.strip(),
            format="tutorial",
            tone="instructional",
            depth=difficulty,
            concept_tags=[c.strip().lower() for c in concepts if c.strip()],
            transcript=transcript.strip(),
        )

        # 4. Evaluate quality, hype, and safety gates
        gate_result = self.gate_evaluator.evaluate(reel)
        quality_score = gate_result.quality.overall
        hype_score = gate_result.hype.overall
        safety_passed = gate_result.safety.passed

        # 5. Determine validation status and target directory
        if not gate_result.passed:
            validation_status = ValidationStatus.REJECTED_GATE
            dest_dir = self.rejected_dir
            is_accepted = False
        else:
            if human_qc_status == HumanQCStatus.ACCEPTED:
                validation_status = ValidationStatus.ACCEPTED
                dest_dir = self.accepted_dir
                is_accepted = True
            elif human_qc_status == HumanQCStatus.REJECTED:
                validation_status = ValidationStatus.REJECTED_QC
                dest_dir = self.rejected_dir
                is_accepted = False
            else:
                validation_status = ValidationStatus.PENDING_REVIEW
                dest_dir = self.processed_dir
                is_accepted = False

        # 6. Copy asset file to target storage directory
        dest_filename = f"{reel_id}{asset_file.suffix}"
        target_path = dest_dir / dest_filename
        shutil.copy2(asset_file, target_path)

        # 7. Record provenance trace
        provenance = {
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "gate_passed": gate_result.passed,
            "rejection_reason": gate_result.rejection_reason,
            "quality_substance_score": quality_score,
            "hype_score": hype_score,
            "safety_passed": safety_passed,
            "original_filename": asset_file.name,
            "file_size_bytes": asset_file.stat().st_size,
        }

        # 8. Create manifest item and save manifest
        item = ReelAssetManifestItem(
            reel_id=reel_id,
            asset_path=str(target_path.resolve()),
            source_url=source_url,
            license=license.strip(),
            creator=creator.strip(),
            download_date=datetime.now(timezone.utc).isoformat(),
            title=title.strip(),
            transcript=transcript.strip(),
            category=category.strip(),
            concepts=reel.concept_tags,
            difficulty=difficulty,
            quality=round(quality_score, 4),
            hype=round(hype_score, 4),
            safety=safety_passed,
            validation_status=validation_status,
            human_qc_status=human_qc_status,
            provenance=provenance,
            file_sha256=file_hash,
        )

        self.manifest.add_or_update_item(item)
        self.manifest.save_to_json(self.manifest_path)

        return IngestionResult(
            item=item,
            reel=reel,
            gate_result=gate_result,
            accepted=is_accepted,
            stored_path=str(target_path.resolve()),
        )
