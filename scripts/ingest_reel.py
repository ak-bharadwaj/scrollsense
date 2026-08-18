"""CLI utility for ingesting, validating, and cataloging licensed Reel media assets."""

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

from scrollsense.domain.enums import DepthLevel
from scrollsense.ingestion import HumanQCStatus, ReelIngestor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest and validate a licensed Reel asset into the ScrollSense content repository.",
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
    parser.add_argument("--category", type=str, default="coding", help="Primary topic category")
    parser.add_argument(
        "--concepts",
        type=str,
        default="",
        help="Comma-separated list of technical concepts/tags",
    )
    parser.add_argument(
        "--license",
        type=str,
        default="CC-BY-4.0",
        help="Content license (default: CC-BY-4.0)",
    )
    parser.add_argument("--creator", type=str, default="Unknown Creator", help="Creator or channel attribution")
    parser.add_argument(
        "--difficulty",
        type=str,
        default="intermediate",
        choices=["beginner", "intermediate", "advanced"],
        help="Estimated technical depth level (default: intermediate)",
    )
    parser.add_argument(
        "--human-qc",
        type=str,
        default="pending",
        choices=["pending", "accepted", "rejected"],
        help="Human QC review status (default: pending)",
    )
    parser.add_argument("--source-url", type=str, default=None, help="Original source URL")
    parser.add_argument(
        "--content-dir",
        type=str,
        default=str(DATA_DIR / "content"),
        help="Base content storage directory (default: data/content)",
    )
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Allow overwriting an already ingested asset checksum",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load metadata JSON if provided
    meta: dict = {}
    if args.metadata_json:
        meta_path = Path(args.metadata_json)
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

    title = args.title or meta.get("title")
    transcript = args.transcript or meta.get("transcript")
    category = args.category or meta.get("category", "coding")
    concepts_raw = args.concepts or meta.get("concepts", [])
    if isinstance(concepts_raw, str):
        concepts = [c.strip() for c in concepts_raw.split(",") if c.strip()]
    else:
        concepts = list(concepts_raw)
    license_str = args.license or meta.get("license", "CC-BY-4.0")
    creator = args.creator or meta.get("creator", "Unknown Creator")
    difficulty_str = args.difficulty or meta.get("difficulty", "intermediate")
    difficulty = DepthLevel(difficulty_str.capitalize())
    qc_status_str = args.human_qc or meta.get("human_qc", "pending")
    human_qc = HumanQCStatus(qc_status_str.lower())
    source_url = args.source_url or meta.get("source_url")

    ingestor = ReelIngestor(content_dir=args.content_dir)

    print("================================================================================")
    print("                SCROLLSENSE REEL ASSET INGESTION & VALIDATION                   ")
    print("================================================================================")
    print(f"Asset File: {args.asset_path}")
    print(f"Title: {title}")
    print(f"Creator: {creator} | License: {license_str}")
    print(f"Human QC Status: {human_qc.value.upper()}")

    result = ingestor.ingest_asset(
        file_path=args.asset_path,
        title=title,
        transcript=transcript,
        category=category,
        concepts=concepts,
        license=license_str,
        creator=creator,
        difficulty=difficulty,
        source_url=source_url,
        human_qc_status=human_qc,
        allow_duplicate=args.allow_duplicate,
    )

    print("\n--- INGESTION RESULTS ---")
    print(f"Reel ID: {result.item.reel_id}")
    print(f"Gate Status: {'PASSED' if result.gate_result.passed else 'FAILED'}")
    if not result.gate_result.passed:
        print(f"Rejection Reason: {result.gate_result.rejection_reason}")
    print(f"Quality Substance Score: {result.item.quality:.4f}")
    print(f"Hype Penalty Score: {result.item.hype:.4f}")
    print(f"Safety Gate: {'PASSED' if result.item.safety else 'VIOLATION'}")
    print(f"Validation Status: {result.item.validation_status.value.upper()}")
    print(f"Accepted into Candidate Corpus: {result.accepted}")
    print(f"Stored Path: {result.stored_path}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
