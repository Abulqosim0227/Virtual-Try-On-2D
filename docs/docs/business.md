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

# Business Model

## Target Market

### Primary: Uzbekistan E-Commerce
- Uzum, Sello, and other local marketplaces.
- Fashion retail growing rapidly, but high return rates due to sizing uncertainty.
- No local competitor offers virtual try-on.

### Secondary: Global SaaS
- API product for any e-commerce store worldwide.
- Shopify / WooCommerce plugin potential.

## Revenue Streams

| Model | Pricing | Target Customer |
|-------|---------|----------------|
| SaaS API (per request) | $0.05 - $0.20 / try-on | E-commerce stores, developers |
| White-label deployment | $500 - $2,000 / month | Major marketplaces (Uzum, Sello) |
| Consumer app (freemium) | Free tier + $5-10/month premium | End users |
| E-commerce commission | 3-5% per sale via try-on | Partner stores |

## Value Proposition

### For Stores
- Reduce return rates (target: -15%+).
- Increase conversion (target: +30% preview-to-cart lift).
- Differentiate from competitors.

### For Users
- Try before you buy — see how clothes look on you.
- Save time, reduce disappointment.
- HD export, outfit history, social sharing (premium).

## Prerequisites Before Revenue Conversations

These must be true before approaching Uzum, Sello, or any paying customer:

1. **Commercial model secured.** At least one generation model must be legally usable for commercial purposes. Options:
   - Negotiate commercial license with CatVTON authors.
   - Confirm a permissive license on Re-CatVTON, FASHN-VTON v1.5, VTON-VLLM, or RefVTON.
   - Fall back to commercial API (fal.ai Lucy, $1-5K budget).
2. **Working demo.** End-to-end try-on on real images, accessible via URL. Not a Jupyter notebook — a web page a product manager can use.
3. **Quality baseline.** SSIM > 0.85, FID < 15 on VITON-HD test set. Side-by-side comparison ready for demo meetings.

Do not schedule meetings with marketplace teams until all 3 are met. Demoing on non-commercial models is fine for R&D, but signing contracts requires cleared licensing.

## Cost Structure (MVP Phase)

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| Development | $0 | Own time + own hardware (RTX 5070 Ti) |
| Cloud GPU (RunPod) | $0 during dev, ~$50-200 at launch | Scales to zero when idle |
| Domain + hosting | ~$10-20 | |
| Model licensing (one-time or annual) | $0-5,000 | Depends on negotiation outcome |
| Commercial API fallback (fal.ai) | ~$50-200/month if needed | Only if no open model clears licensing |
| **Total MVP** | **~$10-20/month** (dev) | **~$100-400/month** (launch) |

## Go-to-Market

1. Build working demo with real results on commercially-cleared model.
2. Secure commercial licensing for at least one Tier 1 model (see models.md action items).
3. Approach Uzbek marketplace teams with demo + licensing proof.
4. Offer free pilot (limited requests) to prove value.
5. Convert to paid white-label or API contract.
6. Launch consumer-facing app once B2B validates the tech.
