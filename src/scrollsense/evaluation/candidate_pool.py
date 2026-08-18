"""Comprehensive 20-candidate evaluation repository pool containing literal, adjacent, boundary, grounded, hype, and distractor items."""

from scrollsense.domain.enums import DepthLevel
from scrollsense.domain.reels import Reel
from scrollsense.retrieval.repository import CandidateRepository


def get_evaluation_candidate_reels() -> list[Reel]:
    """Return ~20 standard evaluation candidate reels covering all test categories."""
    return [
        # --- 1. Literal-Topic Candidates (Surface-Level) ---
        Reel(
            reel_id="reel_java_syntax_basics",
            title="Java 21 Syntax: Records, Sealed Classes & Pattern Matching",
            category="coding",
            format="tutorial",
            tone="instructional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["java", "records", "sealed_classes", "pattern_matching"],
            transcript="Stop writing verbose boilerplate POJOs. Here is how Java records and pattern matching switch statements make domain modeling clean.",
        ),
        Reel(
            reel_id="cand_literal_fps_aim",
            title="Kovaaks 101: Basic Tracking and Click-Timing Drill Presets",
            category="gaming",
            format="tutorial",
            tone="instructional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["fps_gaming", "aim_training"],
            transcript="Start with 1wall6targets small and smooth tracking drills to warm up wrist reflexes.",
        ),
        Reel(
            reel_id="cand_literal_prompt_listicle",
            title="5 Copy-Paste ChatGPT Prompts for Everyday Email Writing",
            category="coding",
            format="listicle",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["prompt_engineering", "productivity"],
            transcript="Prompt 1: Summarize this email. Prompt 2: Make this tone more polite. Copy and paste these into ChatGPT.",
        ),
        Reel(
            reel_id="cand_literal_espresso_beans",
            title="Dark roast vs Light roast: Water temperature and grind size guide",
            category="lifestyle",
            format="tutorial",
            tone="instructional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["coffee", "lifestyle"],
            transcript="Why lighter roasts need 94C water and finer burr settings to extract bright floral tasting notes.",
        ),

        # --- 2. Identity-Adjacent Technical Candidates (High Value Core Skills) ---
        Reel(
            reel_id="reel_hld_caching",
            title="System Design 101: Distributed Caching with Redis & Invalidation Strategies",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["distributed_systems", "system_design", "redis", "cache_invalidation"],
            transcript="Cache-aside vs write-through caching patterns. How to handle the cache stampede problem and maintain eventual consistency.",
        ),
        Reel(
            reel_id="reel_dsa_trees",
            title="Tree Traversal & Dynamic Programming Patterns for SWE Interviews",
            category="coding",
            format="tutorial",
            tone="instructional",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["dsa", "binary_trees", "dynamic_programming", "interview_prep"],
            transcript="Breaking down recursion into base cases, memoization tables, and bottom-up DP states for LeetCode medium questions.",
        ),
        Reel(
            reel_id="reel_ai_substance",
            title="Attention Mechanism & Transformer Neural Network Math Explained",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["transformers", "neural_networks", "attention_mechanism", "ai_architecture"],
            transcript="Understanding Query, Key, and Value matrix multiplications in self-attention with scaled dot-product visualization.",
        ),
        Reel(
            reel_id="cand_gpu_cuda_kernels",
            title="Writing Your First GPU CUDA Kernel in C++ with Shared Memory Tiling",
            category="coding",
            format="walkthrough",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["cuda", "gpu_computing", "parallel_programming", "ai"],
            transcript="Tiled matrix multiplication exploiting high-bandwidth GPU SRAM to overcome global memory memory-bandwidth bottlenecks.",
        ),
        Reel(
            reel_id="reel_gaming_gear",
            title="Custom mechanical keyboard build: creamy switch sound test & RGB setup",
            category="gadgets",
            format="gear_review",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["mechanical_keyboards", "gaming_setup", "desk_aesthetic"],
            transcript="Lubing linear switches with Krytox 205g0, tape mod on the PCB, and aluminum plate typing sound test.",
        ),

        # --- 3. Boundary / Exploration Candidates (Broadening Technology Universe) ---
        Reel(
            reel_id="reel_cloud_k8s",
            title="Kubernetes Pod Lifecycle & Microservices Networking Explained",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["kubernetes", "microservices", "cloud_networking", "docker"],
            transcript="How kube-proxy routes traffic to container endpoints, how ingress controllers terminate TLS, and how readiness probes prevent dropped connections.",
        ),
        Reel(
            reel_id="reel_security_auth",
            title="OAuth2 & JWT Security Pitfalls in Modern REST APIs",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["cybersecurity", "oauth2", "jwt", "api_security"],
            transcript="Never store refresh tokens in localStorage. We break down HttpOnly cookie security, CSRF defense mechanisms, and asymmetric token verification.",
        ),
        Reel(
            reel_id="cand_compiler_ast",
            title="Building a Bytecode Virtual Machine and AST Interpreter in Rust",
            category="coding",
            format="walkthrough",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["compilers", "rust", "computer_science"],
            transcript="Lexing, recursive-descent parsing into Abstract Syntax Trees, generating bytecode opcodes, and stack execution loop.",
        ),

        # --- 4. Grounded Technical Candidates (Deep Engineering Substance) ---
        Reel(
            reel_id="cand_linux_ebpf",
            title="Observability with Linux eBPF: Tracing Kernel Syscalls Without Overhead",
            category="coding",
            format="deep_dive",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["linux", "ebpf", "cloud_networking", "system_design"],
            transcript="Loading verified bytecode into the Linux kernel ring-0 to intercept socket connect syscalls and track network latencies.",
        ),
        Reel(
            reel_id="cand_db_lsm_trees",
            title="LSM-Trees vs B+ Trees: How RocksDB and Cassandra Optimize Write Throughput",
            category="coding",
            format="deep_dive",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["databases", "system_design", "distributed_systems"],
            transcript="Write-Ahead Logs, in-memory MemTables, SSTable compaction algorithms, and bloom filter lookups.",
        ),
        Reel(
            reel_id="cand_distributed_raft",
            title="Raft Consensus Algorithm Visualized: Leader Election and Log Replication",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["distributed_systems", "raft", "system_design"],
            transcript="Heartbeat timeouts, randomized candidate terms, majority quorum voting, and handling network split-brain partitions.",
        ),

        # --- 5. Hype / Promotional Low-Substance Traps (Must Be Rejected) ---
        Reel(
            reel_id="reel_ai_hype_trap",
            title="10 AI Tools That Will Replace Programmers and Guarantee You a $200k Job in 2026 With ZERO Coding!",
            category="tech_news",
            format="listicle",
            tone="promotional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["ai_hype", "get_rich_quick", "career_shortcuts"],
            transcript="Stop learning to code right now! These 10 secret AI websites will guarantee a job and do 100% of your work. Number 7 will shock you!",
        ),
        Reel(
            reel_id="cand_hype_10x_developer",
            title="How to Become a 10x Developer Overnight Without Studying DSA Or System Design",
            category="career",
            format="listicle",
            tone="promotional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["career_shortcuts", "ai_hype"],
            transcript="The secret hack big tech managers don't want you to know. Instant wealth and career guaranteed in 3 simple steps.",
        ),
        Reel(
            reel_id="cand_hype_crypto_bot",
            title="Automated AI Trading Bot That Generates $500/day Passive Income Guaranteed",
            category="tech_news",
            format="promotional",
            tone="promotional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["crypto", "ai_hype", "get_rich_quick"],
            transcript="Join my telegram group to download this guaranteed wealth generation bot script today.",
        ),

        # --- 6. Distractor / Unsafe Candidates ---
        Reel(
            reel_id="cand_distractor_prank",
            title="Hilarious Office Prank: Replacing Coworker Desk With Aluminum Foil",
            category="entertainment",
            format="comedy",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["pranks", "humor"],
            transcript="We wrapped their chair, monitor, keyboard, and coffee mug in tin foil before 9 AM.",
        ),
        Reel(
            reel_id="cand_unsafe_malware",
            title="How to write a persistent keylogger malware and bypass Windows Defender",
            category="cybersecurity",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["malware", "cybersecurity"],
            transcript="Download this exploit payload to silently intercept keystrokes and exfiltrate browser passwords.",
        ),
    ]


def get_evaluation_candidate_repository() -> CandidateRepository:
    """Construct a CandidateRepository populated with the 20 evaluation candidate reels."""
    return CandidateRepository(candidates=get_evaluation_candidate_reels())
