"""CLI runner executing the full ScrollSense evaluation benchmark with pretrained sentence embeddings."""

import argparse
import io
from pathlib import Path
import sys

# Ensure UTF-8 stdout on all operating systems
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add src to pythonpath
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrollsense.evaluation import (
    DEFAULT_SENTENCE_TRANSFORMER_MODEL,
    BenchmarkReportGenerator,
    EvaluationHarness,
    SentenceTransformerEmbeddingProvider,
    get_all_scenarios,
)
from scrollsense.graph.loader import GraphLoader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ScrollSense empirical evaluation benchmark comparing B0, B1, and B2.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=DEFAULT_SENTENCE_TRANSFORMER_MODEL,
        help=f"Pretrained sentence-transformers model identifier (default: {DEFAULT_SENTENCE_TRANSFORMER_MODEL})",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device to run sentence embedding model on (default: cpu)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=str(DATA_DIR / "benchmark_report.json"),
        help="Destination path for machine-readable JSON evaluation report",
    )
    parser.add_argument(
        "--graph-path",
        type=str,
        default=str(DATA_DIR / "identity_skill_graph.json"),
        help="Path to identity skill graph JSON file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("================================================================================")
    print("           SCROLLSENSE V4: EMPIRICAL RECOMMENDATION BENCHMARK                   ")
    print("================================================================================")
    print(f"Loading Graph from: {args.graph_path}")
    graph_store = GraphLoader.load_from_json(args.graph_path)

    print(f"Instantiating Pretrained Embedding Provider: {args.model_name} (device={args.device})")
    embedding_provider = SentenceTransformerEmbeddingProvider(
        model_name=args.model_name,
        device=args.device,
    )

    scenarios = get_all_scenarios()
    print(f"Loaded {len(scenarios)} Standard Evaluation Scenarios.")

    harness = EvaluationHarness(
        graph_store=graph_store,
        embedding_provider=embedding_provider,
        scenarios=scenarios,
    )

    print("Executing Baselines (B0: Literal Jaccard, B1: Sentence Embedding, B2: ScrollSense)...")
    summary = harness.run_benchmark()

    # Generate and print Markdown Table Report
    report_md = BenchmarkReportGenerator.generate_markdown_report(summary)
    print("\n" + report_md + "\n")

    # Save JSON Report
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_report = BenchmarkReportGenerator.generate_json_report(summary)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json_report)
    print(f"Saved machine-readable JSON report to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
