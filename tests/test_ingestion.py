"""Unit and integration tests for Reel media asset ingestion, validation, and manifest tracking."""

from pathlib import Path
import tempfile
import pytest

from scrollsense.domain.enums import DepthLevel
from scrollsense.ingestion import (
    AssetManifest,
    DuplicateAssetError,
    HumanQCStatus,
    MissingMetadataError,
    ReelIngestor,
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


def test_valid_ingestion_pending_qc(temp_content_dir: Path, sample_video_file: Path):
    """Test 1: Valid high-quality video ingestion routes to processed/ when human QC is pending."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_asset(
        file_path=sample_video_file,
        title="Distributed Caching with Redis & Invalidation",
        transcript="How cache-aside and write-through patterns maintain consistency in distributed systems.",
        category="coding",
        concepts=["system_design", "redis", "distributed_systems"],
        license="CC-BY-4.0",
        creator="TechAcademy",
        difficulty=DepthLevel.INTERMEDIATE,
        human_qc_status=HumanQCStatus.PENDING,
    )

    assert result.gate_result.passed is True
    assert result.accepted is False  # Pending QC is not in accepted candidate corpus yet
    assert result.item.validation_status == ValidationStatus.PENDING_REVIEW
    assert Path(result.stored_path).parent == temp_content_dir / "processed"
    assert Path(result.stored_path).exists()

    # Manifest verification
    manifest = AssetManifest.load_from_json(temp_content_dir / "manifest.json")
    assert result.item.reel_id in manifest.items
    assert manifest.get_by_reel_id(result.item.reel_id) is not None


def test_accepted_candidate_enters_accepted_pool(temp_content_dir: Path, sample_video_file: Path):
    """Test 2: Asset passing gates with accepted human QC routes to accepted/ and enters candidate corpus."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_asset(
        file_path=sample_video_file,
        title="Kubernetes Microservices Networking",
        transcript="Deep dive into kube-proxy routing, ingress TLS termination, and service mesh sidecars.",
        category="coding",
        concepts=["kubernetes", "docker", "cloud_networking"],
        license="MIT",
        creator="CloudMaster",
        difficulty=DepthLevel.INTERMEDIATE,
        human_qc_status=HumanQCStatus.ACCEPTED,
    )

    assert result.gate_result.passed is True
    assert result.accepted is True
    assert result.item.validation_status == ValidationStatus.ACCEPTED
    assert Path(result.stored_path).parent == temp_content_dir / "accepted"
    assert Path(result.stored_path).exists()

    manifest = AssetManifest.load_from_json(temp_content_dir / "manifest.json")
    accepted_reels = manifest.get_accepted_candidate_reels()
    assert len(accepted_reels) == 1
    assert accepted_reels[0].reel_id == result.item.reel_id


def test_failed_gate_routes_to_rejected_pool(temp_content_dir: Path, sample_video_file: Path):
    """Test 3: Low-substance exaggerated hype video fails gate and is routed to rejected/."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_asset(
        file_path=sample_video_file,
        title="10 Secret AI Tools That Will Replace Programmers and Guarantee You a $200k Job Overnight!",
        transcript="Zero coding required! These secret tools will guarantee a job and instant wealth.",
        category="tech_news",
        concepts=["ai_hype", "career_shortcuts"],
        license="CC0",
        creator="HypeGuru",
        difficulty=DepthLevel.BEGINNER,
        human_qc_status=HumanQCStatus.ACCEPTED,  # Even if QC was accepted, gate failure overrides
    )

    assert result.gate_result.passed is False
    assert result.accepted is False
    assert result.item.validation_status == ValidationStatus.REJECTED_GATE
    assert Path(result.stored_path).parent == temp_content_dir / "rejected"

    # Manifest verification: Must NOT be in accepted reels
    manifest = AssetManifest.load_from_json(temp_content_dir / "manifest.json")
    assert len(manifest.get_accepted_candidate_reels()) == 0


def test_human_qc_rejection_routes_to_rejected_pool(temp_content_dir: Path, sample_video_file: Path):
    """Test 4: Video passing gates but rejected by human QC is routed to rejected/."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_asset(
        file_path=sample_video_file,
        title="Rust Memory Safety and Borrow Checker",
        transcript="Exploring lifetimes and ownership in Rust systems programming.",
        category="coding",
        concepts=["rust", "memory_safety"],
        license="Apache-2.0",
        creator="RustDev",
        difficulty=DepthLevel.ADVANCED,
        human_qc_status=HumanQCStatus.REJECTED,
    )

    assert result.gate_result.passed is True
    assert result.accepted is False
    assert result.item.validation_status == ValidationStatus.REJECTED_QC
    assert Path(result.stored_path).parent == temp_content_dir / "rejected"


def test_missing_metadata_raises_error(temp_content_dir: Path, sample_video_file: Path):
    """Test 5: Ingesting asset with missing title or transcript raises MissingMetadataError."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    with pytest.raises(MissingMetadataError) as exc:
        ingestor.ingest_asset(
            file_path=sample_video_file,
            title="",  # Empty title
            transcript="Some valid transcript",
            category="coding",
            concepts=["java"],
            license="CC-BY-4.0",
            creator="Creator",
        )
    assert "Asset title is required" in str(exc.value)

    with pytest.raises(MissingMetadataError) as exc:
        ingestor.ingest_asset(
            file_path=sample_video_file,
            title="Valid Title",
            transcript="",  # Empty transcript
            category="coding",
            concepts=["java"],
            license="CC-BY-4.0",
            creator="Creator",
        )
    assert "Asset transcript is required" in str(exc.value)


def test_duplicate_asset_detection(temp_content_dir: Path, sample_video_file: Path):
    """Test 6: Ingesting duplicate video file checksum raises DuplicateAssetError unless overridden."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    # First ingestion succeeds
    ingestor.ingest_asset(
        file_path=sample_video_file,
        title="Initial Asset",
        transcript="Initial valid transcript for testing.",
        category="coding",
        concepts=["docker"],
        license="CC-BY-4.0",
        creator="Dev1",
    )

    # Re-ingesting identical binary file raises DuplicateAssetError
    with pytest.raises(DuplicateAssetError) as exc:
        ingestor.ingest_asset(
            file_path=sample_video_file,
            title="Duplicate Attempt",
            transcript="Another transcript for testing duplicate check.",
            category="coding",
            concepts=["docker"],
            license="CC-BY-4.0",
            creator="Dev2",
            allow_duplicate=False,
        )
    assert "is already ingested" in str(exc.value)


def test_deterministic_reel_id_generation(temp_content_dir: Path, sample_video_file: Path):
    """Test 7: Deterministic ID generator produces identical ID for same file and metadata."""
    file_hash = ReelIngestor.compute_file_sha256(sample_video_file)

    id_1 = ReelIngestor.generate_deterministic_reel_id("System Design Redis Caching", "TechCorp", file_hash)
    id_2 = ReelIngestor.generate_deterministic_reel_id("System Design Redis Caching", "TechCorp", file_hash)

    assert id_1 == id_2
    assert id_1.startswith("reel_techcorp_system_design_redis_")
    assert file_hash[:8] in id_1


def test_provenance_preservation(temp_content_dir: Path, sample_video_file: Path):
    """Test 8: Ingested manifest item preserves complete gate, checksum, and file provenance."""
    ingestor = ReelIngestor(content_dir=temp_content_dir)

    result = ingestor.ingest_asset(
        file_path=sample_video_file,
        title="OAuth2 Security Vulnerabilities",
        transcript="Explaining JWT token theft, HttpOnly cookies, and CSRF protection mechanisms.",
        category="coding",
        concepts=["cybersecurity", "oauth2", "jwt"],
        license="CC-BY-4.0",
        creator="SecOps",
        difficulty=DepthLevel.INTERMEDIATE,
        source_url="https://example.com/reels/oauth2",
    )

    item = result.item
    assert item.file_sha256 == ReelIngestor.compute_file_sha256(sample_video_file)
    assert item.source_url == "https://example.com/reels/oauth2"
    assert "gate_passed" in item.provenance
    assert "quality_substance_score" in item.provenance
    assert item.provenance["original_filename"] == "sample_video.mp4"
    assert item.provenance["file_size_bytes"] > 0
