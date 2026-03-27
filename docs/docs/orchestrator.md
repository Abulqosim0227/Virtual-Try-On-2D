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

# Router

## Purpose

The router is a function inside the FastAPI application. It determines which model handles a request based on the endpoint called and the cache state. No separate service, no message broker, no queue.

## Decision Inputs

| Input | Source | Example |
|-------|--------|---------|
| Endpoint | URL path | `/tryon/fast` or `/tryon/hd` |
| Cache hit | Redis lookup by SHA256(person_bytes + garment_bytes + category) | Exact duplicate detected |
| VRAM state | VRAMManager reports which model is loaded | CatVTON resident, IDM-VTON not loaded |

## Routing Logic

```
def route(request):
    cache_key = sha256(request.person_bytes + request.garment_bytes + request.category)

    if redis.exists(cache_key):
        return CacheHitResponse(redis.get(cache_key))

    if request.endpoint == "/tryon/fast":
        vram_manager.ensure_loaded("catvton")
        return run_tier1(request)

    if request.endpoint == "/tryon/hd":
        job = create_job(request, cache_key)
        vram_manager.ensure_loaded("idm_vton")  # unloads Tier 1, loads Tier 2 via accelerate
        result = run_tier2(request)
        vram_manager.ensure_loaded("catvton")    # restore Tier 1 as default
        return complete_job(job, result)
```

## Model Locking

One generation model runs at a time. Concurrent requests must wait.

- An `asyncio.Lock` guards the inference path.
- If a `/tryon/fast` request arrives while Tier 2 is running, it queues in-process (FastAPI async) and executes when the lock releases.
- If the wait exceeds 30s, the request receives a 503 with `Retry-After` header.
- This prevents VRAM conflicts without any external queue infrastructure.

## VRAMManager Lifecycle

```
Startup:
  1. Load preprocessing models (DWPose, SCHP, RMBG) in fp16 → ~4-5GB
  2. Load CatVTON in fp16 → ~4GB
  3. Total VRAM at idle: ~8-9GB of 16GB

/tryon/fast request:
  1. CatVTON already loaded → run inference → return result

/tryon/hd request:
  1. Unload CatVTON from VRAM → free ~4GB
  2. Load IDM-VTON via accelerate CPU offloading (weights in system RAM)
  3. Run inference (active layers stream to VRAM during forward pass)
  4. Unload IDM-VTON
  5. Reload CatVTON as default resident model

Model switch cost: ~2-3s. Acceptable for HD async requests.
```

## Exception-Driven Fallbacks

No health polling. Failures trigger specific exceptions caught by FastAPI handlers.

| Exception | Trigger | HTTP Response | User-Facing Message |
|-----------|---------|---------------|---------------------|
| `CacheHitResponse` | SHA256 match in Redis | 200 + cached result | (transparent to user) |
| `VRAMExhaustedError` | `torch.cuda.OutOfMemoryError` caught | 503 Service Degraded | "Server busy. Try /tryon/fast or retry in 30s." |
| `WorkerTimeoutError` | Inference exceeds 60s | 504 Gateway Timeout | "Request timed out. Please retry." |
| `PreprocessingError` | Person or garment not detected | 422 Unprocessable | "Could not detect person/garment in image." |
| `ModelLoadError` | Model file missing or corrupted | 500 Internal Error | "Service temporarily unavailable." |
| `InvalidInputError` | Bad file type, oversized, corrupt | 400 Bad Request | Specific validation message. |

Every exception logs full context (without image data) for debugging. Every response includes a machine-readable `error_code` field.

## VRAM Cleanup Contract

After every request (success or failure):

1. Delete all intermediate tensors (pose maps, parsed masks, warped garments).
2. Call `torch.cuda.empty_cache()`.
3. Delete any temp files created during the request.
4. Log VRAM usage before and after cleanup.

This runs in a `finally` block. No request leaks GPU memory.

## Cloud Evolution Path

When deployed to multi-GPU cloud (RunPod, dedicated instances):

- Router becomes a standalone orchestrator service with its own queue.
- Progressive delivery re-enabled: Tier 1 returns instantly, Tier 2 runs on separate GPU.
- Celery + RabbitMQ replaces the asyncio.Lock for job management.
- Add device/connection-based routing (mobile → Tier 0, slow connection → lower resolution).
- Add cost policy routing (per-session budget caps).
- Add circuit breaker: 3 failures in 60s → stop routing to that worker for 30s.
- Add dead letter queue: retry once, then notify user of failure.
