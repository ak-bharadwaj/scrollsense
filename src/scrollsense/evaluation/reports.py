"""Benchmark report generator producing formatted comparison tables and analysis."""

from scrollsense.evaluation.runner import BenchmarkSummary


class BenchmarkReportGenerator:
    """Generates structured Markdown and JSON reports from benchmark evaluation results."""

    @staticmethod
    def generate_markdown_report(summary: BenchmarkSummary) -> str:
        """Generate a complete GitHub-flavored Markdown evaluation report."""
        lines = [
            "# ScrollSense Empirical Evaluation Benchmark Report",
            "",
            f"**Evaluated At:** {summary.evaluated_at.isoformat()}",
            "",
            "## 1. Aggregate Baseline Comparison Table",
            "",
            "| Metric | B0: Literal Jaccard | B1: Semantic Similarity | B2: ScrollSense (Ours) |",
            "| :--- | :---: | :---: | :---: |",
        ]

        metric_names = [
            ("Trap Avoidance Rate", "trap_avoidance_rate"),
            ("Technology Relevance", "technology_relevance"),
            ("Identity Consistency", "identity_consistency"),
            ("Hype Rejection Rate", "hype_rejection_rate"),
            ("Safety Rejection Rate", "safety_rejection_rate"),
            ("Provenance Completeness", "provenance_completeness"),
            ("Deterministic Replay", "deterministic_replay"),
            ("Top-1 Expert Alignment", "top1_expert_alignment"),
        ]

        for label, key in metric_names:
            b0_val = f"{summary.aggregate_metrics['B0'][key] * 100:.1f}%"
            b1_val = f"{summary.aggregate_metrics['B1'][key] * 100:.1f}%"
            b2_val = f"**{summary.aggregate_metrics['B2'][key] * 100:.1f}%**"
            lines.append(f"| {label} | {b0_val} | {b1_val} | {b2_val} |")

        lines.extend([
            "",
            "## 2. Per-Scenario Recommendation Breakdown",
            "",
        ])

        for record in summary.scenario_records:
            lines.extend([
                f"### {record.scenario_name}",
                f"- **Inferred Latent Identity:** `{record.inferred_identity}`",
                f"- **Input Reels Count:** {len(record.input_reel_ids)}",
                "",
                "| Baseline | Recommended Reel | Category | Top-1 Expert Alignment |",
                "| :--- | :--- | :---: | :---: |",
            ])

            for b_id in ("B0", "B1", "B2"):
                rec = record.baseline_recommendations[b_id]
                met = record.metrics[b_id]
                status = "[PASS]" if met.top1_expert_alignment == 1.0 else "[TRAP/MISMATCH]"
                lines.append(
                    f"| **{rec.baseline_name}** (`{b_id}`) | *{rec.recommended_title}* | `{rec.category.value}` | {status} |"
                )

            lines.append("")

        return "\n".join(lines)
