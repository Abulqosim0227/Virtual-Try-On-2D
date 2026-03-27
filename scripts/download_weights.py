"""
Download model weights for Virtual Try-On pipeline.

Usage:
    python scripts/download_weights.py --all
    python scripts/download_weights.py --model catvton
    python scripts/download_weights.py --model dwpose
    python scripts/download_weights.py --model schp
    python scripts/download_weights.py --model rmbg

Prerequisites (RTX 5070 Ti / Blackwell):
    pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
"""

import argparse
import sys
from pathlib import Path

WEIGHTS_DIR = Path("weights")

MODELS = {
    "catvton": {
        "repo": "zhengchong/CatVTON",
        "description": "CatVTON — Tier 1 generation model (~4GB fp16)",
    },
    "dwpose": {
        "repo": "yzd-v/DWPose",
        "description": "DWPose — pose estimation (~1.5GB fp16)",
    },
    "schp": {
        "repo": "GoGoDuck912/Self-Correction-Human-Parsing",
        "description": "SCHP — human body parsing (~1.5GB fp16)",
    },
    "rmbg": {
        "repo": "briaai/RMBG-2.0",
        "description": "RMBG-2.0 — background removal (~1GB fp16)",
    },
}


def download_model(name: str) -> None:
    if name not in MODELS:
        print(f"Unknown model: {name}. Available: {', '.join(MODELS.keys())}")
        sys.exit(1)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Install huggingface_hub: pip install huggingface_hub")
        sys.exit(1)

    model = MODELS[name]
    target = WEIGHTS_DIR / name

    if target.exists() and any(target.iterdir()):
        print(f"[skip] {name} already exists at {target}")
        return

    print(f"[download] {model['description']}")
    print(f"  repo: {model['repo']}")
    print(f"  target: {target}")

    target.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=model["repo"],
        local_dir=str(target),
        local_dir_use_symlinks=False,
    )

    print(f"[done] {name} saved to {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download VTO model weights")
    parser.add_argument("--model", type=str, help="Model name to download")
    parser.add_argument("--all", action="store_true", help="Download all models")
    parser.add_argument("--list", action="store_true", help="List available models")
    args = parser.parse_args()

    if args.list:
        for name, info in MODELS.items():
            print(f"  {name:10s} — {info['description']}")
        return

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        for name in MODELS:
            download_model(name)
    elif args.model:
        download_model(args.model)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
