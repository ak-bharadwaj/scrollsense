"""FastAPI application factory for ScrollSense."""

import json
import os
from pathlib import Path
from typing import Sequence
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scrollsense.api.routes import create_router
from scrollsense.domain.reels import Reel
from scrollsense.engine import ScrollSenseEngine
from scrollsense.graph.loader import GraphLoader
from scrollsense.ingestion.manifest import AssetManifest, ValidationStatus
from scrollsense.retrieval.repository import CandidateRepository

def _resolve_data_dir() -> Path:
    """Resolve data directory robustly across local source runs, package installs, and cloud containers."""
    load_dotenv()
    env_data = os.getenv("SCROLLSENSE_DATA_DIR")
    if env_data and Path(env_data).exists():
        return Path(env_data).resolve()

    cwd_data = Path.cwd() / "data"
    if (cwd_data / "identity_skill_graph.json").exists():
        return cwd_data.resolve()

    src_data = Path(__file__).resolve().parent.parent.parent.parent / "data"
    if (src_data / "identity_skill_graph.json").exists():
        return src_data.resolve()

    for base in [Path(__file__).resolve(), Path.cwd().resolve()]:
        for parent in [base] + list(base.parents):
            candidate = parent / "data"
            if (candidate / "identity_skill_graph.json").exists():
                return candidate.resolve()

    return (Path.cwd() / "data").resolve()


DATA_DIR = _resolve_data_dir()

DEFAULT_DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def create_app(
    engine: ScrollSenseEngine | None = None,
    content_dir: Path | str | None = None,
    inputs_path: Path | str | None = None,
    candidates_path: Path | str | None = None,
    graph_path: Path | str | None = None,
    allowed_origins: Sequence[str] | None = None,
) -> FastAPI:
    """Factory creating and configuring the production ScrollSense FastAPI application."""
    app = FastAPI(
        title="ScrollSense API",
        description="Identity-Aware Latent Skill Graph Recommender API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure explicit CORS origins (no wildcard with credentials)
    if allowed_origins is not None:
        origins = list(allowed_origins)
    else:
        env_origins = os.getenv("SCROLLSENSE_CORS_ORIGINS")
        if env_origins:
            origins = [o.strip() for o in env_origins.split(",") if o.strip()]
        else:
            origins = list(DEFAULT_DEV_CORS_ORIGINS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
    )

    base_content_dir = Path(content_dir) if content_dir else DATA_DIR / "content"
    accepted_dir = base_content_dir / "accepted"
    manifest_path = base_content_dir / "manifest.json"
    manifest = AssetManifest.load_from_json(manifest_path) if manifest_path.exists() else None

    # Load corpus reels (combines inputs and candidate repository)
    in_path = Path(inputs_path) if inputs_path else DATA_DIR / "inputs.json"
    cand_path = Path(candidates_path) if candidates_path else DATA_DIR / "candidates.json"
    gr_path = Path(graph_path) if graph_path else DATA_DIR / "identity_skill_graph.json"

    corpus_reels: dict[str, Reel] = {}

    if in_path.exists():
        with open(in_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                r = Reel.model_validate(item)
                corpus_reels[r.reel_id] = r

    candidate_repo = CandidateRepository.load_from_json(cand_path) if cand_path.exists() else CandidateRepository()
    for r in candidate_repo.get_all():
        corpus_reels[r.reel_id] = r

    if manifest:
        for item in manifest.items.values():
            if item.validation_status == ValidationStatus.ACCEPTED:
                r = item.to_domain_reel()
                corpus_reels[r.reel_id] = r

    # Initialize Engine if not provided
    if engine is None:
        graph_store = GraphLoader.load_from_json(gr_path)
        engine = ScrollSenseEngine.create_default(
            graph_store=graph_store,
            candidate_repo=candidate_repo,
        )

    # Mount API router
    router = create_router(
        engine=engine,
        corpus_reels=corpus_reels,
        manifest=manifest,
        accepted_media_dir=accepted_dir,
    )
    app.include_router(router)

    # Mount static assets and root frontend page
    # Use importlib.resources so this works when installed as a package (e.g. Render)
    import importlib.resources as pkg_resources
    try:
        static_pkg = pkg_resources.files("scrollsense.api") / "static"
        static_dir = Path(str(static_pkg))
    except Exception:
        static_dir = Path(__file__).resolve().parent / "static"

    if static_dir.exists() and (static_dir / "index.html").exists():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def root_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

    return app


# Default app instance for ASGI servers (uvicorn scrollsense.api.app:app)
app = create_app()
