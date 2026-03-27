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

# Architecture

## Constraint: Single GPU (RTX 5070 Ti, 16GB VRAM)

Every architectural decision is driven by this constraint. One process, one GPU, one model loaded at a time. The system is designed to scale out to cloud GPUs later without rewriting business logic.

## Modular Monolith

A single FastAPI application handles everything: routing, preprocessing, inference, caching, and delivery. No separate worker processes, no message broker, no duplicated CUDA contexts.

```
[Client Browser]
       |
[FastAPI Application]
  ├── Auth + Rate Limiting (slowapi, in-process)
  ├── Input Normalizer (resize to 768x1024 at boundary)
  ├── Router (function, not a service)
  ├── Preprocessing Pipeline (sequential, in-memory)
  ├── VRAMManager (singleton, load/unload generation models)
  ├── Tier 1 Inference (CatVTON, fp16, ~4GB resident)
  ├── Tier 2 Inference (IDM-VTON, CPU-offloaded via accelerate)
  ├── Cache (Redis, SHA256 on original upload bytes)
  └── Result Storage (local temp dir, signed URLs)
```

## Two Explicit Modes (No Progressive Delivery)

On a single GPU, progressive delivery (Tier 1 + Tier 2 simultaneously) causes OOM. Instead, the user explicitly chooses:

| Endpoint | Model | Behavior | Target Latency |
|----------|-------|----------|----------------|
| `POST /tryon/fast` | Tier 1 (CatVTON) | Synchronous response | 3-6s |
| `POST /tryon/hd` | Tier 2 (IDM-VTON) | Async job, poll for result | 15-40s |

Progressive delivery is deferred to cloud deployment where Tier 1 and Tier 2 run on separate GPU instances.

## VRAMManager

Singleton that controls GPU memory. Only one generation model is loaded at a time.

- **Preprocessing models** (DWPose, SCHP, RMBG): small, kept resident in fp16 (~4-5GB total).
- **Tier 1 model** (CatVTON): loaded on-demand in fp16 (~4GB). Default resident model.
- **Tier 2 model** (IDM-VTON): loaded on-demand via `accelerate` CPU offloading. Weights live in 64GB system RAM, active layers move to VRAM during forward pass. Automatically unloaded after inference.

Load/unload cycle: ~2-3s penalty when switching between Tier 1 and Tier 2. Acceptable for MVP.

## Edge-Level Input Normalization

Before the ML pipeline sees any image:

1. Validate file type (JPEG/PNG only) and size (<10MB).
2. Resize and pad to exactly **768x1024** (CatVTON native resolution).
3. Convert to RGB, strip EXIF metadata.

This guarantees predictable VRAM usage. No 4K image ever reaches the GPU.

## Exception-Driven Degradation

No health-check polling. The system reacts to failures as they happen:

| Exception | Trigger | Response |
|-----------|---------|----------|
| `VRAMExhaustedError` | torch.cuda.OutOfMemoryError caught | Return 503, suggest `/tryon/fast` at lower resolution |
| `WorkerTimeoutError` | Inference exceeds 60s | Kill task, return 504, log for investigation |
| `PreprocessingError` | Person/garment not detected | Return 422 with specific message |
| `CacheHitResponse` | SHA256 match in Redis | Return cached result, skip GPU entirely |

FastAPI exception handlers catch these and return structured error responses. No silent failures.

## Key Components

| Component | Responsibility |
|-----------|---------------|
| FastAPI app | Auth (JWT), rate limiting (slowapi), request validation (Pydantic) |
| Router | Selects Tier 1 or Tier 2 based on endpoint. Checks cache first. |
| Preprocessing | Pose, parsing, background removal, normalization. Sequential, in-memory. |
| VRAMManager | Model lifecycle: load, unload, track VRAM usage |
| Inference | Runs the selected generation model. Returns result tensor. |
| Cache | Redis. Key = SHA256(person_bytes + garment_bytes + category). TTL = 24h. |
| Storage | Local temp directory for results. Signed URLs with expiry. |

## Design Principles

- One process, one GPU, one generation model loaded at a time.
- Preprocessing models stay resident (small). Generation models load on-demand.
- All data flows through in-memory tensors. No intermediate disk I/O.
- Fallback is exception-driven, not polling-driven.
- Every input is normalized to fixed resolution at the API boundary.
- Adapters make generation models swappable without touching pipeline code.

## Cloud Evolution Path (Post-MVP)

When revenue justifies RunPod or dedicated cloud GPUs:

- Split Tier 1 and Tier 2 into separate GPU instances.
- Re-enable progressive delivery (Tier 1 instant, Tier 2 background).
- Add Celery + RabbitMQ for async job queue.
- Add video tier on 24GB+ instances (Lucy 2.0 / CatV2TON).
- Add Nginx/Traefik as reverse proxy + load balancer.
- The modular monolith's internal interfaces become service boundaries.
