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

# Security

## Core Principle

User images are sensitive biometric data. Every design decision defaults to maximum privacy. Person images must not persist longer than necessary — not on disk, not in GPU memory, not in logs.

## Data Retention Policy

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Person images (uploaded) | Deleted after result generated | Never stored beyond processing |
| Person image tensors (GPU) | Deleted in `finally` block after every request | VRAM cleanup prevents data leaking between requests |
| Result images (cached) | 24 hours max | Signed URL expires, hourly cleanup job deletes files |
| Garment images (catalog) | Until deleted by user | User-managed |
| EXIF metadata | 0 seconds | Stripped at API boundary before processing (removes GPS, camera info, timestamps) |

## Access Control (MVP)

| Layer | Method |
|-------|--------|
| API authentication | `X-API-Key` header. Single dev key for MVP, per-client keys for production. |
| Rate limiting | slowapi: 30 req/min per IP (default), configurable per key |
| Health endpoint | No auth required (`/v1/health`) |

### Deferred Access Control

| Layer | When to Add |
|-------|-------------|
| JWT Bearer tokens | When user management system is built |
| Role-based admin access + MFA | When admin dashboard exists |
| B2B scoped API keys | When first B2B contract is signed |

## Data Protection

| Measure | Implementation | MVP Status |
|---------|---------------|------------|
| EXIF stripping | Strip all metadata at API boundary before processing | MVP |
| Input validation | File type (JPEG/PNG), size (<10MB), dimension checks | MVP |
| Image normalization | Resize to 768x1024, convert to RGB at boundary | MVP |
| SQL injection | Parameterized queries only (SQLAlchemy ORM enforced) | MVP |
| XSS | Content-Security-Policy headers, input sanitization | MVP |
| Signed URLs | Time-limited result URLs with expiry parameter | MVP |
| In-transit encryption (TLS 1.3) | Not applicable for localhost. Required when deploying to production domain. | Production |
| At-rest encryption (AES-256) | Not applicable for local temp dir. Required for cloud storage (S3). | Production |

## VRAM Cleanup (Privacy + Stability)

Person image data in GPU memory is a privacy concern — tensors from one user's request must not be readable by the next request.

Every request (success or failure) executes in a `finally` block:

1. Delete all intermediate tensors (pose maps, parsed masks, warped garments).
2. Delete the person image tensor.
3. Call `torch.cuda.empty_cache()` to release VRAM back to the pool.
4. Delete any temp files created during the request.
5. Log VRAM usage before and after cleanup.

This is tested in CI (see evaluation.md VRAM cleanup tests).

## Content Safety

| Check | Model / Method | When | Action | MVP Status |
|-------|---------------|------|--------|------------|
| NSFW detection | Stable Diffusion safety-checker (small, free) | Before processing | Reject with 422 `NSFW_DETECTED` | MVP |
| Garment validation | CLIP zero-shot ("is this clothing?") | Upload time | Reject non-clothing images with 422 | MVP |
| Age estimation | Dedicated model (TBD) | Before processing | Flag if minor detected, restrict output | Phase 2 |

NSFW safety-checker is lightweight (~200MB) and runs on CPU. Does not add meaningful latency. Use from Day 1.

Age estimation is deferred — adds model complexity and false positive risk. For MVP, a terms-of-service checkbox ("I confirm I am 18+") provides basic legal coverage.

## Audit and Monitoring

- All API requests logged via structlog (JSON format).
- **Never log image data** — log request ID, cache key (SHA256 hash), processing time, model used, VRAM usage.
- Failed auth attempts tracked and alerted via Sentry.
- Anomalous usage patterns: sudden spike in requests from one IP = potential abuse. slowapi handles rate limiting.
- Sentry for error tracking (free tier).
- No PII in logs. No file paths containing usernames.

## Compliance Notes

- Uzbekistan data protection laws apply.
- GDPR-style practices even if not legally required — builds trust.
- User consent required before processing any image.
- Right to deletion: user can request all their data removed (person images, results, garments, account).
- Data processing agreement for B2B clients (template needed before Uzum/Sello pilot).
