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

# API Contract

## Base URL

```
MVP:        http://localhost:8000/v1
Production: https://api.vto.uz/v1
```

## Authentication (MVP)

- API key in `X-API-Key` header. Single key for development, per-client keys for production.
- Rate limiting via slowapi: 30 req/min per IP (default), configurable per key.
- JWT Bearer tokens deferred to production (no user management in MVP).

## Input Normalization

Applied at the API boundary before any ML processing:

1. Validate file type: JPEG or PNG only. Reject everything else (415).
2. Validate file size: max 10MB per image. Reject larger (413).
3. Strip EXIF metadata (privacy: removes GPS, camera info, timestamps).
4. Convert to RGB (drop alpha channel if PNG).
5. Resize and pad to exactly **768x1024** (CatVTON native resolution).
6. Compute cache key: `SHA256(original_person_bytes + original_garment_bytes + category)`.

The cache key is computed on the **original uploaded bytes** before any resizing. This ensures exact duplicate uploads always hit cache, regardless of processing pipeline changes.

## Endpoints

### Try-On Fast (Sync — Tier 1)

```
POST /v1/tryon/fast
Content-Type: multipart/form-data

Fields:
  person_image: file (JPEG/PNG, max 10MB)
  garment_image: file (JPEG/PNG, max 10MB)
  category: string ("upper", "lower", "full")

Response 200:
{
  "success": true,
  "data": {
    "result_url": "http://localhost:8000/results/abc123.jpg?sig=...&exp=1711036200",
    "tier": "fast",
    "model": "catvton",
    "cached": false,
    "processing_ms": 5200,
    "expires_at": "2026-03-18T12:30:00Z"
  },
  "error": null
}
```

### Try-On HD (Async — Tier 2)

```
POST /v1/tryon/hd
Content-Type: multipart/form-data

Fields:
  person_image: file (JPEG/PNG, max 10MB)
  garment_image: file (JPEG/PNG, max 10MB)
  category: string ("upper", "lower", "full")

Response 202:
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "queued",
    "estimated_seconds": 30
  },
  "error": null
}
```

### Job Status (Polling)

```
GET /v1/jobs/{job_id}

Response 200 (processing):
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "processing"
  },
  "error": null
}

Response 200 (completed):
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "completed",
    "result_url": "http://localhost:8000/results/abc123_hd.jpg?sig=...&exp=1711036200",
    "tier": "hd",
    "model": "idm_vton",
    "cached": false,
    "processing_ms": 28400,
    "expires_at": "2026-03-18T13:00:00Z"
  },
  "error": null
}

Response 200 (failed):
{
  "success": false,
  "data": {
    "job_id": "job_abc123",
    "status": "failed"
  },
  "error": {
    "code": "INFERENCE_TIMEOUT",
    "message": "Processing timed out. Please retry."
  }
}
```

Job statuses: `queued` → `processing` → `completed` | `failed`.

### Garment Management

```
POST /v1/garments
Content-Type: multipart/form-data

Fields:
  image: file (JPEG/PNG, max 10MB)
  category: string ("upper", "lower", "full")
  name: string (optional)

Response 201:
{
  "success": true,
  "data": {
    "garment_id": "g_abc123",
    "category": "upper",
    "image_url": "http://localhost:8000/garments/g_abc123.jpg"
  },
  "error": null
}

GET /v1/garments?category=upper&page=1&limit=20

DELETE /v1/garments/{garment_id}
```

### Health Check

```
GET /v1/health

Response 200:
{
  "status": "ok",
  "gpu_vram_used_mb": 8940,
  "gpu_vram_total_mb": 16384,
  "models_loaded": ["dwpose", "schp", "rmbg", "catvton"],
  "redis_connected": true,
  "uptime_seconds": 3600
}
```

## Response Envelope

All responses follow the same structure:

```
{
  "success": bool,
  "data": { ... } | null,
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable description."
  } | null
}
```

## Error Codes

| HTTP | Error Code | Meaning |
|------|------------|---------|
| 400 | `INVALID_REQUEST` | Missing field, bad value, corrupt file |
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 413 | `IMAGE_TOO_LARGE` | File exceeds 10MB |
| 415 | `UNSUPPORTED_FORMAT` | Not JPEG or PNG |
| 422 | `PERSON_NOT_DETECTED` | Preprocessing could not find a person |
| 422 | `GARMENT_NOT_DETECTED` | Preprocessing could not identify garment |
| 429 | `RATE_LIMITED` | Too many requests. `Retry-After` header included. |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_DEGRADED` | GPU busy or VRAM exhausted. `Retry-After` header included. |
| 504 | `INFERENCE_TIMEOUT` | Model inference exceeded 60s |

## Versioning

- URL-based: `/v1/`, `/v2/`.
- Breaking changes get a new version.
- Old versions supported for minimum 6 months after deprecation notice.

## Deferred (Cloud Deployment)

| Feature | Why Deferred |
|---------|-------------|
| WebSocket `/tryon/stream` | Video tier needs 24GB+ VRAM |
| `webhook_url` on `/tryon/hd` | No external webhook infra for MVP |
| JWT Bearer auth | No user management system yet |
| CDN result delivery | Local temp dir sufficient for MVP |
| Progressive delivery header | Requires multi-GPU (see architecture.md) |
