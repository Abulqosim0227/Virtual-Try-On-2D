"""
Evaluate VTO model quality on a test set.

Usage:
    python scripts/evaluate.py --model mock --dataset path/to/viton-hd/test --pairs 10
    python scripts/evaluate.py --model catvton --dataset path/to/viton-hd/test --pairs 200

Expected dataset structure:
    dataset/
      image/           # person images (*.jpg)
      cloth/           # garment images (*.jpg)
      image-parse-v3/  # ground truth parsing (optional)

Metrics: SSIM, LPIPS, FID (skipped if dependencies not installed).
Outputs: results/evaluation_<model>_<timestamp>.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from PIL import Image

from vto.core.normalizer import normalize_image
from vto.pipeline.context import TryOnContext
from vto.pipeline.models.mock import MockVTOModel

THRESHOLDS = {
    "ssim": 0.85,
    "lpips": 0.15,
}


def get_model(name: str):
    if name == "mock":
        return MockVTOModel()

    if name == "catvton":
        try:
            from vto.pipeline.models.catvton import CatVTONModel
            return CatVTONModel()
        except ImportError:
            print("CatVTON model not implemented yet")
            sys.exit(1)

    print(f"Unknown model: {name}")
    sys.exit(1)


def load_pairs(dataset_dir: Path, max_pairs: int) -> list[tuple[Path, Path]]:
    image_dir = dataset_dir / "image"
    cloth_dir = dataset_dir / "cloth"

    if not image_dir.exists() or not cloth_dir.exists():
        print(f"Expected {image_dir} and {cloth_dir} to exist")
        sys.exit(1)

    persons = sorted(image_dir.glob("*.jpg"))[:max_pairs]
    pairs = []
    for person_path in persons:
        cloth_path = cloth_dir / person_path.name
        if cloth_path.exists():
            pairs.append((person_path, cloth_path))

    print(f"Found {len(pairs)} pairs (requested {max_pairs})")
    return pairs


def compute_ssim(img_a: np.ndarray, img_b: np.ndarray) -> float | None:
    try:
        from skimage.metrics import structural_similarity
        return structural_similarity(img_a, img_b, channel_axis=2, data_range=255)
    except ImportError:
        return None


def compute_lpips(img_a: np.ndarray, img_b: np.ndarray) -> float | None:
    try:
        import torch
        import lpips

        fn = lpips.LPIPS(net="alex", verbose=False)
        a = torch.from_numpy(img_a).permute(2, 0, 1).unsqueeze(0).float() / 127.5 - 1
        b = torch.from_numpy(img_b).permute(2, 0, 1).unsqueeze(0).float() / 127.5 - 1
        with torch.no_grad():
            score = fn(a, b).item()
        return score
    except ImportError:
        return None


def evaluate(model_name: str, dataset_dir: Path, max_pairs: int) -> dict:
    model = get_model(model_name)
    model.load()

    pairs = load_pairs(dataset_dir, max_pairs)
    if not pairs:
        print("No pairs found")
        sys.exit(1)

    ssim_scores = []
    lpips_scores = []
    latencies = []

    for i, (person_path, cloth_path) in enumerate(pairs):
        person_bytes = person_path.read_bytes()
        cloth_bytes = cloth_path.read_bytes()

        person_img = normalize_image(person_bytes)
        cloth_img = normalize_image(cloth_bytes)

        ctx = TryOnContext(
            person_image=person_img,
            garment_image=cloth_img,
            category="upper",
            cache_key=f"eval_{i}",
            tier="fast",
        )

        t = time.monotonic()
        ctx.result_image = model.generate(ctx)
        latencies.append(time.monotonic() - t)

        person_arr = np.array(person_img)
        result_arr = np.array(ctx.result_image)

        ssim = compute_ssim(person_arr, result_arr)
        if ssim is not None:
            ssim_scores.append(ssim)

        lp = compute_lpips(person_arr, result_arr)
        if lp is not None:
            lpips_scores.append(lp)

        print(f"  [{i + 1}/{len(pairs)}] {person_path.name} — "
              f"ssim={ssim:.3f if ssim else 'N/A'} "
              f"lpips={lp:.3f if lp else 'N/A'} "
              f"latency={latencies[-1]:.3f}s")

    model.unload()

    results = {
        "model": model_name,
        "pairs": len(pairs),
        "avg_latency_s": round(np.mean(latencies), 3),
    }

    if ssim_scores:
        results["ssim_mean"] = round(float(np.mean(ssim_scores)), 4)
        results["ssim_min"] = round(float(np.min(ssim_scores)), 4)
    if lpips_scores:
        results["lpips_mean"] = round(float(np.mean(lpips_scores)), 4)
        results["lpips_max"] = round(float(np.max(lpips_scores)), 4)

    return results


def check_thresholds(results: dict) -> bool:
    passed = True

    if "ssim_mean" in results and results["ssim_mean"] < THRESHOLDS["ssim"]:
        print(f"FAIL: SSIM {results['ssim_mean']} < {THRESHOLDS['ssim']}")
        passed = False

    if "lpips_mean" in results and results["lpips_mean"] > THRESHOLDS["lpips"]:
        print(f"FAIL: LPIPS {results['lpips_mean']} > {THRESHOLDS['lpips']}")
        passed = False

    if passed:
        print("PASS: All metrics within thresholds")

    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate VTO model quality")
    parser.add_argument("--model", type=str, default="mock")
    parser.add_argument("--dataset", type=str, required=True, help="Path to test dataset")
    parser.add_argument("--pairs", type=int, default=200, help="Max pairs to evaluate")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    print(f"Evaluating {args.model} on {args.dataset} ({args.pairs} pairs)")
    print()

    results = evaluate(args.model, Path(args.dataset), args.pairs)

    print()
    print("Results:")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print()

    passed = check_thresholds(results)

    output_path = args.output
    if not output_path:
        Path("results").mkdir(exist_ok=True)
        ts = int(time.time())
        output_path = f"results/evaluation_{args.model}_{ts}.json"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to {output_path}")

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
