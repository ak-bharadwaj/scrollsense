"""Integration tests for the ScrollSense FastAPI production API contracts and security boundaries."""

from datetime import datetime, timezone
import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from scrollsense.api import app, create_app
from scrollsense.domain.enums import DepthLevel, TechCategory
from scrollsense.domain.reels import Reel
from scrollsense.ingestion.manifest import (
    AssetManifest,
    HumanQCStatus,
    ReelAssetManifestItem,
    ValidationStatus,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def temp_content_setup(tmp_path: Path):
    """Fixture providing populated accepted and rejected content directories with a valid manifest."""
    content_dir = tmp_path / "content"
    accepted_dir = content_dir / "accepted"
    rejected_dir = content_dir / "rejected"
    processed_dir = content_dir / "processed"

    for d in (accepted_dir, rejected_dir, processed_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Valid accepted video with custom extension (.webm)
    accepted_webm = accepted_dir / "reel_custom_asset.webm"
    accepted_webm.write_bytes(b"ACCEPTED_WEBM_VIDEO_DATA")

    # 2. Valid accepted video (.mp4)
    accepted_mp4 = accepted_dir / "reel_ai_substance.mp4"
    accepted_mp4.write_bytes(b"ACCEPTED_MP4_VIDEO_DATA")

    # 3. Accepted status but missing on disk
    missing_asset_path = accepted_dir / "reel_missing_on_disk.mp4"

    # 4. Rejected video in rejected/
    rejected_mp4 = rejected_dir / "reel_ai_hype_trap.mp4"
    rejected_mp4.write_bytes(b"REJECTED_HYPE_DATA")

    # Create AssetManifest
    manifest = AssetManifest()
    manifest.add_or_update_item(
        ReelAssetManifestItem(
            reel_id="reel_custom_asset",
            asset_path=str(accepted_webm.resolve()),
            source_url="https://example.com/custom",
            source_platform="local_filesystem",
            license="MIT",
            creator="OpenSourceLab",
            download_date=datetime.now(timezone.utc).isoformat(),
            title="Custom WebM Asset Reel",
            transcript="Explaining custom WebM video asset ingestion.",
            extraction_method="human_verified",
            category="coding",
            concepts=["docker", "linux"],
            difficulty=DepthLevel.INTERMEDIATE,
            quality=0.85,
            hype=0.10,
            safety=True,
            validation_status=ValidationStatus.ACCEPTED,
            human_qc_status=HumanQCStatus.ACCEPTED,
            file_sha256="fake_sha256_custom",
        )
    )
    manifest.add_or_update_item(
        ReelAssetManifestItem(
            reel_id="reel_ai_substance",
            asset_path=str(accepted_mp4.resolve()),
            source_url=None,
            source_platform="local_filesystem",
            license="Apache-2.0",
            creator="AIResearchGroup",
            download_date=datetime.now(timezone.utc).isoformat(),
            title="Attention Mechanism & Transformer Neural Network Math Explained",
            transcript="Mathematical breakdown of query, key, value matrix multiplications in self-attention.",
            extraction_method="human_verified",
            category="ai",
            concepts=["transformers", "attention_mechanism"],
            difficulty=DepthLevel.INTERMEDIATE,
            quality=0.88,
            hype=0.05,
            safety=True,
            validation_status=ValidationStatus.ACCEPTED,
            human_qc_status=HumanQCStatus.ACCEPTED,
            file_sha256="fake_sha256_ai",
        )
    )
    manifest.add_or_update_item(
        ReelAssetManifestItem(
            reel_id="reel_missing_on_disk",
            asset_path=str(missing_asset_path.resolve()),
            source_url=None,
            source_platform="local_filesystem",
            license="MIT",
            creator="GhostCreator",
            download_date=datetime.now(timezone.utc).isoformat(),
            title="Ghost Asset Title",
            transcript="Ghost transcript text.",
            extraction_method="human_verified",
            category="coding",
            concepts=["git"],
            difficulty=DepthLevel.BEGINNER,
            quality=0.80,
            hype=0.10,
            safety=True,
            validation_status=ValidationStatus.ACCEPTED,
            human_qc_status=HumanQCStatus.ACCEPTED,
            file_sha256="fake_sha256_ghost",
        )
    )
    manifest.add_or_update_item(
        ReelAssetManifestItem(
            reel_id="reel_ai_hype_trap",
            asset_path=str(rejected_mp4.resolve()),
            source_url=None,
            source_platform="local_filesystem",
            license="CC0",
            creator="HypeInfluencer",
            download_date=datetime.now(timezone.utc).isoformat(),
            title="10 Secret AI Tools That Will Replace Programmers!",
            transcript="Get rich overnight without coding.",
            extraction_method="human_verified",
            category="tech_news",
            concepts=["ai_hype"],
            difficulty=DepthLevel.BEGINNER,
            quality=0.20,
            hype=0.90,
            safety=True,
            validation_status=ValidationStatus.REJECTED_GATE,
            human_qc_status=HumanQCStatus.PENDING,
            file_sha256="fake_sha256_hype",
        )
    )
    manifest.save_to_json(content_dir / "manifest.json")
    return content_dir


@pytest.fixture
def client(temp_content_setup: Path) -> TestClient:
    """Fixture providing TestClient with populated manifest and media content."""
    test_app = create_app(
        content_dir=temp_content_setup,
        inputs_path=INPUTS_PATH,
        candidates_path=CANDIDATES_PATH,
        graph_path=GRAPH_PATH,
        allowed_origins=["https://scrollsense.app", "http://localhost:3000"],
    )
    return TestClient(test_app)


def test_cors_explicit_configuration(temp_content_setup: Path):
    """Test 1: Explicit CORS configuration is respected and does not use wildcard with credentials."""
    app_cors = create_app(
        content_dir=temp_content_setup,
        inputs_path=INPUTS_PATH,
        candidates_path=CANDIDATES_PATH,
        graph_path=GRAPH_PATH,
        allowed_origins=["https://production.scrollsense.com"],
    )
    c = TestClient(app_cors)

    # Allowed origin receives CORS header
    res_ok = c.options(
        "/health",
        headers={"Origin": "https://production.scrollsense.com", "Access-Control-Request-Method": "GET"},
    )
    assert res_ok.headers.get("access-control-allow-origin") == "https://production.scrollsense.com"

    # Disallowed origin does NOT receive allow-origin header
    res_bad = c.options(
        "/health",
        headers={"Origin": "https://unauthorized-domain.com", "Access-Control-Request-Method": "GET"},
    )
    assert res_bad.headers.get("access-control-allow-origin") is None


def test_feed_excludes_non_accepted_and_missing_reels(client: TestClient):
    """Test 2: /api/v1/feed returns ONLY accepted manifest items with valid assets on disk."""
    response = client.get("/api/v1/feed?limit=50")
    assert response.status_code == 200
    items = response.json()

    # Must contain reel_custom_asset and reel_ai_substance
    feed_ids = [item["reel_id"] for item in items]
    assert "reel_custom_asset" in feed_ids
    assert "reel_ai_substance" in feed_ids

    # Must NOT contain reel_missing_on_disk (asset file missing on disk)
    assert "reel_missing_on_disk" not in feed_ids

    # Must NOT contain reel_ai_hype_trap (gate rejected)
    assert "reel_ai_hype_trap" not in feed_ids

    # Must NOT contain raw inputs/candidates without accepted manifest entry
    assert "reel_java_meme" not in feed_ids
    assert "reel_swe_lifestyle" not in feed_ids


def test_no_fabricated_license_or_creator(client: TestClient):
    """Test 3: Reels without manifest entry return None for license/creator, never fabricated defaults."""
    # reel_java_meme is in inputs.json but not in our test manifest
    response = client.get("/api/v1/reels/reel_java_meme")
    assert response.status_code == 200
    data = response.json()
    assert data["reel_id"] == "reel_java_meme"
    assert data["license"] is None  # Must NOT be fabricated "CC-BY-4.0"
    assert data["creator"] is None  # Must NOT be fabricated "ScrollSense Creator"

    # reel_ai_substance is in our manifest with Apache-2.0
    res_manifest = client.get("/api/v1/reels/reel_ai_substance")
    assert res_manifest.status_code == 200
    data_manifest = res_manifest.json()
    assert data_manifest["license"] == "Apache-2.0"
    assert data_manifest["creator"] == "AIResearchGroup"


def test_manifest_filename_and_extension_respected(client: TestClient):
    """Test 4: Media URL respects manifest asset filename and extension (.webm)."""
    response = client.get("/api/v1/feed")
    assert response.status_code == 200
    items = response.json()
    custom_item = next(item for item in items if item["reel_id"] == "reel_custom_asset")
    assert custom_item["video_url"] == "/media/accepted/reel_custom_asset.webm"

    # Stream custom webm asset
    res_stream = client.get("/media/accepted/reel_custom_asset.webm")
    assert res_stream.status_code == 200
    assert res_stream.content == b"ACCEPTED_WEBM_VIDEO_DATA"


def test_media_security_and_containment(client: TestClient):
    """Test 5: Path traversal and unauthorized media directory access are strictly blocked."""
    # 1. Accepted MP4 stream works
    res_ok = client.get("/media/accepted/reel_ai_substance.mp4")
    assert res_ok.status_code == 200
    assert res_ok.content == b"ACCEPTED_MP4_VIDEO_DATA"

    # 2. Rejected media cannot be accessed
    res_rej = client.get("/media/accepted/reel_ai_hype_trap.mp4")
    assert res_rej.status_code == 404

    # 3. Path traversal attempts return 400 or 404
    res_trav = client.get("/media/accepted/..%2Frejected%2Freel_ai_hype_trap.mp4")
    assert res_trav.status_code in (400, 403, 404)


def test_canonical_swe_trap_recommendation_and_contract(client: TestClient):
    """Test 6: POST /api/v1/recommend returns full RecommendationResponse with official 8-field contract."""
    payload = {
        "student_id": "test_student_swe",
        "history": [
            "reel_java_meme",
            "reel_swe_lifestyle",
            "reel_interview_joke",
            "reel_laptop_comparison",
        ],
    }

    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    # 1. Official contract validation
    contract = data["official_contract"]
    assert "current_reel" in contract
    assert "reel_laptop_comparison" in contract["current_reel"]
    assert contract["interest_detected"] == "Software Engineer"
    assert "why" in contract
    assert "reel_java_meme" in contract["why"]
    assert "recommended_tech_reel" in contract
    assert "category" in contract
    assert "why_this_recommendation" in contract
    assert "difficulty" in contract
    assert "confidence" in contract

    # 2. Recommended reel feed item
    rec_reel = data["recommended_reel"]
    assert rec_reel["reel_id"] is not None

    # 3. Explainability payload
    explain = data["explainability"]
    assert "software_engineer" in explain["inferred_identities"]
    assert explain["inferred_identities"]["software_engineer"] > 0.80
    assert len(explain["contributing_evidence"]) >= 2
    assert len(explain["graph_traversal"]) > 0


def test_unknown_reel_id_handling(client: TestClient):
    """Test 7: Querying unknown reel ID returns 404."""
    res_detail = client.get("/api/v1/reels/unknown_reel_999")
    assert res_detail.status_code == 404

    res_rec = client.post(
        "/api/v1/recommend",
        json={"student_id": "s1", "history": ["unknown_reel_999"]},
    )
    assert res_rec.status_code == 404


def test_malformed_and_empty_requests(client: TestClient):
    """Test 8: Empty history and malformed payloads return appropriate client errors."""
    res_empty = client.post("/api/v1/recommend", json={"student_id": "s1", "history": []})
    assert res_empty.status_code in (400, 422)

    res_malformed = client.post("/api/v1/recommend", json={"student_id": "s1"})
    assert res_malformed.status_code == 422
