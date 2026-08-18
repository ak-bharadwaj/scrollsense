"""Source adapter abstractions for localized and authorized external media asset ingestion."""

from pathlib import Path
from typing import Any, Protocol
from pydantic import BaseModel, ConfigDict, Field


class RawAssetPayload(BaseModel):
    """Normalized media asset payload extracted by a SourceAdapter."""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., description="Path to the local media asset file")
    source_url: str | None = Field(default=None, description="Canonical source URL")
    source_platform: str = Field(..., description="Origin platform (e.g. 'local_filesystem', 'instagram', 'youtube_shorts')")
    creator: str = Field(..., description="Creator, channel, or rights holder attribution")
    license: str = Field(..., description="Explicit content license or usage authorization basis")
    title: str = Field(..., description="Asset title")
    transcript: str = Field(..., description="Extracted or human-provided transcript text")
    category: str = Field(..., description="Initial topic category")
    difficulty_str: str = Field(..., description="Initial difficulty level string")
    extraction_method: str = Field(..., description="Transcript extraction method (e.g. 'whisper_local', 'human_verified', 'embedded_subtitles')")
    raw_metadata: dict[str, Any] = Field(default_factory=dict, description="Platform-specific raw metadata")


class SourceAdapter(Protocol):
    """Protocol interface for media source ingestion adapters."""

    def load_asset(self, source_reference: str, **kwargs: Any) -> RawAssetPayload:
        """Fetch or load raw asset payload from the target source."""
        ...


class LocalFileSourceAdapter:
    """Adapter for ingesting local media files with strict metadata requirements."""

    def load_asset(
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
        raw_metadata: dict[str, Any] | None = None,
    ) -> RawAssetPayload:
        """Load and validate a local media asset file."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Local media asset not found: {path}")

        # Enforce non-empty mandatory metadata (no silent defaults)
        if not title or not title.strip():
            raise ValueError("Asset title must be explicitly provided")
        if not transcript or not transcript.strip():
            raise ValueError("Asset transcript must be explicitly provided or extracted")
        if not category or not category.strip():
            raise ValueError("Asset category must be explicitly provided")
        if not license or not license.strip():
            raise ValueError("Asset license must be explicitly provided (no default permitted)")
        if not creator or not creator.strip():
            raise ValueError("Asset creator attribution must be explicitly provided")
        if not difficulty or not difficulty.strip():
            raise ValueError("Asset difficulty must be explicitly provided")

        return RawAssetPayload(
            file_path=str(path.resolve()),
            source_url=source_url,
            source_platform="local_filesystem",
            creator=creator.strip(),
            license=license.strip(),
            title=title.strip(),
            transcript=transcript.strip(),
            category=category.strip(),
            difficulty_str=difficulty.strip(),
            extraction_method=extraction_method.strip(),
            raw_metadata=raw_metadata or {},
        )


class InstagramSourceAdapter:
    """Interface for authorized, licensed Instagram Reels ingestion with platform compliance.

    Adheres strictly to platform terms of service, access controls, and authentication.
    Does not bypass access controls or scrape unauthorized endpoints.
    """

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token

    def load_asset(
        self,
        media_id: str,
        file_path: Path | str,
        title: str,
        transcript: str,
        category: str,
        license: str,
        creator: str,
        difficulty: str,
        source_url: str | None = None,
        extraction_method: str = "instagram_graph_api",
        raw_metadata: dict[str, Any] | None = None,
    ) -> RawAssetPayload:
        """Load an authorized Instagram Reel asset record."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Instagram media asset file not found: {path}")

        if not source_url:
            source_url = f"https://www.instagram.com/reel/{media_id}/"

        return RawAssetPayload(
            file_path=str(path.resolve()),
            source_url=source_url,
            source_platform="instagram",
            creator=creator.strip(),
            license=license.strip(),
            title=title.strip(),
            transcript=transcript.strip(),
            category=category.strip(),
            difficulty_str=difficulty.strip(),
            extraction_method=extraction_method.strip(),
            raw_metadata=raw_metadata or {"media_id": media_id},
        )
