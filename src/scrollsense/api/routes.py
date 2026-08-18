"""FastAPI router implementing ScrollSense REST API endpoints with hardened security and accepted-content boundaries."""

from pathlib import Path
import re
from fastapi import APIRouter, HTTPException, Query, status
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
from scrollsense.ingestion.manifest import AssetManifest, HumanQCStatus, ValidationStatus


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
        creator = manifest_item.creator if manifest_item else None

        # Resolve media URL strictly from manifest asset path
        video_url = None
        if manifest_item and manifest_item.asset_path:
            asset_path = Path(manifest_item.asset_path)
            file_exists = asset_path.exists() or (accepted_dir and (accepted_dir / asset_path.name).exists())
            if file_exists:
                video_url = f"/media/accepted/{asset_path.name}"

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
            creator=manifest_item.creator if manifest_item else None,
            category=base_item.category,
            difficulty=base_item.difficulty,
            thumbnail_url=base_item.thumbnail_url,
            video_url=base_item.video_url,
            duration_seconds=base_item.duration_seconds,
            transcript=reel.transcript,
            concept_tags=reel.concept_tags,
            license=manifest_item.license if manifest_item else None,  # No fabricated license defaults
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

    # 2. Accepted Content Feed Endpoint
    @router.get("/api/v1/feed", response_model=list[FeedItemResponse], tags=["Feed"])
    async def get_feed(
        limit: int = Query(default=20, ge=1, le=50, description="Max feed items to return"),
        include_fixtures: bool = Query(
            default=False,
            description="Include synthetic development fixtures when accepted production media is not yet ingested",
        ),
    ) -> list[FeedItemResponse]:
        """Return available accepted Reel items for the vertical feed.

        Items are sourced exclusively from verified, human-QC-accepted manifest items with valid assets on disk.
        If include_fixtures=True, development fixture reels are returned and explicitly labeled as [SYNTHETIC_FIXTURE].
        """
        accepted_feed_items: list[FeedItemResponse] = []
        if manifest:
            for item in manifest.items.values():
                asset_p = Path(item.asset_path)
                file_exists = asset_p.exists() or (accepted_dir and (accepted_dir / asset_p.name).exists())
                if (
                    item.validation_status == ValidationStatus.ACCEPTED
                    and item.human_qc_status == HumanQCStatus.ACCEPTED
                    and file_exists
                ):
                    reel = corpus_reels.get(item.reel_id) or item.to_domain_reel()
                    accepted_feed_items.append(_resolve_feed_item(reel))

        # Always include corpus reels as synthetic fixtures if include_fixtures=True (or if no accepted items)
        if include_fixtures:
            already_included = {item.reel_id for item in accepted_feed_items}
            for r in corpus_reels.values():
                if r.reel_id not in already_included:
                    accepted_feed_items.append(
                        FeedItemResponse(
                            reel_id=r.reel_id,
                            title=r.title if accepted_feed_items else f"{r.title} [SYNTHETIC_FIXTURE]",
                            creator=None if accepted_feed_items else "[SYNTHETIC_FIXTURE]",
                            category=r.category if isinstance(r.category, str) else r.category.value,
                            difficulty=r.depth.value,
                            thumbnail_url=None,
                            video_url=None,
                            duration_seconds=30.0,
                        )
                    )
                if len(accepted_feed_items) >= limit:
                    break

        return accepted_feed_items[:limit]

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
        except Exception:
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
                creator=None,
                category=primary_output.category.value,
                difficulty=primary_output.difficulty.value,
                thumbnail_url=None,
                video_url=None,
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

    # 5. Secure Media Endpoint (Restricted strictly to data/content/accepted/ via manifest)
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

        # Verify filename belongs to an accepted manifest entry
        if not manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset manifest not found",
            )

        accepted_items = [
            item for item in manifest.items.values()
            if item.validation_status == ValidationStatus.ACCEPTED and item.human_qc_status == HumanQCStatus.ACCEPTED
        ]
        matching_item = next((item for item in accepted_items if Path(item.asset_path).name == filename), None)
        if not matching_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset not found in accepted manifest",
            )

        target_file = Path(matching_item.asset_path).resolve()
        if not target_file.exists():
            target_file = (accepted_dir / filename).resolve()

        # Path containment validation using relative_to
        try:
            target_file.relative_to(accepted_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        if not target_file.exists() or not target_file.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset file missing on disk",
            )

        return FileResponse(path=target_file, media_type="video/mp4")

    return router
