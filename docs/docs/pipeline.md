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

# Pipeline

## 3-Stage Processing Engine

One sequential, in-memory pipeline. No threading, no parallelism, no intermediate disk I/O. Every stage reads from and writes to a shared `TryOnContext` object.

## TryOnContext

A Pydantic model that carries all state through the pipeline. Validated at each stage boundary.

```
TryOnContext:
  # Input (set at API boundary)
  person_image: PIL.Image        # RGB, resized to 768x1024
  garment_image: PIL.Image       # RGB, resized to 768x1024
  category: str                  # "upper", "lower", "full"
  cache_key: str                 # SHA256(original_person_bytes + original_garment_bytes + category)
  tier: str                      # "fast" or "hd"

  # Preprocessing outputs (set by Stage 1)
  pose_keypoints: np.ndarray     # DWPose 18-point skeleton
  parsed_mask: np.ndarray        # SCHP human parsing map (18 regions)
  garment_mask: PIL.Image        # Background-removed garment (RMBG-2.0)

  # Synthesis output (set by Stage 2)
  result_image: PIL.Image        # Final try-on result

  # Metadata (set throughout)
  timings: dict                  # Stage-level latency measurements
  model_used: str                # Which generation model ran
```

No raw dictionaries. If a field is missing when a stage needs it, Pydantic raises a validation error caught as `PreprocessingError`.

## Stage 1: Preprocessing

Input: `TryOnContext` with `person_image`, `garment_image`, `category` set.

All models run sequentially on the GPU in fp16. Kept resident in VRAM (~4-5GB total).

| Step | Model | Output | VRAM (fp16) |
|------|-------|--------|-------------|
| Pose estimation | DWPose | 18 keypoints + skeleton image | ~1.5GB |
| Human parsing | SCHP | 18-region segmentation mask | ~1.5GB |
| Garment mask | RMBG-2.0 | Background-removed garment | ~1GB |

Execution order matters — each step adds to the context:

```
context.pose_keypoints = dwpose.predict(context.person_image)
context.parsed_mask = schp.predict(context.person_image)
context.garment_mask = rmbg.predict(context.garment_image)
```

### What is NOT in preprocessing (and why)

| Skipped Step | Reason |
|-------------|--------|
| YOLO person detection | CatVTON and IDM-VTON expect full person images, not crops |
| DensePose | Neither CatVTON nor IDM-VTON community forks require it |
| BlazePose (client-side) | No mobile tier in MVP |
| Explicit garment warping (TPS) | Both MVP models use implicit diffusion-based alignment |

These can be added later via the `BasePreprocessor` adapter when models that need them are integrated.

## Stage 2: Synthesis

The generation model runs. VRAMManager loads the correct model based on `context.tier`.

| Tier | Model | Behavior | Inputs Consumed |
|------|-------|----------|-----------------|
| fast | CatVTON (fp16, resident) | Synchronous, no model swap needed | person, garment, garment_mask, parsed_mask |
| hd | IDM-VTON (accelerate CPU offload) | CatVTON unloaded first, ~2-3s swap | person, garment, garment_mask, pose, parsed_mask |

Both models implement `BaseVTOModel.generate(context) -> PIL.Image`.

```
model = vram_manager.ensure_loaded(context.tier)
context.result_image = model.generate(context)
```

### Adapter Pattern

Every generation model is a subclass of `BaseVTOModel`:

```
class BaseVTOModel(ABC):
    def load(self) -> None: ...
    def unload(self) -> None: ...
    def generate(self, context: TryOnContext) -> PIL.Image: ...
    def vram_estimate_mb(self) -> int: ...
```

Swapping CatVTON for Re-CatVTON, FASHN-VTON, or any future model requires only a new subclass. Zero changes to the router, API, or pipeline.

## Stage 3: Post-Processing + Delivery

| Step | Implementation | When |
|------|---------------|------|
| Color correction | Simple histogram matching against input person | Always |
| Cache result | Redis SET with cache_key, TTL 24h | Always |
| Save result | Local temp directory, generate signed URL with expiry | Always |
| VRAM cleanup | Delete intermediate tensors, `torch.cuda.empty_cache()` | Always (finally block) |
| Temp file cleanup | Scheduled job deletes expired results | Every hour |

### Deferred Post-Processing (Not in MVP)

| Step | Model | When to Add |
|------|-------|-------------|
| Face restoration | GFPGAN | When evaluation metrics show face degradation |
| Image upscaling | Real-ESRGAN | When output resolution needs to exceed 768x1024 |

These will be added as optional pipeline stages behind feature flags when quality metrics justify the VRAM cost.

## Latency Budget (RTX 5070 Ti, Measured + Estimated)

| Component | Tier 1 (fast) | Tier 2 (hd) |
|-----------|---------------|-------------|
| Upload + input normalization | 100-300ms | 100-300ms |
| Preprocessing (sequential) | 500-1000ms | 500-1000ms |
| Model swap | 0ms (resident) | 2000-3000ms |
| Model inference | **7-8s** (measured, 25 steps) | 15-30s (estimated, 50 steps) |
| Post-processing + cache | 100-300ms | 100-300ms |
| **Total** | **~8-10s** | **~18-35s** |

**Measured on RTX 5070 Ti** (March 18, 2026): CatVTON vitonhd checkpoint, fp16, 768x1024.
- 25 steps (Tier 1 default): **7.7s** avg steady-state
- 50 steps: 15.0s avg steady-state
- VRAM peak: 3,660 MB regardless of step count
- Latency scales linearly with steps. 25 steps is the sweet spot for fast tier.

## In-Memory Guarantee

Tensors and PIL images never touch disk during processing. The only disk writes are:

1. Final result image saved to temp directory (for serving via URL).
2. Redis persistence (if configured, optional).

No intermediate masks, pose maps, or warped garments are written to the SSD. This protects SSD lifespan and eliminates disk I/O latency.
