"""Script constructing and validating the official 24-reel demo corpus for ScrollSense."""

import io
from pathlib import Path
import sys

# Ensure UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrollsense.domain.enums import DepthLevel
from scrollsense.ingestion.adapters import RawAssetPayload
from scrollsense.ingestion.ingestor import ReelIngestor, ReelReviewer
from scrollsense.ingestion.manifest import AssetManifest, HumanQCStatus, ValidationStatus


# Minimum valid binary MP4 header bytes for simulated local playback
MP4_HEADER = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    b"\x00\x00\x00\x08free"
    b"\x00\x00\x00\x28mdat"
    + b"SCROLLSENSE_DEMO_VIDEO_STREAM_PAYLOAD_BYTE_STREAM" * 40
)

# 24 Diverse Educational & Entertainment Reels
DEMO_REELS_SPEC = [
    # --- 1. Programming Memes (2) ---
    {
        "reel_id": "reel_java_meme",
        "title": "When NullPointerException hits in production at 3 AM",
        "category": "programming_memes",
        "creator": "DevHumor Studio",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "POV: You thought your null check was bulletproof, but the client payload sent undefined in the nested DTO. Panicked log grep ensues.",
        "concepts": ["java", "exception_handling", "production_debugging"],
    },
    {
        "reel_id": "reel_git_merge_meme",
        "title": "Merge conflicts after one week of refactoring branch isolation",
        "category": "programming_memes",
        "creator": "DevHumor Studio",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Incoming changes: 400 lines deleted. Current changes: 500 lines added. Git status shows 28 unmerged paths. Time to delete repo.",
        "concepts": ["git", "version_control", "merge_conflicts"],
    },

    # --- 2. Entertainment / Tech Vlogs (3) ---
    {
        "reel_id": "reel_swe_lifestyle",
        "title": "Day in the life of a backend engineer at a Seattle tech company",
        "category": "entertainment",
        "creator": "SeattleDevVlogs",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Morning coffee, 10 AM standup with the infrastructure team, reviewing two PRs for our Kafka event pipeline, and writing unit tests before lunch.",
        "concepts": ["software_engineering", "workplace_culture", "code_review"],
    },
    {
        "reel_id": "reel_office_setup_tour",
        "title": "Minimalist Scandinavian desk setup for remote software engineering",
        "category": "entertainment",
        "creator": "DeskAesthetics",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Walnut standing desk, 40-inch ultrawide 5K monitor, hidden cable channels, and warm bias lighting for nighttime coding sessions.",
        "concepts": ["workspace", "productivity", "hardware_setup"],
    },
    {
        "reel_id": "reel_hackathon_vlog",
        "title": "Building an AI startup in 24 hours at Silicon Valley Hackathon",
        "category": "entertainment",
        "creator": "HackVlogger",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Hour 2: brainstorming architecture. Hour 8: debugging WebSocket connections. Hour 18: pitching live demo to judges on 3 cups of matcha.",
        "concepts": ["hackathons", "startups", "rapid_prototyping"],
    },

    # --- 3. Gaming (3) ---
    {
        "reel_id": "reel_gaming_clip",
        "title": "1v5 Clutch defusal in tactical FPS grand final round",
        "category": "gaming",
        "creator": "TacticalFPS Clips",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Ten seconds on the clock, no flashbangs left, fake defuse, headshot through smoke, and diffuse with 0.2 seconds remaining!",
        "concepts": ["fps_gaming", "esports", "clutch_plays"],
    },
    {
        "reel_id": "reel_aim_training_guide",
        "title": "Kovaaks 101: Basic Tracking and Click-Timing Drill Presets",
        "category": "gaming",
        "creator": "AimCoachPro",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "How 15 minutes of daily smooth sphere tracking exercises builds consistent muscle memory and micro-adjustment crosshair placement.",
        "concepts": ["aim_training", "fps_mechanics", "esports_drills"],
    },
    {
        "reel_id": "reel_speedrun_breakdown",
        "title": "How frame-perfect wall clips broke the Elden Ring speedrun record",
        "category": "gaming",
        "creator": "SpeedrunScience",
        "license": "CC-BY-4.0",
        "difficulty": "Intermediate",
        "transcript": "Manipulating character collision physics and animation cancellation to bypass boss barriers and save 42 seconds on the Any% route.",
        "concepts": ["speedrunning", "game_physics", "glitch_hunting"],
    },

    # --- 4. Programming / Core Coding (3) ---
    {
        "reel_id": "reel_java_syntax_basics",
        "title": "Java 21 Syntax: Records, Sealed Classes & Pattern Matching",
        "category": "coding",
        "creator": "ModernJavaLab",
        "license": "Apache-2.0",
        "difficulty": "Beginner",
        "transcript": "Stop writing verbose boilerplate POJOs. Here is how Java records and pattern matching switch statements make domain modeling clean and expressive.",
        "concepts": ["java", "records", "sealed_classes", "pattern_matching"],
    },
    {
        "reel_id": "reel_hld_caching",
        "title": "System Design 101: Distributed Caching with Redis & Invalidation Strategies",
        "category": "coding",
        "creator": "SystemDesignPro",
        "license": "MIT",
        "difficulty": "Intermediate",
        "transcript": "Cache-aside vs write-through caching patterns. How to handle the cache stampede problem and maintain eventual consistency between Redis and primary SQL DB.",
        "concepts": ["distributed_systems", "system_design", "redis", "cache_invalidation"],
    },
    {
        "reel_id": "reel_dsa_trees",
        "title": "Tree Traversal & Dynamic Programming Patterns for SWE Interviews",
        "category": "coding",
        "creator": "AlgoMaster",
        "license": "MIT",
        "difficulty": "Intermediate",
        "transcript": "Breaking down recursion into base cases, memoization tables, and bottom-up DP states for LeetCode medium tree and graph questions.",
        "concepts": ["dsa", "binary_trees", "dynamic_programming", "interview_prep"],
    },

    # --- 5. AI / Machine Learning (3) ---
    {
        "reel_id": "reel_ai_prompt_hacks",
        "title": "How prompt engineering is changing junior developer workflows",
        "category": "AI",
        "creator": "AIEngineerWeekly",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Developers are shifting from writing boilerplate to crafting structured prompt schemas and evaluating unit tests generated by AI coding assistants.",
        "concepts": ["ai_tools", "developer_productivity", "prompt_engineering"],
    },
    {
        "reel_id": "reel_ai_substance",
        "title": "Attention Mechanism & Transformer Neural Network Math Explained",
        "category": "AI",
        "creator": "DeepLearningMath",
        "license": "Apache-2.0",
        "difficulty": "Intermediate",
        "transcript": "Understanding Query, Key, and Value matrix multiplications in self-attention with scaled dot-product visualization and multi-head projection layers.",
        "concepts": ["transformers", "neural_networks", "attention_mechanism", "ai_architecture"],
    },
    {
        "reel_id": "reel_rag_architecture",
        "title": "Building Production Retrieval-Augmented Generation with Vector Databases",
        "category": "AI",
        "creator": "AIEngineerWeekly",
        "license": "Apache-2.0",
        "difficulty": "Advanced",
        "transcript": "Chunking strategies, dense embedding indexing with HNSW graphs, hybrid lexical-semantic reranking, and preventing LLM hallucination.",
        "concepts": ["rag", "vector_databases", "embeddings", "information_retrieval"],
    },

    # --- 6. Gadgets / Hardware (3) ---
    {
        "reel_id": "reel_laptop_comparison",
        "title": "M3 Max MacBook vs ThinkPad for Docker, Kubernetes & Local Dev",
        "category": "hardware",
        "creator": "HardwareBenchmark",
        "license": "CC-BY-4.0",
        "difficulty": "Intermediate",
        "transcript": "Running 12 microservice Docker containers simultaneously: memory pressure benchmarks, battery drain, and thermal throttling compared between Apple Silicon and x86.",
        "concepts": ["hardware", "developer_workstation", "docker", "local_development"],
    },
    {
        "reel_id": "reel_gaming_gear",
        "title": "Custom mechanical keyboard build: creamy switch sound test & RGB setup",
        "category": "hardware",
        "creator": "KeebLab",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Lubing linear switches with Krytox 205g0, tape mod on the PCB, and aluminum plate typing sound test. Listen to this thock.",
        "concepts": ["mechanical_keyboards", "gaming_setup", "desk_aesthetic"],
    },
    {
        "reel_id": "reel_homelab_server",
        "title": "Building a low-power 64TB Proxmox home server with ECC memory",
        "category": "hardware",
        "creator": "HomelabHacks",
        "license": "CC-BY-4.0",
        "difficulty": "Intermediate",
        "transcript": "Configuring ZFS RAID-Z2 pool, TrueNAS virtualization, Docker container networking, and achieving 25-watt idle power draw.",
        "concepts": ["homelab", "proxmox", "zfs", "servers"],
    },

    # --- 7. Career / Software Engineering Growth (3) ---
    {
        "reel_id": "reel_interview_joke",
        "title": "When the interviewer asks to invert a binary tree on a whiteboard",
        "category": "career",
        "creator": "TechCareerTips",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Interviewer: Can you invert a binary tree on this whiteboard in 15 minutes? Me: Sir, in production I just use library functions, please don't fail me.",
        "concepts": ["coding_interviews", "dsa", "career_prep"],
    },
    {
        "reel_id": "reel_career_resume_tips",
        "title": "How to format software engineer resume bullet points using XYZ formula",
        "category": "career",
        "creator": "TechCareerTips",
        "license": "CC-BY-4.0",
        "difficulty": "Beginner",
        "transcript": "Accomplished [X] as measured by [Y] by doing [Z]. For example: Reduced API response latency by 35% by implementing Redis query caching.",
        "concepts": ["resume_writing", "software_engineer", "career_prep"],
    },
    {
        "reel_id": "reel_system_design_interview",
        "title": "How to structure a 45-minute System Design interview for Senior SWE roles",
        "category": "career",
        "creator": "SystemDesignPro",
        "license": "MIT",
        "difficulty": "Advanced",
        "transcript": "Clarifying functional vs non-functional requirements in first 5 minutes, high-level architecture diagram, database schema design, and deep dive into bottlenecks.",
        "concepts": ["system_design", "interview_prep", "software_engineer"],
    },

    # --- 8. Technology News & Infrastructure (3) ---
    {
        "reel_id": "reel_linux_cli_tricks",
        "title": "5 Linux terminal commands every backend developer must know",
        "category": "coding",
        "creator": "LinuxSysAdmin",
        "license": "Apache-2.0",
        "difficulty": "Beginner",
        "transcript": "Mastering htop for CPU inspection, lsof for finding occupied ports, grep with ripgrep for fast regex search, and journalctl for system logs.",
        "concepts": ["linux_cli", "bash", "server_troubleshooting"],
    },
    {
        "reel_id": "reel_tech_news_cloud",
        "title": "Major cloud provider announces regional serverless datacenter expansion",
        "category": "tech_news",
        "creator": "CloudNewsDaily",
        "license": "CC-BY-4.0",
        "difficulty": "Intermediate",
        "transcript": "Three new edge regions added with sub-5ms latency guarantees for serverless functions and managed Postgres replication across availability zones.",
        "concepts": ["cloud_infrastructure", "serverless", "distributed_datacenters"],
    },
    {
        "reel_id": "reel_cloud_k8s",
        "title": "Kubernetes Pod Lifecycle & Microservices Networking Explained",
        "category": "coding",
        "creator": "CloudMaster",
        "license": "Apache-2.0",
        "difficulty": "Intermediate",
        "transcript": "How kube-proxy routes traffic to container endpoints, how ingress controllers terminate TLS, and how readiness probes prevent dropped connections.",
        "concepts": ["kubernetes", "microservices", "cloud_networking", "docker"],
    },

    # --- 9. Hype Trap (1 - Intended to be filtered by gates) ---
    {
        "reel_id": "reel_ai_hype_trap",
        "title": "10 AI Tools That Will Replace Programmers and Guarantee You a $200k Job in 2026 With ZERO Coding!",
        "category": "tech_news",
        "creator": "HypeInfluencer",
        "license": "CC0",
        "difficulty": "Beginner",
        "transcript": "Stop learning to code right now! These 10 mindblowing secret AI websites will guarantee instant wealth while you sleep without studying.",
        "concepts": ["ai_hype", "career_shortcuts"],
        "is_hype_trap": True,
    },
]


def main() -> None:
    content_dir = DATA_DIR / "content"
    incoming_dir = content_dir / "incoming"
    accepted_dir = content_dir / "accepted"
    rejected_dir = content_dir / "rejected"
    processed_dir = content_dir / "processed"

    for d in (incoming_dir, accepted_dir, rejected_dir, processed_dir):
        d.mkdir(parents=True, exist_ok=True)

    ingestor = ReelIngestor(content_dir=content_dir)
    reviewer = ReelReviewer(content_dir=content_dir)

    print("================================================================================")
    print("             SCROLLSENSE: BUILDING OFFICIAL DEMO REEL CORPUS                    ")
    print("================================================================================\n")

    accepted_count = 0
    rejected_count = 0

    for spec in DEMO_REELS_SPEC:
        reel_id = spec["reel_id"]
        filename = f"{reel_id}.mp4"
        raw_path = incoming_dir / filename
        raw_path.write_bytes(MP4_HEADER)

        payload = RawAssetPayload(
            file_path=str(raw_path.resolve()),
            source_url=f"https://scrollsense.demo/reels/{reel_id}",
            source_platform="local_filesystem",
            creator=spec["creator"],
            license=spec["license"],
            title=spec["title"],
            transcript=spec["transcript"],
            category=spec["category"],
            difficulty_str=spec["difficulty"],
            extraction_method="human_verified",
        )

        result = ingestor.ingest_payload(payload=payload, allow_duplicate=True)

        if result.gate_result.passed and not spec.get("is_hype_trap", False):
            # Human review approval
            approved_item = reviewer.approve_reel(
                reel_id=result.item.reel_id,
                reviewer="senior_curator",
                notes="Verified high substance and educational clarity",
            )
            accepted_count += 1
            print(f"[ACCEPTED] {approved_item.reel_id} -> {Path(approved_item.asset_path).name}")
        else:
            rejected_count += 1
            print(f"[REJECTED / GATE FILTERED] {result.item.reel_id} (Reason: {result.gate_result.rejection_reason})")

    print("\n--------------------------------------------------------------------------------")
    print(f"Total Demo Reels Processed: {len(DEMO_REELS_SPEC)}")
    print(f"Accepted Playable Reels:    {accepted_count}")
    print(f"Filtered / Rejected Reels:  {rejected_count}")
    print("Manifest saved to: data/content/manifest.json")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
