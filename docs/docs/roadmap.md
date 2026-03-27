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

# Roadmap

3 phases to first revenue. Everything else is a future backlog item with no committed timeline.

## Phase 1: Working Demo

**Goal:** End-to-end try-on on real images, accessible via web UI.

**Exit criteria:** A non-technical person can open a URL, upload a photo and a garment, and see a try-on result.

### Week 1: Setup + Benchmark

- Initialize git repo, project structure, Python environment.
- Install PyTorch, Diffusers, FastAPI, Redis.
- Download VITON-HD dataset. Extract 200 pairs as golden test set.
- Download CatVTON weights.
- **Benchmark CatVTON on RTX 5070 Ti.** Measure: preprocessing time, inference time, VRAM peak, output quality on 10 VITON-HD pairs. This sets the real baseline for all latency targets.
- Set up GitHub repo + GitHub Actions (pytest on every push).
- Create 3-pair micro test set (256x256) in `tests/fixtures/`.
- Audit CatVTON LICENSE file. Email authors about commercial terms.

### Week 2: Preprocessing Pipeline

- Build TryOnContext Pydantic model.
- Implement BasePreprocessor interface.
- Integrate DWPose (pose estimation, fp16).
- Integrate SCHP (human parsing, fp16).
- Integrate RMBG-2.0 (background removal, fp16).
- Sequential pipeline: person image → pose → parsing → garment mask.
- All in-memory, no intermediate disk I/O.
- pytest: micro test set passes through full preprocessing.

### Week 3-4: CatVTON Integration + API

- Implement BaseVTOModel interface.
- Integrate CatVTON as first model (fp16, torch.compile).
- Build VRAMManager singleton (load/unload, VRAM tracking).
- Build FastAPI server:
  - `POST /v1/tryon/fast` — synchronous Tier 1.
  - `GET /v1/health` — VRAM, loaded models, uptime.
  - Input normalization at boundary (768x1024, EXIF strip, RGB).
  - API key auth (`X-API-Key` header).
  - Rate limiting (slowapi).
  - Structured logging (structlog, no PII).
- Implement MockVTOModel for API testing without GPU.
- Redis caching: SHA256 key on original bytes, 24h TTL.
- NSFW safety-checker (Stable Diffusion, CPU).
- Exception handlers: VRAMExhaustedError, PreprocessingError, InvalidInputError.
- VRAM cleanup in `finally` block.
- pytest: full API integration tests with MockVTOModel.

### Week 5-6: Web UI + End-to-End

- Build basic Next.js web UI:
  - Upload person photo.
  - Upload or select garment.
  - Display result image.
  - Show processing time.
  - Error messages for failed requests.
- End-to-end flow: browser → FastAPI → preprocess → CatVTON → result → browser.
- Run golden test set (200 pairs) via `scripts/evaluate.py`. Record baseline metrics.
- Fix any quality issues found during evaluation.

**Phase 1 deliverable:** Working demo URL (http://rdp-ip:3000) that anyone can use.

## Phase 2: Multi-Model + Production Ready

**Goal:** Two quality tiers, alternative models tested, Docker deployment, licensing secured.

**Exit criteria:** Dockerized app with Tier 1 + Tier 2, commercial licensing for at least one model, load test baseline established.

### Week 7-8: Tier 2 + Model Swapping

- Integrate IDM-VTON as Tier 2 model (accelerate CPU offloading).
- VRAMManager: model swap flow (unload CatVTON → load IDM-VTON → run → restore CatVTON).
- `POST /v1/tryon/hd` — async endpoint, job status polling via `GET /v1/jobs/{id}`.
- asyncio.Lock guarding inference path (prevent concurrent GPU access).
- Router function: endpoint determines tier, cache check first.
- Exception handlers: WorkerTimeoutError, ModelLoadError.
- pytest: Tier 2 path with MockVTOModel.

### Week 9-10: Alternative Model Testing

- Standalone benchmark of each candidate on 10 VITON-HD pairs:
  1. Re-CatVTON — quality improvement over CatVTON?
  2. FASHN-VTON v1.5 — can we skip preprocessing?
  3. VTON-VLLM — human preference alignment.
- CatV2TON video mode test: does it fit in 16GB VRAM? If yes, video roadmap accelerates.
- Compare side-by-side: SSIM, FID, LPIPS, VRAM peak, latency.
- Swap primary Tier 1 model if a candidate beats CatVTON on quality at same VRAM.
- Update models.md with benchmark results.

### Week 11-12: Docker + Load Test + Licensing

- Dockerfile for the FastAPI app.
- Docker Compose: app + Redis + PostgreSQL.
- Load test with locust: establish baseline (requests/sec, p95 latency, max concurrent).
- Secure commercial licensing for at least one model (CatVTON negotiation or permissive alternative).
- If no open model clears licensing: set up fal.ai API fallback, budget confirmed.
- Security review: run through security.md checklist.
- Full golden test set evaluation. Compare against Phase 1 baseline.

**Phase 2 deliverable:** Dockerized app, two quality tiers, licensing cleared, load test baseline.

## Phase 3: First Revenue

**Goal:** Paying customers.

**Exit criteria:** At least one signed contract (pilot or paid) with an Uzbek marketplace.

### Week 13-16: Deploy + Market

- Deploy to RunPod serverless. Same Docker image, more VRAM headroom.
- Domain setup (api.vto.uz). TLS certificate.
- Prepare demo materials for Uzum/Sello meetings.
- Run demo with real Uzbek fashion items.
- Offer free pilot (limited requests) to prove value.
- Monitor: latency, error rate, VRAM usage, cache hit rate in production.

### Week 17-20: Optimize + Scale

- Uzbek dataset collection planning (5K pairs, $3-4K budget).
- SaaS API packaging with billing (per-request pricing).
- Optimize based on production metrics (torch.compile tuning, cache strategy).
- Convert pilot to paid contract.

**Phase 3 deliverable:** Revenue.

## Future Backlog (No Committed Timeline)

These items are valuable but not required for first revenue. Prioritize based on customer feedback and business needs.

| Item | Trigger to Start |
|------|-----------------|
| Progressive delivery (Tier 1 + Tier 2 simultaneous) | Multi-GPU cloud deployment |
| Video try-on (CatV2TON or Lucy 2.0 API) | Customer demand for live try-on |
| Mobile app (React Native / Flutter) | Consumer app validated by B2B traction |
| On-device inference (CoreML / TFLite) | Mobile app built, offline demand confirmed |
| TensorRT optimization | Optimizing cloud inference cost at scale |
| NVIDIA Triton model serving | Serving >100 concurrent users |
| Kubernetes orchestration | Running multiple GPU instances across regions |
| Prometheus + Grafana monitoring | Structured logs insufficient for debugging |
| Uzbek dataset fine-tuning | Dataset collected, base model quality insufficient for local market |
| A/B testing framework | Multiple models in production, need to compare on real users |
| 3D/AR exploration | Customer demand, technology maturity |
| Shopify / WooCommerce plugin | Global SaaS expansion beyond Uzbek market |

## Milestones

| Week | Milestone |
|------|-----------|
| 1 | CatVTON benchmarked on 5070 Ti. Real latency baseline set. |
| 2 | Preprocessing pipeline passing tests. |
| 4 | FastAPI server running with CatVTON. First API-driven try-on. |
| 6 | Web UI working. Non-technical person can demo it. |
| 8 | Tier 2 (IDM-VTON) integrated. Two quality levels available. |
| 10 | Alternative models benchmarked. Best Tier 1 model selected. |
| 12 | Dockerized. Load tested. Licensing secured. |
| 16 | Running on RunPod. Demo meetings with Uzum/Sello. |
| 20 | First paying customer. |
