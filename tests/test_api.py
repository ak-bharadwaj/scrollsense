"""Integration tests for the ScrollSense FastAPI production API contracts."""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from scrollsense.api import app, create_app
from scrollsense.domain.enums import ConfidenceBucket, DepthLevel, TechCategory
from scrollsense.domain.reels import Reel
from scrollsense.engine import ScrollSenseEngine
from scrollsense.graph.loader import GraphLoader
from scrollsense.retrieval.repository import CandidateRepository

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_PATH = DATA_DIR / "identity_skill_graph.json"
INPUTS_PATH = DATA_DIR / "inputs.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Fixture providing TestClient with configured temp media directory."""
    content_dir = tmp_path / "content"
    accepted_dir = content_dir / "accepted"
    rejected_dir = content_dir / "rejected"
    accepted_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy accepted video file
    sample_accepted = accepted_dir / "reel_ai_substance.mp4"
    sample_accepted.write_bytes(b"ACCEPTED_VIDEO_DATA")

    # Create dummy rejected video file
    sample_rejected = rejected_dir / "reel_ai_hype_trap.mp4"
    sample_rejected.write_bytes(b"REJECTED_VIDEO_DATA")

    test_app = create_app(
        content_dir=content_dir,
        inputs_path=INPUTS_PATH,
        candidates_path=CANDIDATES_PATH,
        graph_path=GRAPH_PATH,
    )
    return TestClient(test_app)


def test_health_endpoint(client: TestClient):
    """Test 1: GET /health returns 200 and valid service status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "scrollsense-api"
    assert "version" in data


def test_feed_endpoint(client: TestClient):
    """Test 2: GET /api/v1/feed returns valid FeedItemResponse list and respects limits."""
    response = client.get("/api/v1/feed?limit=5")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 5

    for item in items:
        assert "reel_id" in item
        assert "title" in item
        assert "creator" in item
        assert "category" in item
        assert "difficulty" in item
        assert "video_url" in item
        assert "transcript" not in item  # Transcript must be excluded from feed item


def test_reel_detail_endpoint(client: TestClient):
    """Test 3: GET /api/v1/reels/{reel_id} returns full ReelDetailResponse with transcript and tags."""
    response = client.get("/api/v1/reels/reel_java_meme")
    assert response.status_code == 200
    data = response.json()
    assert data["reel_id"] == "reel_java_meme"
    assert "NullPointerException" in data["title"]
    assert "transcript" in data
    assert "concept_tags" in data
    assert "java" in data["concept_tags"]


def test_canonical_swe_trap_recommendation(client: TestClient):
    """Test 4: POST /api/v1/recommend returns full RecommendationResponse with official 8-field contract."""
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

    # 1. Check official contract (all 8 exact required fields)
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

    # 2. Check recommended reel feed item
    rec_reel = data["recommended_reel"]
    assert rec_reel["reel_id"] is not None
    assert rec_reel["video_url"].startswith("/media/accepted/")

    # 3. Check explainability payload
    explain = data["explainability"]
    assert "software_engineer" in explain["inferred_identities"]
    assert explain["inferred_identities"]["software_engineer"] > 0.80
    assert len(explain["contributing_evidence"]) >= 2
    assert len(explain["graph_traversal"]) > 0


def test_recommendation_with_interaction_events(client: TestClient):
    """Test 5: POST /api/v1/recommend accepts structured InteractionEvent payloads."""
    payload = {
        "student_id": "test_student_events",
        "history": [
            {
                "reel_id": "reel_java_meme",
                "event_type": "watch",
                "watched_seconds": 25.0,
                "completion_ratio": 1.0,
            },
            {
                "reel_id": "reel_swe_lifestyle",
                "event_type": "watch",
                "watched_seconds": 30.0,
                "completion_ratio": 1.0,
            },
        ],
    }

    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["official_contract"]["interest_detected"] == "Software Engineer"


def test_media_streaming_security_and_containment(client: TestClient):
    """Test 6: Media endpoint streams accepted assets and strictly rejects unauthorized paths."""
    # 1. Valid accepted file streams successfully
    res_ok = client.get("/media/accepted/reel_ai_substance.mp4")
    assert res_ok.status_code == 200
    assert res_ok.content == b"ACCEPTED_VIDEO_DATA"

    # 2. Non-existent file returns 404
    res_missing = client.get("/media/accepted/non_existent.mp4")
    assert res_missing.status_code == 404

    # 3. Rejected assets are NOT exposed through accepted media endpoint
    res_rej = client.get("/media/accepted/reel_ai_hype_trap.mp4")
    assert res_rej.status_code == 404

    # 4. Path traversal attempt returns 400 Bad Request
    res_trav = client.get("/media/accepted/..%2Frejected%2Freel_ai_hype_trap.mp4")
    assert res_trav.status_code in (400, 404)


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
    # Empty history
    res_empty = client.post("/api/v1/recommend", json={"student_id": "s1", "history": []})
    assert res_empty.status_code in (400, 422)

    # Missing history
    res_malformed = client.post("/api/v1/recommend", json={"student_id": "s1"})
    assert res_malformed.status_code == 422


def test_deterministic_api_responses(client: TestClient):
    """Test 9: Repeated recommendation requests produce identical contract outputs."""
    payload = {
        "student_id": "test_deterministic",
        "history": ["reel_java_meme", "reel_swe_lifestyle"],
    }

    res_1 = client.post("/api/v1/recommend", json=payload)
    res_2 = client.post("/api/v1/recommend", json=payload)

    assert res_1.status_code == 200
    assert res_2.status_code == 200
    assert res_1.json() == res_2.json()
