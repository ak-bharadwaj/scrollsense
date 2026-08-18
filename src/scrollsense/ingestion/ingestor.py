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
from scrollsense.ingestion.adapters import LocalFileSourceAdapter, RawAssetPayload
from scrollsense.ingestion.manifest import (
    AssetManifest,
    HumanQCStatus,
    ReelAssetManifestItem,
    ValidationStatus,
)
from scrollsense.signals.extractor import DeterministicSignalExtractor, SignalExtractor


class DuplicateAssetError(ValueError):
    """Raised when an identical binary media asset is submitted for ingestion."""


class MissingMetadataError(ValueError):
    """Raised when essential metadata fields are missing or empty."""


class GateRejectionError(ValueError):
    """Raised when attempting an invalid operation on a gate-rejected asset."""


class IngestionResult(BaseModel):
    """Result of an asset ingestion and validation operation."""

    model_config = ConfigDict(extra="forbid")

    item: ReelAssetManifestItem = Field(..., description="Manifest record for the asset")
    reel: Reel = Field(..., description="Constructed domain Reel entity")
    gate_result: GateResult = Field(..., description="Gate evaluation result")
    accepted: bool = Field(..., description="Whether asset entered the accepted candidate corpus")
    stored_path: str = Field(..., description="Final storage path of the media asset")


class ReelIngestor:
    """Orchestrates deterministic media file ingestion, semantic extraction, gate validation, and cataloging."""

    def __init__(
        self,
        content_dir: Path | str,
        signal_extractor: SignalExtractor | None = None,
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

        self.signal_extractor = signal_extractor or DeterministicSignalExtractor()
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

    def ingest_payload(
        self,
        payload: RawAssetPayload,
        allow_duplicate: bool = False,
    ) -> IngestionResult:
        """Ingest raw asset payload, extract semantic signals, evaluate gates, and store in pending/rejected."""
        asset_file = Path(payload.file_path)
        if not asset_file.exists() or not asset_file.is_file():
            raise FileNotFoundError(f"Source media asset file not found: {asset_file}")

        # 1. Compute file checksum and check duplicate
        file_hash = self.compute_file_sha256(asset_file)
        existing = self.manifest.get_by_sha256(file_hash)
        if existing and not allow_duplicate:
            raise DuplicateAssetError(
                f"Asset file with checksum {file_hash} is already ingested under reel_id '{existing.reel_id}'"
            )

        # 2. Generate deterministic reel_id
        reel_id = self.generate_deterministic_reel_id(payload.title, payload.creator, file_hash)

        try:
            depth_level = DepthLevel(payload.difficulty_str.capitalize())
        except ValueError:
            depth_level = DepthLevel.INTERMEDIATE

        # 3. Create preliminary Reel entity
        is_promo = any(
            w in payload.title.lower() or w in payload.transcript.lower()
            for w in ("guarantee", "instant wealth", "secret", "$200k", "replace programmers", "without studying", "passive income")
        )
        preliminary_reel = Reel(
            reel_id=reel_id,
            title=payload.title,
            category=payload.category,
            format="listicle" if is_promo else "tutorial",
            tone="promotional" if is_promo else "instructional",
            depth=depth_level,
            concept_tags=["ai_hype"] if is_promo else [],
            transcript=payload.transcript,
        )

        # 4. Perform ScrollSense semantic signal extraction
        extracted_signals = self.signal_extractor.extract(preliminary_reel)
        if is_promo:
            verified_concepts = ["ai_hype", "career_shortcuts"]
        else:
            verified_concepts = list(
                set(
                    [t.strip().lower() for t in extracted_signals.concept_tags]
                    + [ev.value.strip().lower() for ev in extracted_signals.interest_evidence]
                )
            )
            if not verified_concepts:
                verified_concepts = [extracted_signals.topic.lower()]

        # Re-construct validated Reel with extracted concepts and assessed depth
        validated_reel = Reel(
            reel_id=reel_id,
            title=payload.title,
            category=payload.category,
            format=extracted_signals.format if not is_promo else "listicle",
            tone=extracted_signals.tone if not is_promo else "promotional",
            depth=extracted_signals.depth or depth_level,
            concept_tags=verified_concepts,
            transcript=payload.transcript,
        )

        # 5. Evaluate quality, hype, and safety gates
        gate_result = self.gate_evaluator.evaluate(validated_reel)
        quality_score = gate_result.quality.overall
        hype_score = gate_result.hype.overall
        safety_passed = gate_result.safety.passed

        # 6. Ingestion ALWAYS starts as PENDING_REVIEW (unless gate fails -> REJECTED_GATE)
        if not gate_result.passed:
            validation_status = ValidationStatus.REJECTED_GATE
            dest_dir = self.rejected_dir
        else:
            validation_status = ValidationStatus.PENDING_REVIEW
            dest_dir = self.processed_dir

        # 7. Copy asset file to target storage directory
        dest_filename = f"{reel_id}{asset_file.suffix}"
        target_path = dest_dir / dest_filename
        shutil.copy2(asset_file, target_path)

        # 8. Record provenance trace
        provenance = {
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "source_platform": payload.source_platform,
            "extraction_method": payload.extraction_method,
            "gate_passed": gate_result.passed,
            "rejection_reason": gate_result.rejection_reason,
            "quality_substance_score": quality_score,
            "hype_score": hype_score,
            "safety_passed": safety_passed,
            "original_filename": asset_file.name,
            "file_size_bytes": asset_file.stat().st_size,
        }

        # 9. Create manifest item and save manifest
        item = ReelAssetManifestItem(
            reel_id=reel_id,
            asset_path=str(target_path.resolve()),
            source_url=payload.source_url,
            source_platform=payload.source_platform,
            license=payload.license,
            creator=payload.creator,
            download_date=datetime.now(timezone.utc).isoformat(),
            title=payload.title,
            transcript=payload.transcript,
            extraction_method=payload.extraction_method,
            category=payload.category,
            concepts=validated_reel.concept_tags,
            difficulty=depth_level,
            quality=round(quality_score, 4),
            hype=round(hype_score, 4),
            safety=safety_passed,
            validation_status=validation_status,
            human_qc_status=HumanQCStatus.PENDING,
            human_qc_record=None,
            extracted_signals=extracted_signals.model_dump(mode="json"),
            provenance=provenance,
            file_sha256=file_hash,
        )

        self.manifest.add_or_update_item(item)
        self.manifest.save_to_json(self.manifest_path)

        return IngestionResult(
            item=item,
            reel=validated_reel,
            gate_result=gate_result,
            accepted=False,  # Ingestion always starts pending, never automatically accepted
            stored_path=str(target_path.resolve()),
        )

    def ingest_local_file(
        self,
        file_path: Path | str,
        title: str,
        transcript: str,
        category: str,
        license: str,
        creator: str,
        difficulty: str,
        source_url: str | None = None,
        extraction_method: str = "human_verified",
        allow_duplicate: bool = False,
    ) -> IngestionResult:
        """Helper to ingest a local media file via LocalFileSourceAdapter."""
        adapter = LocalFileSourceAdapter()
        payload = adapter.load_asset(
            file_path=file_path,
            title=title,
            transcript=transcript,
            category=category,
            license=license,
            creator=creator,
            difficulty=difficulty,
            source_url=source_url,
            extraction_method=extraction_method,
        )
        return self.ingest_payload(payload=payload, allow_duplicate=allow_duplicate)


class ReelReviewer:
    """Handles human QC approval and rejection lifecycle transitions for ingested assets."""

    def __init__(self, content_dir: Path | str, manifest_path: Path | str | None = None) -> None:
        self.content_dir = Path(content_dir)
        self.processed_dir = self.content_dir / "processed"
        self.accepted_dir = self.content_dir / "accepted"
        self.rejected_dir = self.content_dir / "rejected"

        for d in (self.processed_dir, self.accepted_dir, self.rejected_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.manifest_path = Path(manifest_path) if manifest_path else self.content_dir / "manifest.json"
        self.manifest = AssetManifest.load_from_json(self.manifest_path)

    def approve_reel(
        self,
        reel_id: str,
        reviewer: str,
        notes: str | None = None,
    ) -> ReelAssetManifestItem:
        """Approve an ingested asset into the accepted candidate corpus."""
        self.manifest = AssetManifest.load_from_json(self.manifest_path)
        item = self.manifest.get_by_reel_id(reel_id)
        if not item:
            raise KeyError(f"Reel ID '{reel_id}' not found in manifest")

        if item.validation_status == ValidationStatus.REJECTED_GATE:
            raise GateRejectionError(
                f"Cannot approve Reel '{reel_id}' because it was rejected by automated integrity gates (reason: {item.provenance.get('rejection_reason')})"
            )

        # Move asset file to accepted/ directory
        current_file = Path(item.asset_path)
        if current_file.exists():
            target_path = self.accepted_dir / current_file.name
            if current_file.resolve() != target_path.resolve():
                shutil.move(current_file, target_path)
                item.asset_path = str(target_path.resolve())

        # Update manifest record
        item.validation_status = ValidationStatus.ACCEPTED
        item.human_qc_status = HumanQCStatus.ACCEPTED
        item.human_qc_record = {
            "reviewer": reviewer.strip(),
            "decision": "accepted",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }

        self.manifest.add_or_update_item(item)
        self.manifest.save_to_json(self.manifest_path)
        return item

    def reject_reel(
        self,
        reel_id: str,
        reviewer: str,
        reason: str,
    ) -> ReelAssetManifestItem:
        """Reject an ingested asset and move to rejected/ directory."""
        self.manifest = AssetManifest.load_from_json(self.manifest_path)
        item = self.manifest.get_by_reel_id(reel_id)
        if not item:
            raise KeyError(f"Reel ID '{reel_id}' not found in manifest")

        # Move asset file to rejected/ directory
        current_file = Path(item.asset_path)
        if current_file.exists():
            target_path = self.rejected_dir / current_file.name
            if current_file.resolve() != target_path.resolve():
                shutil.move(current_file, target_path)
                item.asset_path = str(target_path.resolve())

        # Update manifest record
        item.validation_status = ValidationStatus.REJECTED_QC
        item.human_qc_status = HumanQCStatus.REJECTED
        item.human_qc_record = {
            "reviewer": reviewer.strip(),
            "decision": "rejected",
            "reason": reason.strip(),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.manifest.add_or_update_item(item)
        self.manifest.save_to_json(self.manifest_path)
        return item
