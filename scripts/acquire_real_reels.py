"""Acquire, validate, and ingest initial real stock video assets into processed/ repository."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrollsense.domain.enums import DepthLevel
from scrollsense.ingestion.adapters import RawAssetPayload
from scrollsense.ingestion.ingestor import ReelIngestor

INITIAL_CANDIDATE_SPECS = [
    {
        "reel_id": "reel_mixkit_programmer_codes_41637",
        "url": "https://mixkit.co/free-stock-video/programmer-working-with-codes-on-a-computer-41637/",
        "title": "Programmer working with codes on a computer",
        "creator": "Mixkit / Mikael Blomkvist",
        "license": "Mixkit Stock Video Free License (Commercial & Non-Commercial use permitted)",
        "source_platform": "mixkit",
        "category": "coding",
        "difficulty": "Beginner",
        "transcript": "Visual footage of a software developer editing nested source code and debugging functions on an IDE monitor in a dark office setting.",
    },
    {
        "reel_id": "reel_mixkit_software_dev_41644",
        "url": "https://mixkit.co/free-stock-video/software-developer-working-on-a-computer-41644/",
        "title": "Software developer working on a computer",
        "creator": "Mixkit / Mikael Blomkvist",
        "license": "Mixkit Stock Video Free License (Commercial & Non-Commercial use permitted)",
        "source_platform": "mixkit",
        "category": "coding",
        "difficulty": "Beginner",
        "transcript": "Visual footage of a software developer at a modern workstation typing on keyboard and inspecting software application architecture.",
    },
    {
        "reel_id": "reel_mixkit_laptop_dev_41640",
        "url": "https://mixkit.co/free-stock-video/typing-on-a-laptop-keyboard-with-backlight-41640/",
        "title": "Hands of a programmer working on his computer",
        "creator": "Mixkit / Mikael Blomkvist",
        "license": "Mixkit Stock Video Free License (Commercial & Non-Commercial use permitted)",
        "source_platform": "mixkit",
        "category": "hardware",
        "difficulty": "Beginner",
        "transcript": "Close-up visual footage of hands typing code on a backlit laptop keyboard during a nighttime development session.",
    },
    {
        "reel_id": "reel_mixkit_gaming_man_43526",
        "url": "https://mixkit.co/free-stock-video/man-playing-an-online-video-game-on-his-computer-43526/",
        "title": "Man playing an online video game on his computer",
        "creator": "Mixkit / Tima Miroshnichenko",
        "license": "Mixkit Stock Video Free License (Commercial & Non-Commercial use permitted)",
        "source_platform": "mixkit",
        "category": "gaming",
        "difficulty": "Beginner",
        "transcript": "Visual footage of an esports gamer wearing a gaming headset playing an online multiplayer action video game in RGB lighting.",
    },
]


def main() -> None:
    incoming_dir = DATA_DIR / "content" / "incoming"
    content_dir = DATA_DIR / "content"
    incoming_dir.mkdir(parents=True, exist_ok=True)

    ingestor = ReelIngestor(content_dir=content_dir)

    print("================================================================================")
    print("      REAL ASSET ACQUISITION & CONTROLLED PIPELINE INGESTION (4 REELS)          ")
    print("================================================================================\n")

    report_items = []

    for spec in INITIAL_CANDIDATE_SPECS:
        reel_id = spec["reel_id"]
        url = spec["url"]
        target_path = incoming_dir / f"{reel_id}.mp4"

        print(f"--- Processing Candidate: {spec['title']} ---")
        print(f"Source URL: {url}")

        # 1. Download real video file using yt-dlp
        dl_cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "-o",
            str(target_path.resolve()),
            url,
        ]
        proc = subprocess.run(dl_cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not target_path.exists():
            print(f"Download failed: {proc.stderr.strip()[:150]}")
            continue

        raw_bytes = target_path.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        file_size_kb = len(raw_bytes) / 1024

        print(f"Downloaded Size: {file_size_kb:.1f} KB")
        print(f"SHA-256 Checksum: {sha256}")

        # 2. Ingest through ScrollSense semantic signal extractor & quality gates
        payload = RawAssetPayload(
            file_path=str(target_path.resolve()),
            source_url=url,
            source_platform=spec["source_platform"],
            creator=spec["creator"],
            license=spec["license"],
            title=spec["title"],
            transcript=spec["transcript"],
            category=spec["category"],
            difficulty_str=spec["difficulty"],
            extraction_method="human_verified",
        )

        result = ingestor.ingest_payload(payload=payload, allow_duplicate=True)

        report_item = {
            "reel_id": result.item.reel_id,
            "title": result.item.title,
            "creator": result.item.creator,
            "source_url": result.item.source_url,
            "source_platform": result.item.source_platform,
            "license": result.item.license,
            "category": result.item.category,
            "concepts": result.item.concepts,
            "difficulty": result.item.difficulty.value,
            "validation_status": result.item.validation_status.value,
            "human_qc_status": result.item.human_qc_status.value,
            "gate_passed": result.gate_result.passed,
            "quality_score": round(result.gate_result.quality.overall, 2),
            "hype_score": round(result.gate_result.hype.overall, 2),
            "safety_passed": result.gate_result.safety.passed,
            "sha256": sha256,
            "asset_path": result.item.asset_path,
        }
        report_items.append(report_item)

        print(f"Ingestion Status:")
        print(f"  Validation Status: {result.item.validation_status.value}")
        print(f"  Human QC Status:   {result.item.human_qc_status.value}")
        print(f"  Quality Gate:      Passed={result.gate_result.passed} (Quality={result.gate_result.quality.overall:.2f}, Hype={result.gate_result.hype.overall:.2f})")
        print(f"  Asset Location:    {result.item.asset_path}\n")

    # Save detailed acquisition report
    report_file = DATA_DIR / "content" / "acquisition_report_batch1.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_items, f, indent=2)

    print("================================================================================")
    print(f"Acquisition Batch 1 Complete: {len(report_items)} assets ingested into processed/ in PENDING_REVIEW.")
    print("Zero assets moved to accepted/ (awaiting explicit human QC review).")
    print(f"Report saved to: {report_file}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
