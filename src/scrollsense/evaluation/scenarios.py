"""Evaluation scenarios containing 4 diverse 8-Reel user interaction histories."""

from pydantic import BaseModel, ConfigDict, Field

from scrollsense.domain.enums import DepthLevel, TechCategory
from scrollsense.domain.reels import Reel


class Scenario(BaseModel):
    """Specification of an evaluation scenario with ground truth criteria."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="Description of the user persona and interaction history")
    input_reels: list[Reel] = Field(..., min_length=8, max_length=8, description="8-reel interaction history")
    ground_truth_latent_identity: str = Field(..., description="Expected latent professional identity")
    ground_truth_target_categories: list[TechCategory] = Field(
        ...,
        description="Target acceptable technical categories for top recommendations",
    )
    literal_trap_categories: list[TechCategory] = Field(
        default_factory=list,
        description="Shallow literal categories that represent surface-level traps",
    )


def get_all_scenarios() -> list[Scenario]:
    """Construct and return the 4 canonical 8-Reel evaluation scenarios."""

    # Scenario 1: SWE Latent Interest (8 Reels)
    swe_reels = [
        Reel(
            reel_id="s1_r1_java_meme",
            title="When NullPointerException hits in production at 3 AM",
            category="coding",
            format="meme",
            tone="humorous",
            depth=DepthLevel.BEGINNER,
            concept_tags=["java", "exception_handling", "production_debugging"],
            transcript="3 AM pager goes off. Null pointer in the payment gateway. Who merged without a null check?",
        ),
        Reel(
            reel_id="s1_r2_swe_lifestyle",
            title="Day in the life of a backend engineer at a Seattle tech company",
            category="coding",
            format="vlog",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["software_engineering", "workplace_culture"],
            transcript="Morning standup, reviewing pull requests, designing API schemas, and afternoon deep work.",
        ),
        Reel(
            reel_id="s1_r3_interview_joke",
            title="When the interviewer asks to invert a binary tree on a whiteboard",
            category="coding",
            format="interview_joke",
            tone="humorous",
            depth=DepthLevel.BEGINNER,
            concept_tags=["coding_interviews", "dsa", "career_prep"],
            transcript="I have 5 years building scalable distributed microservices, but please watch me invert this binary tree on a glass wall.",
        ),
        Reel(
            reel_id="s1_r4_laptop_review",
            title="M3 Max MacBook vs ThinkPad for Docker, Kubernetes & Local Dev",
            category="hardware",
            format="hardware_comparison",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["hardware", "developer_workstation", "docker", "local_development"],
            transcript="Benchmarking build times for 50 microservices container cluster in Docker Desktop.",
        ),
        Reel(
            reel_id="s1_r5_git_conflict",
            title="Git merge vs rebase explained in 30 seconds of pure terror",
            category="coding",
            format="meme",
            tone="humorous",
            depth=DepthLevel.BEGINNER,
            concept_tags=["git", "version_control", "coding"],
            transcript="When 4 engineers edit the same auth middleware and push with force.",
        ),
        Reel(
            reel_id="s1_r6_terminal_workflow",
            title="My minimalist terminal & tmux setup for high-speed backend hacking",
            category="coding",
            format="walkthrough",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["terminal", "linux", "tmux", "backend"],
            transcript="Fast navigation across multiple server SSH sessions with tmux pane splits and fzf fuzzy search.",
        ),
        Reel(
            reel_id="s1_r7_docker_compose",
            title="It works on my machine: docker compose for local PostgreSQL & Redis",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.BEGINNER,
            concept_tags=["docker", "postgresql", "redis", "backend"],
            transcript="Spin up your database, caching layer, and mock S3 storage in one single docker-compose.yml file.",
        ),
        Reel(
            reel_id="s1_r8_system_whiteboard",
            title="Senior engineer breaks down event-driven architecture on a glass board",
            category="coding",
            format="walkthrough",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["system_design", "event_driven", "kafka", "microservices"],
            transcript="Why synchronous REST creates cascading failures and how Kafka event logs decouple services.",
        ),
    ]

    # Scenario 2: Gaming (8 Reels)
    gaming_reels = [
        Reel(
            reel_id="s2_r1_fps_clutch",
            title="1v5 Clutch defusal in tactical FPS grand final round",
            category="gaming",
            format="gameplay_clip",
            tone="energetic",
            depth=DepthLevel.BEGINNER,
            concept_tags=["fps_gaming", "esports"],
            transcript="No armor, 15 HP, 10 seconds on the bomb clock. Watch this pixel-perfect crosshair placement.",
        ),
        Reel(
            reel_id="s2_r2_custom_keyboard",
            title="Custom mechanical keyboard build: creamy switch sound test & RGB setup",
            category="gadgets",
            format="gear_review",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["mechanical_keyboards", "gaming_setup", "desk_aesthetic"],
            transcript="Lubing linear switches with Krytox 205g0, tape mod on the PCB, and aluminum plate sound test.",
        ),
        Reel(
            reel_id="s2_r3_esports_moments",
            title="Top 10 craziest esports tournament moments of the decade",
            category="gaming",
            format="compilation",
            tone="energetic",
            depth=DepthLevel.BEGINNER,
            concept_tags=["esports", "gaming_highlights"],
            transcript="The crowd reaction in the arena when the final headshot landed in overtime round 30.",
        ),
        Reel(
            reel_id="s2_r4_aim_warmup",
            title="Pro gamer 15-minute daily aim trainer routine for micro-adjustments",
            category="gaming",
            format="tutorial",
            tone="instructional",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["fps_gaming", "aim_training"],
            transcript="Gridshot, tracking spheres, and flick precision exercises to build muscle memory.",
        ),
        Reel(
            reel_id="s2_r5_ultrawide_desk",
            title="Dream gaming battlestation tour: 49 inch OLED & monitor arms",
            category="gadgets",
            format="vlog",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["gaming_setup", "desk_aesthetic"],
            transcript="Zero cable clutter, hidden power bricks under the desk, and synchronized nanoleaf lighting.",
        ),
        Reel(
            reel_id="s2_r6_speedrun_record",
            title="How a runner shaved 0.4 seconds off the world speedrun record",
            category="gaming",
            format="deep_dive",
            tone="analytical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["speedrun", "gaming_mechanics"],
            transcript="Analyzing sub-pixel wall jumps and frame-perfect collision glitches in the castle level.",
        ),
        Reel(
            reel_id="s2_r7_mouse_sensor",
            title="Wireless gaming mouse latency test: 8000Hz polling rate real difference",
            category="gadgets",
            format="gear_review",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["gaming_gear", "hardware"],
            transcript="Measuring motion delay and click response times with oscilloscope probes.",
        ),
        Reel(
            reel_id="s2_r8_game_glitches",
            title="Physics engine chaos: top hilarious open world game bugs",
            category="gaming",
            format="comedy",
            tone="humorous",
            depth=DepthLevel.BEGINNER,
            concept_tags=["gaming_humor", "glitches"],
            transcript="When ragdoll physics multiply by negative gravity and vehicles launch into orbit.",
        ),
    ]

    # Scenario 3: AI / Machine Learning (8 Reels)
    ai_reels = [
        Reel(
            reel_id="s3_r1_prompt_hacks",
            title="How prompt engineering is changing junior developer workflows",
            category="coding",
            format="screencast",
            tone="informative",
            depth=DepthLevel.BEGINNER,
            concept_tags=["prompt_engineering", "ai_tools"],
            transcript="Structuring system instructions with few-shot examples and chain-of-thought scratchpads.",
        ),
        Reel(
            reel_id="s3_r2_local_llm",
            title="Running Llama 3 8B locally on your laptop with Ollama and vLLM",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["ai", "local_llm", "transformers"],
            transcript="Quantization with 4-bit GGUF, KV cache management, and continuous batching on consumer GPUs.",
        ),
        Reel(
            reel_id="s3_r3_numpy_vectorization",
            title="Stop writing Python for-loops: Vectorized matrix operations with NumPy",
            category="coding",
            format="tutorial",
            tone="instructional",
            depth=DepthLevel.BEGINNER,
            concept_tags=["python", "numpy", "data_science"],
            transcript="Replacing 100,000 loop iterations with single SIMD broadcast tensor operations.",
        ),
        Reel(
            reel_id="s3_r4_pytorch_gradients",
            title="Visualizing backpropagation and gradient descent loss landscapes in PyTorch",
            category="coding",
            format="walkthrough",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["pytorch", "neural_networks", "ai_math"],
            transcript="Automatic differentiation, computational graphs, and learning rate momentum dynamics.",
        ),
        Reel(
            reel_id="s3_r5_gpu_cuda",
            title="Why GPUs are fast for AI: Tensor cores vs CPU threads visualized",
            category="hardware",
            format="deep_dive",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["cuda", "gpu_computing", "hardware", "ai"],
            transcript="Massively parallel matrix multiplication across thousands of lightweight streaming multiprocessors.",
        ),
        Reel(
            reel_id="s3_r6_ai_agent_rag",
            title="Building a real-time Retrieval Augmented Generation (RAG) pipeline",
            category="coding",
            format="tutorial",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["rag", "vector_databases", "embeddings", "ai"],
            transcript="Chunking strategies, cosine similarity retrieval in vector DBs, and context reranking.",
        ),
        Reel(
            reel_id="s3_r7_attention_heatmap",
            title="Self-attention heatmaps: How transformers attend to surrounding tokens",
            category="coding",
            format="screencast",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["transformers", "attention_mechanism", "ai_architecture"],
            transcript="Multi-head scaled dot-product attention visualizing subject-verb syntactic dependencies.",
        ),
        Reel(
            reel_id="s3_r8_eval_dspy",
            title="Systematic LLM evaluation and synthetic data generation with DSPy",
            category="coding",
            format="walkthrough",
            tone="technical",
            depth=DepthLevel.ADVANCED,
            concept_tags=["dspy", "ai_evaluation", "synthetic_data"],
            transcript="Compiling prompt signatures into optimized teleprompter modules using metric optimizers.",
        ),
    ]

    # Scenario 4: Ambiguous / Mixed (8 Reels)
    mixed_reels = [
        Reel(
            reel_id="s4_r1_java_humor",
            title="When NullPointerException hits in production at 3 AM",
            category="coding",
            format="meme",
            tone="humorous",
            depth=DepthLevel.BEGINNER,
            concept_tags=["java", "exception_handling"],
            transcript="3 AM pager goes off. Null pointer in payment gateway.",
        ),
        Reel(
            reel_id="s4_r2_gaming_clip",
            title="1v5 Clutch defusal in tactical FPS grand final round",
            category="gaming",
            format="gameplay_clip",
            tone="energetic",
            depth=DepthLevel.BEGINNER,
            concept_tags=["fps_gaming", "esports"],
            transcript="15 HP, 10 seconds on the bomb clock.",
        ),
        Reel(
            reel_id="s4_r3_desk_coffee",
            title="Rainy morning desk routine: espresso and lofi focus vibes",
            category="lifestyle",
            format="vlog",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["desk_aesthetic", "coffee", "lifestyle"],
            transcript="Grinding fresh beans, steam wand latte art, and turning on ambient rain sounds.",
        ),
        Reel(
            reel_id="s4_r4_ai_news",
            title="How prompt engineering is changing junior developer workflows",
            category="coding",
            format="screencast",
            tone="informative",
            depth=DepthLevel.BEGINNER,
            concept_tags=["prompt_engineering", "ai_tools"],
            transcript="Structuring system instructions with few-shot examples.",
        ),
        Reel(
            reel_id="s4_r5_keyboard_build",
            title="Custom mechanical keyboard build: creamy switch sound test",
            category="gadgets",
            format="gear_review",
            tone="casual",
            depth=DepthLevel.BEGINNER,
            concept_tags=["mechanical_keyboards", "gaming_setup"],
            transcript="Lubing linear switches with Krytox 205g0.",
        ),
        Reel(
            reel_id="s4_r6_laptop_dock",
            title="M3 Max MacBook vs ThinkPad for Docker, Kubernetes & Local Dev",
            category="hardware",
            format="hardware_comparison",
            tone="technical",
            depth=DepthLevel.INTERMEDIATE,
            concept_tags=["hardware", "docker"],
            transcript="Benchmarking build times for microservices in Docker.",
        ),
        Reel(
            reel_id="s4_r7_game_glitch",
            title="Physics engine chaos: top hilarious open world game bugs",
            category="gaming",
            format="comedy",
            tone="humorous",
            depth=DepthLevel.BEGINNER,
            concept_tags=["gaming_humor", "glitches"],
            transcript="Ragdoll physics multiplying by negative gravity.",
        ),
        Reel(
            reel_id="s4_r8_startup_podcast",
            title="Founders podcast: Scaling from zero to 100k daily active users",
            category="business",
            format="podcast_clip",
            tone="informative",
            depth=DepthLevel.BEGINNER,
            concept_tags=["startups", "entrepreneurship", "business"],
            transcript="How early product-market fit requires talking to 10 users every single day.",
        ),
    ]

    return [
        Scenario(
            scenario_id="scenario_swe_latent",
            name="1. Latent Software Engineer Interest",
            description="Student watches memes, workstation reviews, and developer lifestyle clips indicating latent SWE intent.",
            input_reels=swe_reels,
            ground_truth_latent_identity="software_engineer",
            ground_truth_target_categories=[TechCategory.HLD, TechCategory.DSA, TechCategory.CLOUD, TechCategory.CYBERSECURITY, TechCategory.AI],
            literal_trap_categories=[TechCategory.JAVA],
        ),
        Scenario(
            scenario_id="scenario_gaming",
            name="2. Pure Gamer Non-Trap",
            description="Student strictly watches competitive FPS gameplay, speedruns, and gear reviews.",
            input_reels=gaming_reels,
            ground_truth_latent_identity="gamer",
            ground_truth_target_categories=[TechCategory.HARDWARE, TechCategory.OTHER],
            literal_trap_categories=[],
        ),
        Scenario(
            scenario_id="scenario_ai_ml",
            name="3. AI / Machine Learning Explorer",
            description="Student explores RAG pipelines, tensor math, CUDA architectures, and prompt tooling.",
            input_reels=ai_reels,
            ground_truth_latent_identity="software_engineer",
            ground_truth_target_categories=[TechCategory.AI, TechCategory.HLD, TechCategory.CLOUD, TechCategory.DSA],
            literal_trap_categories=[],
        ),
        Scenario(
            scenario_id="scenario_mixed_ambiguous",
            name="4. Ambiguous / Mixed Interaction History",
            description="Student watches a diverse mix of lifestyle, gaming, and technology reels.",
            input_reels=mixed_reels,
            ground_truth_latent_identity="software_engineer",
            ground_truth_target_categories=[TechCategory.HLD, TechCategory.AI, TechCategory.HARDWARE, TechCategory.CLOUD],
            literal_trap_categories=[],
        ),
    ]
