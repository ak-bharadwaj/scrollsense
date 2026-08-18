"""CLI script executing and displaying the official ScrollSense required output contract."""

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

from scrollsense.domain.reels import Reel
from scrollsense.engine import ScrollSenseEngine
from scrollsense.graph.loader import GraphLoader
from scrollsense.retrieval.repository import CandidateRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ScrollSense end-to-end and display the official required output contract.",
    )
    parser.add_argument(
        "--inputs-path",
        type=str,
        default=str(DATA_DIR / "inputs.json"),
        help="Path to inputs.json containing interaction history",
    )
    parser.add_argument(
        "--graph-path",
        type=str,
        default=str(DATA_DIR / "identity_skill_graph.json"),
        help="Path to identity_skill_graph.json",
    )
    parser.add_argument(
        "--candidates-path",
        type=str,
        default=str(DATA_DIR / "candidates.json"),
        help="Path to candidates.json",
    )
    parser.add_argument(
        "--student-id",
        type=str,
        default="session_user_001",
        help="Target student / session identifier",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load resources
    graph_store = GraphLoader.load_from_json(args.graph_path)
    candidate_repo = CandidateRepository.load_from_json(args.candidates_path)
    with open(args.inputs_path, "r", encoding="utf-8") as f:
        input_reels = [Reel.model_validate(item) for item in json.load(f)]

    engine = ScrollSenseEngine.create_default(
        graph_store=graph_store,
        candidate_repo=candidate_repo,
    )

    # Execute full engine recommendation
    engine_result = engine.recommend_full(
        student_id=args.student_id,
        input_reels=input_reels,
    )

    output = engine_result.outputs[0]

    print("================================================================================")
    print("               SCROLLSENSE: OFFICIAL REQUIRED OUTPUT CONTRACT                   ")
    print("================================================================================\n")

    print("--------------------------------------------------------------------------------")
    print("SECTION A: CUMULATIVE SESSION EVOLUTION")
    print("--------------------------------------------------------------------------------")
    signals = []
    for step_idx, reel in enumerate(input_reels, 1):
        sig = engine.extractor.extract(reel)
        signals.append(sig)
        state = engine.inferencer.infer_interest_state(
            student_id=args.student_id,
            reel_signals=signals,
        )
        if state.professional_identity:
            top_ident, top_weight = list(state.professional_identity.items())[0]
            ident_label = top_ident.replace("_", " ").title()
        else:
            ident_label = "General Technology"
            top_weight = 0.0

        print(f"Step {step_idx}:")
        print(f"  - Current Reel:    {reel.reel_id} — {reel.title}")
        print(f"  - Detected Interest: {ident_label}")
        print(f"  - Interest Weight:   {top_weight:.2f}")
        print()

    print("--------------------------------------------------------------------------------")
    print("SECTION B: OFFICIAL REQUIRED OUTPUT FOR FINAL RECOMMENDATION")
    print("--------------------------------------------------------------------------------")
    print(f"CURRENT REEL:              {output.current_reel}")
    print(f"INTEREST DETECTED:         {output.interest_detected}")
    print(f"WHY:                       {output.why}")
    print(f"RECOMMENDED TECH REEL:     {output.recommended_tech_reel}")
    print(f"CATEGORY:                  {output.category.value}")
    print(f"WHY THIS RECOMMENDATION:   {output.why_this_recommendation}")
    print(f"DIFFICULTY:                {output.difficulty.value}")
    print(f"CONFIDENCE:                {output.confidence.value}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
