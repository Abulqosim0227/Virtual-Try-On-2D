# STILAR - AI Virtual Try-On

<div align="center">

**See how clothes look on you before you buy.**

AI-powered virtual fitting room for e-commerce. Upload a photo, select a garment, get a photorealistic try-on in seconds.

[Live Demo](#quick-start) | [API Docs](#api) | [Architecture](#architecture) | [Reports](reports/)

</div>

---

## What It Does

Upload a person photo and a garment image. STILAR generates a photorealistic result showing the person wearing the garment. The system handles pose estimation, body segmentation, garment alignment, and diffusion-based synthesis automatically.

**Input:** Person photo + Garment photo
**Output:** Photorealistic try-on result (768x1024)
**Time:** ~15 seconds per try-on on RTX 5070 Ti

## Key Features

- **CatVTON Pipeline** (ICLR 2025) - Concatenation-based virtual try-on with SD 1.5 inpainting
- **DensePose + SCHP + OpenPose** - Triple-model masking for accurate body segmentation
- **FastAPI Backend** - REST API with caching, rate limiting, signed URLs
- **Next.js Frontend** (STILAR) - Dark premium UI with drag-and-drop upload
- **ComfyUI Workflow** - Node-based pipeline for advanced users
- **Single GPU Optimized** - Runs on 16GB VRAM (RTX 5070 Ti)

## Architecture

```
[Browser UI]  -->  [FastAPI Server]  -->  [Pipeline]
                        |                     |
                   [Redis Cache]    [DensePose + SCHP + OpenPose]
                        |                     |
                   [Result Storage]     [CatVTON (bf16)]
                                              |
                                        [Result Image]
```

### Pipeline Flow

```
Person Photo + Garment
        |
   Input Normalization (validate, EXIF strip, RGB)
        |
   Auto Mask Generation
   ├── DensePose (detectron2) --> body surface regions
   ├── SCHP ATR + LIP --> clothing/body parsing
   └── OpenPose --> arm keypoints (safety net)
        |
   CatVTON Inference (mix checkpoint, bf16, 50 steps)
        |
   Result Image (768x1024)
```

### VRAM Budget (16GB RTX 5070 Ti)

| Component | VRAM |
|-----------|------|
| CatVTON (bf16) | 1,818 MB |
| SCHP (ATR + LIP) | 516 MB |
| DensePose | 257 MB |
| **Total loaded** | **2,590 MB** |
| **Peak during inference** | **4,433 MB** |
| **Free headroom** | **11.6 GB** |

## Tech Stack

### Backend
| Tool | Purpose |
|------|---------|
| Python 3.11+ | Primary language |
| FastAPI | REST API server |
| PyTorch 2.9+ (CUDA 12.8) | ML framework |
| Diffusers (HuggingFace) | CatVTON pipeline |
| detectron2 | DensePose body mapping |
| controlnet_aux | OpenPose keypoints |
| Redis | Result caching (SHA256 dedup) |
| Pydantic | Request/response validation |
| structlog | Structured JSON logging |

### Frontend
| Tool | Purpose |
|------|---------|
| Next.js 15 | React framework |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| shadcn/ui | UI components |
| Framer Motion | Animations |
| react-dropzone | File upload |

### ML Models
| Model | Purpose | VRAM |
|-------|---------|------|
| CatVTON (mix-48k-1024) | Try-on generation | 1.8 GB |
| DensePose (R-50-FPN) | Body surface mapping | 257 MB |
| SCHP (ATR) | Human parsing (18 classes) | ~260 MB |
| SCHP (LIP) | Human parsing (20 classes) | ~260 MB |
| OpenPose | Arm keypoint detection | CPU |

## Quick Start

### Prerequisites
- NVIDIA GPU with 16GB+ VRAM
- Python 3.10+
- PyTorch with CUDA support
- Node.js 18+
- Redis (optional, for caching)

### 1. Clone & Install

```bash
git clone https://github.com/Abulqosim0227/Virtual-Try-On-2D.git
cd Virtual-Try-On-2D

# Python dependencies
pip install -e ".[ml,dev]"

# Download model weights
python scripts/download_weights.py --all

# Web UI
cd web && npm install && cd ..
```

### 2. RTX 5070 Ti / Blackwell GPU

If using RTX 5070 Ti or newer Blackwell GPU, install PyTorch nightly:

```bash
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
```

### 3. Install detectron2 (for DensePose)

```bash
pip install 'git+https://github.com/facebookresearch/detectron2.git'
```

### 4. Run

```bash
# Start backend (port 8899)
PYTHONPATH=src uvicorn vto.main:app --host 0.0.0.0 --port 8899

# Start frontend (port 3000)
cd web && npm run dev
```

Open `http://localhost:3000` in your browser.

## API

### Try-On (Sync)

```bash
curl -X POST http://localhost:8899/v1/tryon/fast \
  -H "X-API-Key: changeme-generate-a-real-key" \
  -F "person_image=@person.jpg" \
  -F "garment_image=@garment.jpg" \
  -F "category=upper"
```

Response:
```json
{
  "success": true,
  "data": {
    "result_url": "http://localhost:8899/results/abc123_fast.jpg?sig=...&exp=...",
    "tier": "fast",
    "model": "catvton",
    "cached": false,
    "processing_ms": 15200,
    "expires_at": "2026-03-28T12:00:00Z"
  }
}
```

### All Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/tryon/fast` | Sync try-on (Tier 1, ~15s) |
| POST | `/v1/tryon/hd` | Async HD try-on (Tier 2) |
| GET | `/v1/jobs/{job_id}` | Poll job status |
| POST | `/v1/garments` | Upload garment |
| GET | `/v1/garments` | List garments |
| DELETE | `/v1/garments/{id}` | Delete garment |
| GET | `/v1/health` | System health + VRAM |

## Project Structure

```
Virtual-Try-On-2D/
├── src/vto/                    # Backend Python package
│   ├── api/                    # FastAPI routes, schemas, middleware
│   ├── core/                   # Cache, storage, VRAM manager, router
│   ├── pipeline/               # ML pipeline
│   │   ├── models/             # CatVTON, IDM-VTON, mock
│   │   │   └── catvton_lib/    # CatVTON pipeline + masking
│   │   └── preprocessors/      # DWPose, SCHP, RMBG
│   └── db/                     # SQLAlchemy models
├── web/                        # Next.js frontend (STILAR)
│   └── src/components/         # React components
├── tests/                      # 58 tests (unit + integration)
├── scripts/                    # Benchmark, evaluate, download weights
├── docs/                       # 14 spec documents
├── reports/                    # 16 daily progress reports
└── .github/workflows/          # CI pipeline
```

## Testing

```bash
PYTHONPATH=src pytest tests/ -v
```

58 tests covering:
- TryOnContext validation
- Input normalization (EXIF strip, format validation)
- Cache operations (Redis graceful degradation)
- API endpoints (auth, try-on, garments, health)
- Error handling (400, 401, 413, 422, 429, 503)
- Preprocessor interfaces

## ComfyUI Support

CatVTON workflow available for ComfyUI with custom nodes:
- `LoadCatVTONPipeline` - Load the try-on model
- `LoadAutoMasker` - Load DensePose + SCHP masking
- `AutoMasker` - Generate agnostic mask
- `CatVTON` - Run virtual try-on

## Target Market

**Primary:** Uzbekistan e-commerce (Uzum, Sello)
**Secondary:** Global SaaS API

Reduce return rates by 15%+, increase conversion by 30%+ with virtual try-on.

## Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| Phase 1 | Working 2D demo | Done |
| Phase 2 | Multi-model + Docker | In Progress |
| Phase 3 | First revenue | Planned |
| Future | 3D try-on, video, mobile | Research |

## License

CatVTON model weights: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (non-commercial).
Commercial use requires separate licensing — see [risks documentation](docs/docs/risks.md).

## Team

Built by a 3-person team in Tashkent, Uzbekistan.

---

<div align="center">
<sub>Powered by CatVTON (ICLR 2025), DensePose, SCHP, OpenPose</sub>
</div>
