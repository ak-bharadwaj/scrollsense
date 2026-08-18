"""Unit and integration tests for hardened Reel media asset ingestion and review workflow."""

from pathlib import Path
import tempfile
import pytest

from scrollsense.domain.enums import DepthLevel
from scrollsense.ingestion import (
    AssetManifest,
    DuplicateAssetError,
    GateRejectionError,
    HumanQCStatus,
    InstagramSourceAdapter,
    LocalFileSourceAdapter,
    ReelIngestor,
    ReelReviewer,
    ValidationStatus,
)


@pytest.fixture
def temp_content_dir() -> Path:
    """Create a temporary content directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_video_file(temp_content_dir: Path) -> Path:
    """Create a dummy binary media file representing a local reel video."""
    video_path = temp_content_dir / "sample_video.mp4"
    with open(video_path, "wb") as f:
        f.write(b"FAKE_MP4_HEADER_DATA_1234567890_SAMPLE_VIDEO_BYTES")
    return video_path


def test_license_cannot_default(sample_video_file: Path):
    """Test 1: Ingesting an asset without an explicit license raises ValueError (no silent default)."""
    adapter = LocalFileSourceAdapter()
    with pytest.raises(ValueError) as exc:
        adapter.load_asset(
            file_path=sample_video_file,
            title="Valid Title",
            transcript="Valid transcript",
            category="coding",
            license="",  # Empty license
            creator="Creator",
            difficulty="intermediate",
        )
    assert "Asset license must be explicitly provided" in str(exc.value)


def test_category_cannot_silently_default(sample_video_file: Path):
    """Test 2: Ingesting an asset without an explicit category raises ValueError."""
    adapter = LocalFileSourceAdapter()
    with pytest.raises(ValueError) as exc:
        adapter.load_asset(
            file_path=sample_video_file,
            title="Valid Title",
            transcript="Valid transcript",
            category="",  # Empty category
            license="CC-BY-4.0",
            creator="Creator",
            difficulty="intermediate",
        )
    assert "Asset category must be explicitly provided" in str(exc.value)


def test_ingestion_always_starts_pending(temp_content_dir: Path, sample_video_file: Path):
    """Test 3: Ingestion always creates PENDING_REVIEW in processed/, never automatically accepted."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_local_file(
        file_path=sample_video_file,
        title="Distributed Caching with Redis",
        transcript="How cache-aside and write-through patterns maintain consistency in distributed systems.",
        category="coding",
        license="CC-BY-4.0",
        creator="TechAcademy",
        difficulty="intermediate",
    )

    assert result.gate_result.passed is True
    assert result.accepted is False  # Must NOT be automatically accepted
    assert result.item.validation_status == ValidationStatus.PENDING_REVIEW
    assert result.item.human_qc_status == HumanQCStatus.PENDING
    assert Path(result.stored_path).parent == temp_content_dir / "processed"

    manifest = AssetManifest.load_from_json(temp_content_dir / "manifest.json")
    assert len(manifest.get_accepted_candidate_reels()) == 0


def test_approval_is_a_separate_operation(temp_content_dir: Path, sample_video_file: Path):
    """Test 4: Asset only enters accepted candidate corpus after explicit human QC approval."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)
    reviewer = ReelReviewer(content_dir=temp_content_dir)

    # 1. Ingest asset -> starts pending
    res = ingestor.ingest_local_file(
        file_path=sample_video_file,
        title="Kubernetes Pod Networking",
        transcript="Deep dive into kube-proxy routing, ingress TLS, and service mesh networking.",
        category="coding",
        license="MIT",
        creator="CloudMaster",
        difficulty="intermediate",
    )
    reel_id = res.item.reel_id

    manifest_before = AssetManifest.load_from_json(temp_content_dir / "manifest.json")
    assert len(manifest_before.get_accepted_candidate_reels()) == 0

    # 2. Perform separate human approval operation
    approved_item = reviewer.approve_reel(reel_id=reel_id, reviewer="lead_engineer", notes="High educational value")
    assert approved_item.validation_status == ValidationStatus.ACCEPTED
    assert approved_item.human_qc_status == HumanQCStatus.ACCEPTED
    assert approved_item.human_qc_record["reviewer"] == "lead_engineer"
    assert Path(approved_item.asset_path).parent == temp_content_dir / "accepted"

    manifest_after = AssetManifest.load_from_json(temp_content_dir / "manifest.json")
    accepted_reels = manifest_after.get_accepted_candidate_reels()
    assert len(accepted_reels) == 1
    assert accepted_reels[0].reel_id == reel_id


def test_rejected_gate_cannot_be_approved(temp_content_dir: Path, sample_video_file: Path):
    """Test 5: An asset rejected by automated gates cannot be approved by human QC."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)
    reviewer = ReelReviewer(content_dir=temp_content_dir)

    # Ingest hype trap -> gate rejection
    res = ingestor.ingest_local_file(
        file_path=sample_video_file,
        title="10 Secret AI Tools That Will Replace Programmers and Guarantee You a $200k Job!",
        transcript="Zero coding required! These secret tools will guarantee a job and instant wealth.",
        category="tech_news",
        license="CC0",
        creator="HypeGuru",
        difficulty="beginner",
    )
    assert res.item.validation_status == ValidationStatus.REJECTED_GATE

    # Attempting to approve gate-rejected item raises GateRejectionError
    with pytest.raises(GateRejectionError) as exc:
        reviewer.approve_reel(reel_id=res.item.reel_id, reviewer="lead_engineer")
    assert "rejected by automated integrity gates" in str(exc.value)


def test_human_qc_rejection_workflow(temp_content_dir: Path, sample_video_file: Path):
    """Test 6: Human QC rejection routes media to rejected/ with REJECTED_QC status."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)
    reviewer = ReelReviewer(content_dir=temp_content_dir)

    res = ingestor.ingest_local_file(
        file_path=sample_video_file,
        title="Rust Memory Management",
        transcript="Exploring lifetimes and ownership in Rust systems programming.",
        category="coding",
        license="Apache-2.0",
        creator="RustDev",
        difficulty="advanced",
    )

    rejected_item = reviewer.reject_reel(
        reel_id=res.item.reel_id,
        reviewer="lead_engineer",
        reason="Audio quality is too degraded for mobile playback",
    )
    assert rejected_item.validation_status == ValidationStatus.REJECTED_QC
    assert rejected_item.human_qc_status == HumanQCStatus.REJECTED
    assert Path(rejected_item.asset_path).parent == temp_content_dir / "rejected"


def test_duplicate_detection(temp_content_dir: Path, sample_video_file: Path):
    """Test 7: Ingesting duplicate video checksum raises DuplicateAssetError."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    ingestor.ingest_local_file(
        file_path=sample_video_file,
        title="Initial Asset",
        transcript="Initial valid transcript for testing.",
        category="coding",
        license="CC-BY-4.0",
        creator="Dev1",
        difficulty="intermediate",
    )

    with pytest.raises(DuplicateAssetError) as exc:
        ingestor.ingest_local_file(
            file_path=sample_video_file,
            title="Duplicate Attempt",
            transcript="Another transcript for testing duplicate check.",
            category="coding",
            license="CC-BY-4.0",
            creator="Dev2",
            difficulty="intermediate",
            allow_duplicate=False,
        )
    assert "is already ingested" in str(exc.value)


def test_provenance_and_semantic_signal_extraction(temp_content_dir: Path, sample_video_file: Path):
    """Test 8: Ingestion extracts semantic signals and preserves complete provenance."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_local_file(
        file_path=sample_video_file,
        title="OAuth2 Security Vulnerabilities",
        transcript="Explaining JWT token theft, HttpOnly cookies, and CSRF protection mechanisms in REST APIs.",
        category="coding",
        license="CC-BY-4.0",
        creator="SecOps",
        difficulty="intermediate",
        source_url="https://example.com/reels/oauth2",
        extraction_method="whisper_local",
    )

    item = result.item
    assert item.source_platform == "local_filesystem"
    assert item.extraction_method == "whisper_local"
    assert item.file_sha256 == ReelIngestor.compute_file_sha256(sample_video_file)
    assert "extracted_signals" in item.model_dump()
    assert "gate_passed" in item.provenance
    assert "quality_substance_score" in item.provenance


def test_source_adapter_abstraction(sample_video_file: Path):
    """Test 9: SourceAdapter abstractions load normalized payloads properly."""
    # Local adapter
    local_adapter = LocalFileSourceAdapter()
    payload = local_adapter.load_asset(
        file_path=sample_video_file,
        title="Local Title",
        transcript="Local transcript",
        category="coding",
        license="CC-BY-4.0",
        creator="LocalAuthor",
        difficulty="intermediate",
    )
    assert payload.source_platform == "local_filesystem"

    # Instagram adapter
    ig_adapter = InstagramSourceAdapter()
    ig_payload = ig_adapter.load_asset(
        media_id="1234567890",
        file_path=sample_video_file,
        title="IG Tech Clip",
        transcript="IG Transcript",
        category="coding",
        license="Authorized Reel License",
        creator="IGDev",
        difficulty="intermediate",
    )
    assert ig_payload.source_platform == "instagram"
    assert "1234567890" in ig_payload.source_url
