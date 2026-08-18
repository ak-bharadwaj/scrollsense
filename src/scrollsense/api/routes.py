"""FastAPI router implementing ScrollSense REST API endpoints."""

from pathlib import Path
import re
from typing import Sequence
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from scrollsense.api.schemas import (
    ExplainabilityPayload,
    FeedItemResponse,
    InteractionEvent,
    RecommendRequest,
    RecommendationResponse,
    ReelDetailResponse,
)
from scrollsense.domain.reels import Reel
from scrollsense.engine import NoEligibleCandidatesError, ScrollSenseEngine
from scrollsense.ingestion.manifest import AssetManifest


FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def create_router(
    engine: ScrollSenseEngine,
    corpus_reels: dict[str, Reel],
    manifest: AssetManifest | None = None,
    accepted_media_dir: Path | None = None,
) -> APIRouter:
    """Create configured API router with injected engine and content dependencies."""
    router = APIRouter()
    accepted_dir = Path(accepted_media_dir).resolve() if accepted_media_dir else None

    def _resolve_feed_item(reel: Reel) -> FeedItemResponse:
        """Construct FeedItemResponse for a domain Reel entity."""
        manifest_item = manifest.get_by_reel_id(reel.reel_id) if manifest else None
        creator = manifest_item.creator if manifest_item else "ScrollSense Creator"

        # Construct safe media endpoint URL
        video_url = f"/media/accepted/{reel.reel_id}.mp4"

        return FeedItemResponse(
            reel_id=reel.reel_id,
            title=reel.title,
            creator=creator,
            category=reel.category if isinstance(reel.category, str) else reel.category.value,
            difficulty=reel.depth.value,
            thumbnail_url=None,
            video_url=video_url,
            duration_seconds=30.0,
        )

    def _resolve_reel_detail(reel: Reel) -> ReelDetailResponse:
        """Construct ReelDetailResponse for a domain Reel entity."""
        base_item = _resolve_feed_item(reel)
        manifest_item = manifest.get_by_reel_id(reel.reel_id) if manifest else None

        return ReelDetailResponse(
            reel_id=base_item.reel_id,
            title=base_item.title,
            creator=base_item.creator,
            category=base_item.category,
            difficulty=base_item.difficulty,
            thumbnail_url=base_item.thumbnail_url,
            video_url=base_item.video_url,
            duration_seconds=base_item.duration_seconds,
            transcript=reel.transcript,
            concept_tags=reel.concept_tags,
            license=manifest_item.license if manifest_item else "CC-BY-4.0",
            source_url=manifest_item.source_url if manifest_item else None,
        )

    # 1. Health Endpoint
    @router.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        """Health check endpoint for Cloud Run and load balancers."""
        return {
            "status": "ok",
            "service": "scrollsense-api",
            "version": "1.0.0",
        }

    # 2. General Feed Endpoint
    @router.get("/api/v1/feed", response_model=list[FeedItemResponse], tags=["Feed"])
    async def get_feed(
        limit: int = Query(default=20, ge=1, le=50, description="Max feed items to return"),
    ) -> list[FeedItemResponse]:
        """Return available accepted Reel items for the simulated vertical feed.

        Note: Items returned are general available feed content, not personalized recommendations.
        """
        all_reels = list(corpus_reels.values())[:limit]
        return [_resolve_feed_item(r) for r in all_reels]

    # 3. Individual Reel Detail Endpoint
    @router.get("/api/v1/reels/{reel_id}", response_model=ReelDetailResponse, tags=["Reels"])
    async def get_reel_detail(reel_id: str) -> ReelDetailResponse:
        """Return metadata, transcript, and technical concepts for a single reel."""
        if not FILENAME_REGEX.match(reel_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reel_id format",
            )
        reel = corpus_reels.get(reel_id)
        if not reel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reel '{reel_id}' not found in corpus",
            )
        return _resolve_reel_detail(reel)

    # 4. Recommendation Endpoint
    @router.post("/api/v1/recommend", response_model=RecommendationResponse, tags=["Recommendations"])
    async def get_recommendation(request: RecommendRequest) -> RecommendationResponse:
        """Generate identity-aware recommendation and explainability payload from interaction history."""
        if not request.history:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interaction history cannot be empty",
            )

        # Resolve reel sequence from request history
        resolved_reels: list[Reel] = []
        for item in request.history:
            r_id = item.reel_id if isinstance(item, InteractionEvent) else item
            if not isinstance(r_id, str) or not FILENAME_REGEX.match(r_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid reel identifier format: '{r_id}'",
                )
            reel = corpus_reels.get(r_id)
            if not reel:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reel ID '{r_id}' not found in corpus",
                )
            resolved_reels.append(reel)

        # Run ScrollSense recommendation engine
        try:
            engine_result = engine.recommend_full(
                student_id=request.student_id,
                input_reels=resolved_reels,
            )
        except NoEligibleCandidatesError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal recommendation computation error",
            )

        if not engine_result.outputs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No eligible candidates survived quality gates and ranking",
            )

        primary_output = engine_result.outputs[0]
        top_rec = engine_result.internal_recommendations[0]

        # Resolve recommendation FeedItem
        recommended_reel = corpus_reels.get(top_rec.reel_id)
        if not recommended_reel:
            recommended_feed_item = FeedItemResponse(
                reel_id=top_rec.reel_id,
                title=top_rec.title,
                creator="ScrollSense Recommended",
                category=primary_output.category.value,
                difficulty=primary_output.difficulty.value,
                thumbnail_url=None,
                video_url=f"/media/accepted/{top_rec.reel_id}.mp4",
                duration_seconds=45.0,
            )
        else:
            recommended_feed_item = _resolve_feed_item(recommended_reel)

        # Construct Explainability Payload
        state = engine_result.interest_state
        explainability = ExplainabilityPayload(
            inferred_identities=state.professional_identity,
            domains_breakdown=state.domains,
            contributing_evidence=[
                f"{r.title} ({r.reel_id})"
                for r in resolved_reels
                if r.reel_id in state.evidence
            ],
            graph_traversal=top_rec.traversal_path,
            raw_traces={
                "final_score": top_rec.final_score,
                "confidence": top_rec.confidence.value,
                "retrieval_source": top_rec.retrieval_source.value,
            },
        )

        return RecommendationResponse(
            official_contract=primary_output,
            recommended_reel=recommended_feed_item,
            explainability=explainability,
        )

    # 5. Secure Media Endpoint (Restricted strictly to data/content/accepted/)
    @router.get("/media/accepted/{filename}", tags=["Media"])
    async def stream_media(filename: str) -> FileResponse:
        """Stream validated media assets strictly from the accepted content directory."""
        if not FILENAME_REGEX.match(filename) or ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid media filename",
            )

        if not accepted_dir or not accepted_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media repository not configured",
            )

        target_file = (accepted_dir / filename).resolve()

        # Strict containment check: target must be inside accepted_dir
        if not str(target_file).startswith(str(accepted_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        if not target_file.exists() or not target_file.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset not found",
            )

        return FileResponse(path=target_file, media_type="video/mp4")

    return router
