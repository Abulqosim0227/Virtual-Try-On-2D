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

# Risks and Mitigations

Ordered by severity. Risk #1 can kill the business. Risk #7 is manageable.

## Risk 1: Licensing Blocks Commercial Launch

**Severity: CRITICAL — business-ending if ignored.**

**Problem:** Almost every strong open-weight VTO model is CC BY-NC-SA 4.0 or "Research only." Launching a paid SaaS, white-label, or API product on these models without a commercial license is illegal. There are very few fully permissive VTO models in 2026.

**Current state:**
- CatVTON (MVP primary): CC BY-NC-SA 4.0 — non-commercial.
- IDM-VTON (Tier 2): CC BY-NC-SA 4.0 — non-commercial.
- Re-CatVTON, FASHN-VTON v1.5, VTON-VLLM, RefVTON: licenses unverified.

**Mitigation:**
- **Immediate:** Audit the LICENSE file in every repo we plan to use. Track in a spreadsheet (model, license, commercial OK, author contact, date checked).
- **Phase 1:** Contact CatVTON authors about commercial licensing. Many academic teams negotiate reasonable terms ($1-5K/year or revenue share).
- **Fallback:** Budget $1-5K for commercial API (fal.ai Lucy) as a bridge if no open model clears licensing.
- **Architecture protection:** BaseVTOModel adapter pattern (see pipeline.md) means we can swap any model without rewriting the pipeline. If a model gets a license change or takedown, we swap in 1 day.
- **Hard gate:** Do not have revenue conversations with Uzum/Sello until at least one commercially-viable model is secured.

## Risk 2: VRAM Exhaustion on Single GPU

**Severity: HIGH — blocks all development if hit frequently.**

**Problem:** RTX 5070 Ti has 16GB VRAM. Preprocessing models (~4-5GB fp16) + CatVTON (~4GB fp16) = ~8-9GB at idle. A 4K input image, a VRAM leak, or loading Tier 2 without unloading Tier 1 will cause instant OOM and crash the FastAPI server.

**Mitigation:**
- **Edge-level input normalization:** All images resized to 768x1024 at the API boundary before the GPU sees them (see api.md).
- **VRAMManager singleton:** Only one generation model loaded at a time. Tier 2 (IDM-VTON) uses accelerate CPU offloading — weights in 64GB system RAM, active layers stream to VRAM.
- **fp16 everywhere:** Halves VRAM usage for all models.
- **VRAM cleanup contract:** Every request runs `torch.cuda.empty_cache()` in a `finally` block. Intermediate tensors deleted immediately after use.
- **asyncio.Lock:** Prevents concurrent inference. Second request waits, never competes for VRAM.
- **Monitoring:** `/v1/health` endpoint reports `gpu_vram_used_mb` and `gpu_vram_total_mb`. Log VRAM before and after every request.

## Risk 3: Model Compatibility

**Severity: HIGH — wastes weeks if models don't integrate.**

**Problem:** Different models expect different input formats, resolutions, preprocessing outputs. Assuming they work together without testing leads to silent quality degradation or crashes.

**Mitigation:**
- Phase 1 Week 1: standalone benchmark of CatVTON on 5070 Ti. Verify exact I/O contract (input shapes, dtype, expected preprocessing outputs).
- BaseVTOModel adapter: each model declares its own preprocessing requirements. Pipeline only runs what the active model needs.
- Integration tests: run 3-pair micro test set (see evaluation.md) through full pipeline on every code change.
- Test models in isolation before integration: CatVTON → Re-CatVTON → FASHN-VTON v1.5 → VTON-VLLM (see models.md evaluation order).

## Risk 4: Latency Worse Than Expected

**Severity: MEDIUM — impacts UX but doesn't block launch.**

**Problem:** Latency estimates in pipeline.md are unverified. Real-world includes upload over RDP network, preprocessing, model swap overhead, and post-processing. CatVTON "~11s" is from the original paper on unknown hardware.

**Mitigation:**
- Revised latency budget: Tier 1 target 4-10s, Tier 2 target 18-35s (see pipeline.md). Honest, not aspirational.
- First Phase 1 task: benchmark CatVTON on 5070 Ti. Measure preprocessing, inference, and post-processing separately.
- torch.compile for 20-30% free speedup (see hardware.md). Defer TensorRT to cloud optimization phase.
- If Tier 1 exceeds 10s consistently: investigate FASHN-VTON v1.5 (skips preprocessing entirely).

## Risk 5: Concurrency Limited to 1-3 Requests

**Severity: MEDIUM — limits demo capacity but acceptable for MVP.**

**Problem:** Single GPU + asyncio.Lock means one inference at a time. During a demo with multiple users, requests queue and latency stacks.

**Mitigation:**
- Realistic MVP target: 1-3 concurrent users (one inferencing, 1-2 waiting).
- Redis cache absorbs duplicate requests. Cache hit = 0 GPU cost.
- 30s queue timeout: if wait exceeds 30s, return 503 with Retry-After header.
- Load test with locust at end of Phase 2 to establish real baseline.
- Scale path: RunPod serverless ($0.30/hr per GPU) when demand exceeds single GPU.

## Risk 6: Failure Recovery

**Severity: MEDIUM — poor error handling destroys user trust.**

**Problem:** GPU crashes, model loading failures, corrupt inputs, timeouts. Without explicit handling, users get blank screens or cryptic 500 errors.

**Mitigation:**
- Exception-driven fallbacks (see orchestrator.md): VRAMExhaustedError, WorkerTimeoutError, PreprocessingError, ModelLoadError, InvalidInputError.
- Every error returns structured JSON: `{success: false, error: {code, message}}`.
- Every error logs full context (without image data) for debugging.
- VRAM cleanup runs in `finally` block — even crashed requests don't leak GPU memory.
- If CatVTON fails to load: return 503, log alert. No silent degradation.

## Risk 7: Vendor Lock-in

**Severity: LOW — manageable with current architecture.**

**Problem:** Depending on one cloud provider, one model, or one API.

**Mitigation:**
- BaseVTOModel adapter: swap any model without pipeline changes.
- Docker-based deployment: runs on any cloud with NVIDIA GPUs.
- No vendor-specific cloud services in MVP (no AWS Lambda, no GCP-specific APIs).
- If RunPod becomes expensive or unreliable, same Docker image deploys to Vast.ai, Lambda Labs, or bare metal.

## Resolved Risks (Previously Open)

These were identified in the original plan review and have been addressed:

| Risk | Resolution |
|------|-----------|
| No API contract | Defined in api.md |
| No evaluation framework | Defined in evaluation.md |
| No dataset strategy | Defined in datasets.md |
| Security too high-level | Full policy in security.md |
| No failure/fallback design | Exception-driven fallbacks in orchestrator.md |
