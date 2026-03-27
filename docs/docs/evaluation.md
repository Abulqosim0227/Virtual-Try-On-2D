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

# Evaluation

Two separate systems: **software tests** (automated, every push) and **ML evaluation** (manual script, on model changes).

## Software Tests (pytest, CI)

Run on every push via GitHub Actions. Must pass before merging.

### 1. Micro Test Set (3 Pairs)

3 tiny (256x256) person-garment pairs embedded in the repo under `tests/fixtures/`. The full pipeline runs on these in seconds — no real model quality assessment, just code path verification.

Tests:
- Preprocessing produces expected output shapes (pose keypoints, parsed mask, garment mask).
- TryOnContext Pydantic validation catches missing fields.
- Generation model produces an output image of correct dimensions.
- Cache hit returns same result without GPU inference.
- VRAM cleanup runs (torch.cuda memory before/after).
- Error paths: bad image format returns 400, missing person returns 422, oversized image returns 413.

### 2. MockVTOModel

A fake generation model that takes inputs and instantly returns a blurred version of the person image. Implements `BaseVTOModel` interface.

Purpose: test the entire web stack (FastAPI routes, auth, rate limiting, Redis caching, job status polling, error handling) at thousands of requests per second without touching the GPU.

```
class MockVTOModel(BaseVTOModel):
    def load(self): pass
    def unload(self): pass
    def generate(self, context): return context.person_image.filter(GaussianBlur(radius=10))
    def vram_estimate_mb(self): return 0
```

### 3. Security Tests

- EXIF metadata stripped from all outputs.
- Oversized images rejected before GPU.
- Rate limiting enforced (429 after threshold).
- API key required on all endpoints except `/v1/health`.
- Temp files cleaned up after request (success and failure paths).
- No PII in structured logs.

### 4. VRAM Cleanup Tests

Assert that every request (success or failure) triggers cleanup:
- Intermediate tensors deleted.
- `torch.cuda.empty_cache()` called.
- Temp files removed.
- VRAM usage after request <= VRAM usage before request (within tolerance).

## ML Evaluation (Manual Script)

Run manually via `scripts/evaluate.py`. Not part of CI — too slow (runs on real models, takes minutes to hours).

### Test Sets

| Set | Size | Purpose | When to Run |
|-----|------|---------|-------------|
| Golden test set | 200 pairs (VITON-HD subset) | Fixed baseline. Regression detection. | Every model update |
| Challenging set | 50 pairs | Edge cases: unusual poses, patterns, accessories | Every model update |
| Uzbek validation | 100 pairs | Local market relevance | After Uzbek dataset collected (Phase 3) |

Download VITON-HD in Phase 1 Day 1. Extract 200 pairs as golden set. Store dataset path in config, never in git.

### Image Quality Metrics

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| SSIM | Structural similarity to ground truth | > 0.85 |
| FID | Distribution quality (lower = better) | < 15 |
| LPIPS | Perceptual similarity (lower = better) | < 0.15 |

### Identity Preservation

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| ArcFace cosine similarity | Face identity preserved after try-on | > 0.90 |
| Skin tone consistency | No color shift on skin areas | Delta E < 3 |

### Garment Fidelity

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| CLIP similarity (garment) | Output garment matches input garment | > 0.85 |
| Pattern preservation | Logos, prints, textures retained | Visual check |
| Edge quality | Clean boundaries, no bleeding | Visual check |

### Human Preference Alignment

Inspired by VTON-VLLM (NeurIPS 2025). Measures how well model output matches what real users prefer, not just pixel-level metrics.

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Pairwise preference rate | % of time users prefer our output over input | > 70% |
| Naturalness score | 1-5 rating of "does this look real?" | > 4.0 |
| Garment-person coherence | 1-5 rating of "does this garment suit this person?" | > 3.5 |

Collect via simple A/B comparison tool (show 2 outputs, user picks better one). Run monthly with 5 evaluators on 20 random outputs.

### Video-Specific (Deferred)

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Temporal consistency | Frame-to-frame stability (no flicker) | TC score > 0.90 |
| Motion artifacts | Ghosting, tearing on movement | < 2% of frames |

Added when video tier is built.

## Performance KPIs

| KPI | Target (MVP, single GPU) |
|-----|--------------------------|
| Tier 1 (fast) p95 response time | < 10s |
| Tier 2 (hd) p95 completion time | < 40s |
| Inference error rate | < 2% |
| Cache hit rate | > 30% (at scale) |
| VRAM leak per request | 0 MB (within tolerance) |

## Business KPIs

| KPI | Target |
|-----|--------|
| Preview-to-cart interaction lift | > 30% |
| User realism feedback score | > 4.2 / 5 |
| Return rate reduction | > 15% |

Measurable only after Uzum/Sello pilot. Not relevant during MVP development.

## Evaluation Schedule

| Frequency | What |
|-----------|------|
| Every push | Software tests (micro set, mock model, security, VRAM cleanup) via GitHub Actions |
| Every model update | Full golden test set via `scripts/evaluate.py` (all image metrics) |
| Monthly | Human preference evaluation (20 random outputs, 5 evaluators) |
| After Uzbek dataset | Full benchmark including challenging set + Uzbek validation |

## Regression Detection

- If any image metric drops > 5% from baseline on the golden set: block deployment.
- Visual diff tool: side-by-side comparison of current vs previous outputs on golden set. Generate HTML report.
- Automated: `scripts/evaluate.py` exits with non-zero code if any metric below threshold.
