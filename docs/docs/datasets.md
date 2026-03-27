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

# Datasets

## Phase 1-2: Public Datasets

Use existing public datasets for development and benchmarking. No collection cost.

| Dataset | Size | Content | Use For | When |
|---------|------|---------|---------|------|
| VITON-HD | 13K pairs | Person + upper body garment, 1024x768 | Primary dev/test, golden test set source | Phase 1 Week 1 (download immediately) |
| DressCode | 48K pairs | Upper, lower, full body | Multi-category evaluation when lower/full body added | Phase 2 |
| DeepFashion | 800K images | In-shop + consumer photos | Preprocessing model validation | Phase 2 (if needed) |

VITON-HD is the only required download for Phase 1. DressCode and DeepFashion are useful but not blocking.

## Phase 3: Uzbek Dataset Collection

For fine-tuning models to work better with Uzbek body types, skin tones, and fashion styles. Triggered when base model quality is insufficient for the local market (measured via human preference evaluation).

### Target
- 5,000 person-garment pairs.
- Categories: upper body, lower body, full outfit.
- Mix of men and women, diverse body types.

### Budget
- Estimated: $3,000 - $4,000 total.
- Photographer / studio: ~$1,500.
- Model compensation: ~$1,000.
- Annotation: ~$500-1,000.

### Process
1. Recruit 50-100 volunteers (paid).
2. Photograph each person in 3-5 outfits.
3. Photograph each garment flat-lay (product shot).
4. Annotate with Label Studio (pose, parsing, garment mask).
5. Quality review: reject blurry, bad lighting, incomplete pairs.

### Legal Requirements
- Written consent from every participant.
- Right to withdraw consent and have data deleted.
- Data used only for model training, not published.
- Consent form reviewed by legal.
- Minors excluded.

## Evaluation Datasets

### Micro Test Set (CI — in repo)

3 tiny (256x256) person-garment pairs stored in `tests/fixtures/`. Committed to git. Used by pytest on every push to verify code paths, not model quality.

### ML Evaluation Sets (Manual — not in repo)

Separate from training data. Used by `scripts/evaluate.py` to benchmark model quality.

| Set | Size | Source | Purpose | When Available |
|-----|------|--------|---------|----------------|
| Golden test set | 200 pairs | VITON-HD subset | Fixed baseline. Regression detection. Never changes. | Phase 1 Week 1 |
| Challenging set | 50 pairs | VITON-HD + manual selection | Edge cases: unusual poses, patterns, accessories. | Phase 1 Week 6 |
| Uzbek validation | 100 pairs | Uzbek dataset collection | Local market relevance check. | Phase 3 |

## Data Storage

### MVP (Local)
- Datasets stored on local SSD (2TB NVMe). Path configured via environment variable, never hardcoded.
- No images in git repos (add to `.gitignore`).
- Micro test set (3 pairs, 256x256) is the only exception — small enough to commit.

### Production
- Raw images: encrypted S3 bucket, access-controlled.
- Annotations: version-controlled (DVC).
- Backup: separate encrypted storage.
