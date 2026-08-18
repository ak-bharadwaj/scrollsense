"""CLI utility for human QC review, approval, and rejection of ingested Reel assets."""

import argparse
import io
from pathlib import Path
import sys

# Ensure UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrollsense.ingestion import GateRejectionError, ReelReviewer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Human QC review workflow for approving or rejecting ingested Reel assets.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", type=str, help="Reel ID to approve into accepted candidate corpus")
    group.add_argument("--reject", type=str, help="Reel ID to reject from candidate corpus")

    parser.add_argument("--reviewer", type=str, default="human_reviewer", help="Reviewer username or ID")
    parser.add_argument("--notes", type=str, default=None, help="Approval notes or feedback")
    parser.add_argument("--reason", type=str, default=None, help="Rejection rationale")
    parser.add_argument(
        "--content-dir",
        type=str,
        default=str(DATA_DIR / "content"),
        help="Base content storage directory (default: data/content)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reviewer = ReelReviewer(content_dir=args.content_dir)

    print("================================================================================")
    print("                SCROLLSENSE REEL HUMAN QC REVIEW WORKFLOW                       ")
    print("================================================================================")

    if args.approve:
        reel_id = args.approve
        print(f"Review Action: APPROVE Reel '{reel_id}'")
        print(f"Reviewer: {args.reviewer}")
        try:
            item = reviewer.approve_reel(
                reel_id=reel_id,
                reviewer=args.reviewer,
                notes=args.notes,
            )
            print("\n--- STATUS UPDATE: APPROVED ---")
            print(f"Reel ID: {item.reel_id}")
            print(f"Validation Status: {item.validation_status.value.upper()}")
            print(f"Human QC Status: {item.human_qc_status.value.upper()}")
            print(f"Storage Path: {item.asset_path}")
            print(f"Candidate Corpus Integration: ACTIVE (Candidate is eligible for recommendations)")
        except GateRejectionError as exc:
            print(f"\nError: {exc}", file=sys.stderr)
            sys.exit(1)
        except KeyError as exc:
            print(f"\nError: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.reject:
        reel_id = args.reject
        reason = args.reason or "Rejected during manual quality control check"
        print(f"Review Action: REJECT Reel '{reel_id}'")
        print(f"Reviewer: {args.reviewer} | Reason: {reason}")
        try:
            item = reviewer.reject_reel(
                reel_id=reel_id,
                reviewer=args.reviewer,
                reason=reason,
            )
            print("\n--- STATUS UPDATE: REJECTED ---")
            print(f"Reel ID: {item.reel_id}")
            print(f"Validation Status: {item.validation_status.value.upper()}")
            print(f"Human QC Status: {item.human_qc_status.value.upper()}")
            print(f"Storage Path: {item.asset_path}")
            print(f"Candidate Corpus Integration: EXCLUDED")
        except KeyError as exc:
            print(f"\nError: {exc}", file=sys.stderr)
            sys.exit(1)

    print("================================================================================\n")


if __name__ == "__main__":
    main()
