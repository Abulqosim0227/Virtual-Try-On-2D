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

# Models

## Core Try-On Models

| Model | Tier | Speed | VRAM | Key Strength | Status | License | Commercial Use |
|-------|------|-------|------|-------------|--------|---------|----------------|
| CatVTON | Tier 1 | Fast (~11s*) | <8GB | 899M params, lightweight. ICLR 2025 (accepted). | Active (commits Dec 2025) | CC BY-NC-SA 4.0 | No — requires negotiation |
| CatV2TON | Tier 1 / Video | Fast | <8GB | CatVTON update (Feb 2025). Adds video try-on support on top of image. | New | CC BY-NC-SA 4.0 | No — requires negotiation |
| Re-CatVTON | Tier 1 | Fast | <8GB | Rethink of CatVTON garment conditioning. Single UNet, efficient. Dec 2025. | New | Check repo | Unverified — audit needed |
| FASHN-VTON v1.5 | Tier 1 | Fast | ~8GB | Open-sourced early 2025. No pose/parsing preprocessing needed. SOTA at release. | Active | Check repo | Unverified — possibly permissive |
| FastFit | Tier 1 | Fast | ~8GB | Encode garment once, 3.5x faster on repeat. | Research | Research | No |
| VTON-VLLM | Tier 1/2 | Medium | ~8-10GB | NeurIPS 2025. Human preference alignment. Closes research-commercial gap. | New (public code) | Check repo | Unverified — audit needed |
| IDM-VTON | Tier 2 | Slow (~17s*) | ~12GB | Best detail (GarmentNet). ECCV 2024 (published). Community forks run on 8GB. | Frozen (stable since early 2025) | CC BY-NC-SA 4.0 | No — requires negotiation |
| RefVTON | Tier 2 | Medium | ~10GB | End-to-end with visual reference. Flux-based backbone. LoRA weights. Code Oct 2025. | New | Check repo | Unverified — audit needed |
| OOTDiffusion | Tier 2 | Slow | ~12GB | AAAI 2025 version. End-to-end diffusion pipeline. | Active | Research | No |
| DualFit | Tier 2 | Medium | ~10GB | Warp + synthesis fidelity. ICCV 2025 (published). | Research | Research | No |

*Speed estimates from original papers, not benchmarked on RTX 5070 Ti. First Phase 1 task is real benchmarking.

## Supporting Models (MVP)

Only models required by CatVTON and IDM-VTON. All run in fp16, kept resident in VRAM.

| Model | Purpose | VRAM (fp16) | MVP Status |
|-------|---------|-------------|------------|
| DWPose | Pose estimation (18 keypoints, server-side) | ~1.5GB | Required |
| SCHP | Human body parsing (18 regions) | ~1.5GB | Required |
| RMBG-2.0 | Background removal / garment masking | ~1GB | Required |

### Deferred Supporting Models

| Model | Purpose | When to Add |
|-------|---------|-------------|
| GFPGAN | Face restoration post-process | When evaluation shows face degradation |
| Real-ESRGAN | Image upscaling post-process | When output needs to exceed 768x1024 |
| DensePose | 3D body surface mapping | When a model requiring it is integrated |
| MediaPipe BlazePose | Browser-side pose detection | When mobile/Tier 0 is built |
| Mask2Former / OneFormer | Alternative human parsing | When SCHP proves insufficient for Uzbek body types |

## Evaluated but Rejected

| Model | Reason |
|-------|--------|
| OutfitAnyone (HumanAIGC) | No open weights, no code, demo only, non-commercial. |
| DM-VTON | Tier 0 / on-device. Deferred until mobile phase. |
| Mobile-VTON | Tier 0 / on-device. Deferred until mobile phase. |
| DS-VTON | Multi-scale detail preservation but no clear advantage over DualFit. |

## Video Models (Deferred — Requires 24GB+ VRAM)

| Model | Speed | VRAM | License | Notes |
|-------|-------|------|---------|-------|
| Lucy 2.0 | 30 FPS | 24GB+ | Commercial API (fal.ai) | Pay-per-use, no local deployment |
| MagicTryOn | Real-time | 24GB+ | Research (CC BY-NC-SA 4.0) | Coarse-to-fine DiT architecture |
| CatV2TON | TBD | <8GB? | CC BY-NC-SA 4.0 | If video mode fits in 8GB, test early — could eliminate need for 24GB models |

CatV2TON is the wildcard. If its video capability runs on 16GB VRAM, it compresses the video roadmap significantly. Test in Phase 2.

## Licensing Reality Check

**The hard truth:** Almost no strong open-weight VTO model is commercially usable today.

| License Status | Models |
|---------------|--------|
| Non-commercial (CC BY-NC-SA 4.0) | CatVTON, CatV2TON, IDM-VTON, MagicTryOn |
| Research / Academic only | FastFit, OOTDiffusion, DualFit |
| Unverified — must audit repo LICENSE file | Re-CatVTON, FASHN-VTON v1.5, VTON-VLLM, RefVTON |
| Commercial API (pay-per-use) | Lucy 2.0 (fal.ai) |

### Action Items (Before Phase 2 Revenue Conversations)

1. **Audit licenses** of Re-CatVTON, FASHN-VTON v1.5, VTON-VLLM, RefVTON. Check actual LICENSE file in each repo, not just paper headers.
2. **Contact CatVTON authors** about commercial licensing terms. Many academic teams are open to it.
3. **Budget $1-5K** for commercial API fallback (fal.ai Lucy or similar) if no open model clears licensing.
4. **Track in a spreadsheet:** model, license type, commercial OK (yes/no), author contact, date checked, response.

Launching a paid SaaS on CC BY-NC-SA 4.0 models without a commercial license is illegal. This is the #1 business risk (see risks.md).

## MVP Evaluation Order

Test these models in Phase 1-2 in this order. Goal: find the best model that fits on 16GB VRAM.

1. **CatVTON** — Primary MVP model. Best documented, active community, known to work.
2. **Re-CatVTON** — If it improves on CatVTON quality with same VRAM, swap in.
3. **FASHN-VTON v1.5** — No preprocessing needed (skips pose/parsing). If quality matches, simplifies the pipeline.
4. **VTON-VLLM** — Human preference alignment. Most relevant for business KPIs (user satisfaction).

Each gets a standalone benchmark: load model, run 10 VITON-HD pairs, measure SSIM/FID/LPIPS, measure VRAM peak, measure latency. Compare side-by-side before committing to a primary model.
