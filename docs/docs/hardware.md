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

# Hardware

## Development Machine (RDP)

| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 5070 Ti 16GB VRAM (Blackwell) |
| CPU | Intel i9-14900K |
| RAM | 64GB DDR5 |
| Storage | 2TB NVMe SSD |
| Access | Remote Desktop (RDP) |

This is the only development and inference machine for the entire MVP. All architectural decisions (modular monolith, VRAMManager, sequential inference) are driven by its 16GB VRAM constraint.

### RDP Access Strategy

FastAPI runs directly on the RDP machine. Access the web UI from your local browser by pointing at the RDP machine's IP:

```
http://<rdp-machine-ip>:8000       # API
http://<rdp-machine-ip>:3000       # Web UI (when built)
```

This removes one network hop compared to tunneling through the RDP display. Ensure ports 8000 and 3000 are open on the RDP machine's firewall.

## VRAM Budget (16GB Total)

All models run in fp16. Only one generation model loaded at a time.

### Idle State (Tier 1 Ready)

| Component | VRAM | Source |
|-----------|------|--------|
| CUDA context + PyTorch overhead | ~0.3GB | Measured |
| DWPose (pose estimation) | ~1.5GB | Estimated |
| SCHP (human parsing) | ~1.5GB | Estimated |
| RMBG-2.0 (background removal) | ~1GB | Estimated |
| CatVTON (Tier 1 generation) | **1.8GB** | **Measured** |
| **Total idle** | **~6.1GB of 16GB** | |
| **Free headroom** | **~9.9GB** | |

CatVTON measured at 1,818 MB loaded (fp16) — much less than the original 4GB estimate. Peak during inference: 3,661 MB. This leaves significant headroom for preprocessing models.

### Tier 2 Request (Model Swap)

| Step | VRAM After |
|------|-----------|
| Unload CatVTON | ~5GB (preprocessing only) |
| Load IDM-VTON via accelerate CPU offload | ~5GB + active layers streamed from 64GB system RAM |
| During inference | ~10-12GB peak (estimated) |
| Unload IDM-VTON, reload CatVTON | Back to ~9GB idle |

IDM-VTON uses HuggingFace `accelerate` CPU offloading: full model weights stay in 64GB system RAM, only the active layers move to VRAM during the forward pass. This avoids loading 12GB into 16GB VRAM. Tradeoff: ~30-50% slower inference vs. native GPU, but it works without OOM.

### Hard Limits

| Scenario | Fits? | Notes |
|----------|-------|-------|
| Preprocessing + CatVTON (Tier 1) | Yes | ~6GB idle, ~8GB peak (measured). Very comfortable. |
| Preprocessing + IDM-VTON (Tier 2, accelerate offload) | Yes | ~10-12GB peak, tight but viable |
| Two generation models simultaneously | No | Guaranteed OOM. VRAMManager prevents this. |
| Video models (Lucy 2.0, MagicTryOn) | No | Need 24GB+. Deferred to cloud. |
| CatV2TON video mode | Unknown | Test in Phase 2 — if <16GB, video comes early |

## Performance Optimization Strategy

### Phase 1: torch.compile (Free Speed)

```python
model = torch.compile(model)
```

One line of code. PyTorch 2.0+ fuses operations and optimizes the computation graph. Expected 20-30% speedup on the 5070 Ti's Blackwell architecture. No configuration, no export step, no compatibility issues with diffusion models.

Use this from Day 1.

### Phase 2: fp16 Everywhere (Already Planned)

All models loaded with `torch.float16`. The 5070 Ti has dedicated FP16 Tensor Cores that run 2x faster than FP32. Also halves VRAM usage.

### Deferred: TensorRT

TensorRT can give 2-4x additional speedup but:
- Painful to set up for dynamic shapes (diffusion models have variable denoising steps).
- Brittle — breaks on PyTorch/CUDA version updates.
- Requires exporting each model individually.
- Kills development velocity during MVP.

Defer to cloud optimization phase when you're optimizing inference cost at scale, not development speed.

## Production Strategy

### Phase 1: MVP (Current)
- All development and inference on the RDP desktop.
- Zero cloud cost.
- Single user / demo capable.

### Phase 2: First Revenue
- Move inference to **RunPod serverless** ($0.30/hr per GPU).
- Scales to zero when idle — no cost when no users.
- Same Docker image, same code. VRAMManager still works but with more headroom on cloud GPUs (A100 40GB / A6000 48GB).
- Desktop becomes local testing only.

### Phase 3: Growth
- Dedicated cloud GPU instances for consistent load.
- Separate Tier 1 and Tier 2 on different GPU instances.
- Re-enable progressive delivery (see architecture.md cloud evolution path).
- Consider reserved instances for cost savings.
