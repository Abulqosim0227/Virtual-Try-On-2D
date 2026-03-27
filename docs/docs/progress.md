# Rules

1. Never write code without asking permission first. Explain what and why before writing.
2. After writing code, explain it, then ask permission before the next function/file.
3. State which file I'm starting with before touching it.
4. Clean, fast, understandable. No unnecessary comments. No emojis. No bloat.
5. Shorter and cleaner beats longer. Every line earns its place.
6. Top priority: privacy and security.
7. Check my own code after writing. Alert on concerns.
8. Never skip or forget these rules.

# Plan Mode

Review this plan thoroughly before making any code changes. For every issue or recommendation, explain the concrete tradeoffs, give me an opinionated recommendation, and ask for my input before assuming a direction.

Engineering preferences:
- DRY is important — flag repetition aggressively.
- Well-tested code is non-negotiable; rather too many tests than too few.
- Code should be "engineered enough" — not under-engineered (fragile, hacky), not over-engineered (premature abstraction, unnecessary complexity).
- Err on the side of handling more edge cases, thoughtfulness > speed.
- Bias toward explicit over clever.

Review sections: Architecture > Code Quality > Tests > Performance.
Before starting, ask: BIG CHANGE (4 top issues per section) or SMALL CHANGE (1 question per section).
For each issue: describe concretely with file/line refs, present 2-3 options, give recommended option, ask before proceeding.

---

# Progress

> Last updated: March 17, 2026
> Status: Plan review complete. All docs revised. Ready for Phase 1 implementation.

## Timeline

### Step 1: Card Vault Bot (Abandoned)
- Originally explored a Telegram card-management bot.
- Discussed security/storage trade-offs.
- Decided to stop. Design docs deleted.

### Step 2: Market Research
- Searched for what the Uzbek market needs.
- Top opportunities: SME tools, AgriTech, FinTech, EdTech, e-commerce infrastructure.
- Biggest pain points outside Tashkent — rural areas, small businesses.

### Step 3: Virtual Try-On Decision
- Discovered CVPR 2024 VTO Workshop: https://vto-cvpr24.github.io/
- Key requirement: "do not take only 1 model — combine into one great project."

### Step 4: Deep Research
- Found 11+ models across different categories.
- Researched TensorRT/ONNX optimization, MediaPipe, DensePose.

### Step 5: Two Plans Created
- Claude built visual HTML plan: `virtual-tryon-plan.html`
- Cursor built technical markdown plan: `REALTIME_VTO_MASTER_PLAN.md`

### Step 6: Plans Merged
- Combined into `virtual-tryon-masterpiece.html`.
- Claude strengths: visual design, UX, business, Uzbek market.
- Cursor strengths: multi-tier arch, orchestrator, model coverage, routing.

### Step 7: Fixed 8 Critical Gaps
1. Model compatibility — audit plan, adapter layer, standalone fallback.
2. Latency claims — revised per-component budget with realistic numbers.
3. Concurrency — load test plan, realistic 5-15 concurrent (not 50-100).
4. Failure handling — 4-level degradation ladder.
5. Security — full policy (retention, signed URLs, encryption, audit, NSFW).
6. Evaluation — KPIs (SSIM, FID, LPIPS, ArcFace, CLIP, human eval).
7. Dataset strategy — public first, then Uzbek 5K pairs collection.
8. API contract — REST + WebSocket schemas, versioning, error codes.

### Step 8: Hardware Decision
- PC (RTX 5070 Ti 16GB, i9-14900K, 64GB RAM) = sole dev machine (RDP access).
- Cloud (RunPod $0.30/hr) when making money.

### Step 9: Model Research (OutfitAnyone)
- Evaluated OutfitAnyone (HumanAIGC/Alibaba). Two-stream diffusion with refiner stage.
- Verdict: not usable. No open weights, no code, demo only, non-commercial license.
- Confirmed our multi-model approach is stronger.

### Step 10: Full Plan Review (March 17, 2026)

Reviewed all 14 docs with team (3 people). Two rounds of review.

**Round 1 — Model & licensing refresh:**
- Added 5 new 2025-2026 models: CatV2TON, Re-CatVTON, FASHN-VTON v1.5, VTON-VLLM, RefVTON.
- Elevated licensing to #1 business risk. Most VTO models are non-commercial.
- Added commercial license column to models.md.
- Fixed stale conference dates across all docs.

**Round 2 — Architecture overhaul for single GPU:**
- Replaced microservices with modular monolith (single FastAPI process).
- Added VRAMManager singleton — one generation model loaded at a time.
- Removed progressive delivery for MVP (impossible on single GPU).
- Removed video tier, mobile tier from MVP scope.
- Added edge-level input normalization (768x1024 max).
- Exception-driven fallbacks replace polling-based degradation ladder.
- In-memory pipeline with Pydantic TryOnContext object.
- Sequential preprocessing (no threading, prevents VRAM fragmentation).
- fp16 everywhere, torch.compile for free speedup, accelerate CPU offloading for Tier 2.
- Collapsed 7 phases to 3 phases + future backlog.
- Separated software tests (pytest, CI) from ML evaluation (manual script).
- Added micro test set (3 pairs), MockVTOModel, VRAM cleanup tests.
- Added human preference metrics (from VTON-VLLM paper).

**All 14 docs updated.** No code written.

## Current State
- All planning docs revised and internally consistent.
- No production code exists.
- RTX 5070 Ti RDP machine confirmed as sole development hardware.
- Ready to begin Phase 1 Week 1.

## Next Action
Phase 1 Week 1: git repo init, Python environment, download VITON-HD + CatVTON weights, benchmark CatVTON on 5070 Ti, GitHub Actions CI, license audit.
