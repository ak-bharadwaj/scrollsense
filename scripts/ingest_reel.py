"""CLI utility for ingesting raw media assets with semantic signal extraction and gate validation."""

import argparse
import io
import json
from pathlib import Path
import sys

# Ensure UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrollsense.ingestion import LocalFileSourceAdapter, ReelIngestor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a licensed Reel asset with semantic extraction and automated gate checks.",
    )
    parser.add_argument(
        "--asset-path",
        type=str,
        required=True,
        help="Path to local media asset file (.mp4, .webm, etc.)",
    )
    parser.add_argument(
        "--metadata-json",
        type=str,
        default=None,
        help="Optional path to a JSON file containing asset metadata",
    )
    parser.add_argument("--title", type=str, default=None, help="Reel title")
    parser.add_argument("--transcript", type=str, default=None, help="Reel transcript text")
    parser.add_argument("--category", type=str, default=None, help="Topic category (required)")
    parser.add_argument("--license", type=str, default=None, help="Content license (required)")
    parser.add_argument("--creator", type=str, default=None, help="Creator attribution (required)")
    parser.add_argument(
        "--difficulty",
        type=str,
        default=None,
        choices=["beginner", "intermediate", "advanced"],
        help="Estimated technical depth level (required)",
    )
    parser.add_argument("--source-url", type=str, default=None, help="Canonical source URL")
    parser.add_argument(
        "--extraction-method",
        type=str,
        default="human_verified",
        help="Transcript extraction method (default: human_verified)",
    )
    parser.add_argument(
        "--content-dir",
        type=str,
        default=str(DATA_DIR / "content"),
        help="Base content storage directory (default: data/content)",
    )
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Allow re-ingesting an identical asset checksum",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    meta: dict = {}
    if args.metadata_json:
        meta_path = Path(args.metadata_json)
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

    title = args.title or meta.get("title")
    transcript = args.transcript or meta.get("transcript")
    category = args.category or meta.get("category")
    license_str = args.license or meta.get("license")
    creator = args.creator or meta.get("creator")
    difficulty = args.difficulty or meta.get("difficulty")
    source_url = args.source_url or meta.get("source_url")
    extraction_method = args.extraction_method or meta.get("extraction_method", "human_verified")

    # Enforce mandatory fields explicitly
    missing = []
    if not title:
        missing.append("--title")
    if not transcript:
        missing.append("--transcript")
    if not category:
        missing.append("--category")
    if not license_str:
        missing.append("--license")
    if not creator:
        missing.append("--creator")
    if not difficulty:
        missing.append("--difficulty")

    if missing:
        print(f"Error: The following mandatory fields must be explicitly supplied: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    adapter = LocalFileSourceAdapter()
    payload = adapter.load_asset(
        file_path=args.asset_path,
        title=title,
        transcript=transcript,
        category=category,
        license=license_str,
        creator=creator,
        difficulty=difficulty,
        source_url=source_url,
        extraction_method=extraction_method,
    )

    ingestor = ReelIngestor(content_dir=args.content_dir)

    print("================================================================================")
    print("                SCROLLSENSE REEL ASSET INGESTION PIPELINE                       ")
    print("================================================================================")
    print(f"Source File: {payload.file_path}")
    print(f"Title: {payload.title}")
    print(f"Creator: {payload.creator} | License: {payload.license}")
    print(f"Extraction Method: {payload.extraction_method}")

    result = ingestor.ingest_payload(payload=payload, allow_duplicate=args.allow_duplicate)

    print("\n--- AUTOMATED VALIDATION & GATE RESULTS ---")
    print(f"Reel ID: {result.item.reel_id}")
    print(f"Gate Status: {'PASSED' if result.gate_result.passed else 'FAILED'}")
    if not result.gate_result.passed:
        print(f"Rejection Reason: {result.gate_result.rejection_reason}")
    print(f"Quality Substance Score: {result.item.quality:.4f}")
    print(f"Hype Penalty Score: {result.item.hype:.4f}")
    print(f"Safety Gate: {'PASSED' if result.item.safety else 'VIOLATION'}")
    print(f"Validation Status: {result.item.validation_status.value.upper()}")
    print(f"Human QC Status: {result.item.human_qc_status.value.upper()} (Approval required via scripts/review_reel.py)")
    print(f"Stored Path: {result.stored_path}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
