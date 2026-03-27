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

# Tech Stack

Split into MVP (what we install now) and Deferred (what we add when needed).

## AI / ML (MVP)

| Tool | Purpose |
|------|---------|
| PyTorch 2.0+ | Core ML framework, model inference |
| torch.compile | Free 20-30% speedup, one line of code. Use from Day 1. |
| Diffusers (HuggingFace) | Diffusion model loading (CatVTON, IDM-VTON) |
| accelerate (HuggingFace) | CPU offloading for Tier 2 — weights in system RAM, active layers on GPU |
| DWPose | Server-side pose estimation (18 keypoints) |
| SCHP | Human body parsing (18 regions) |
| RMBG-2.0 | Background removal / garment masking |

## Backend (MVP)

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Primary backend language |
| FastAPI | REST API server (no WebSocket for MVP) |
| Pydantic | Request/response validation, TryOnContext model |
| Redis | Result caching (SHA256 key, 24h TTL) |
| slowapi | In-process rate limiting (30 req/min per IP) |
| SQLAlchemy | Database ORM |
| PostgreSQL | Primary database (users, garments, jobs) |

## Frontend (MVP)

| Tool | Purpose |
|------|---------|
| Next.js / React | Web application framework |
| TypeScript | Type safety |
| TailwindCSS | Styling |

## Infrastructure (MVP)

| Tool | Purpose |
|------|---------|
| Docker | Containerization |
| Docker Compose | Local dev: FastAPI + Redis + PostgreSQL |

That's it. Two containers (app + Redis) plus a PostgreSQL instance. No reverse proxy, no CDN, no orchestration platform.

## Monitoring (MVP)

| Tool | Purpose |
|------|---------|
| Structured logging (structlog) | JSON logs, no PII, VRAM usage per request |
| `/v1/health` endpoint | GPU VRAM, loaded models, Redis status, uptime |
| Sentry | Error tracking (free tier) |

## Development (MVP)

| Tool | Purpose |
|------|---------|
| Git | Version control |
| GitHub | Repository hosting |
| GitHub Actions | CI: run pytest on every push, lint on every PR |
| pytest | Python testing (unit + integration) |
| pytest-asyncio | Async FastAPI endpoint testing |

## Deferred Tech

Added when specific triggers are met. Not installed during MVP.

| Tool | Purpose | When to Add |
|------|---------|-------------|
| TensorRT | 2-4x inference speedup | Cloud optimization phase (optimizing cost, not dev speed) |
| ONNX Runtime | Cross-platform model export | If deploying to non-NVIDIA hardware |
| Celery + RabbitMQ | Async job queue | When multi-GPU cloud deployment enables true async |
| NVIDIA Triton | Model serving at scale | When serving >100 concurrent users |
| Kubernetes | Production orchestration | When running multiple GPU instances |
| Nginx / Traefik | Reverse proxy, load balancer | When running multiple app instances |
| AWS S3 / MinIO | Object storage | When local temp dir is insufficient |
| CloudFront CDN | Result image delivery | When serving users across regions |
| RunPod | Serverless GPU inference | Phase 2: first revenue |
| Prometheus + Grafana | Metrics dashboards | When structured logs are insufficient |
| WebRTC | Live video capture | When video tier is built |
| MediaPipe JS | Client-side pose detection | When mobile / Tier 0 is built |
| Detectron2 (DensePose) | 3D body surface mapping | When a model requiring it is integrated |
| locust / k6 | Load testing | End of Phase 2 for baseline |
| Label Studio | Data annotation | Phase 3: Uzbek dataset collection |
| DVC | Dataset version control | Phase 3: Uzbek dataset collection |
| React Native / Flutter | Mobile app | Deferred indefinitely |
| CoreML / TFLite | On-device inference | Deferred indefinitely |
