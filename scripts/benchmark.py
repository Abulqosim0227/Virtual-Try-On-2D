"""
Benchmark a VTO model on the current GPU.

Usage:
    python scripts/benchmark.py --model mock --runs 5
    python scripts/benchmark.py --model catvton --runs 10
    python scripts/benchmark.py --model catvton --runs 10 --image path/to/person.jpg

Measures: VRAM peak, latency (min/avg/max), per-stage timing.
"""

import argparse
import io
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import Image

from vto.core.normalizer import compute_cache_key, normalize_image
from vto.core.vram_manager import VRAMManager
from vto.pipeline.context import TryOnContext
from vto.pipeline.models.mock import MockVTOModel


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


def make_context(image_path: str | None, tier: str = "fast") -> TryOnContext:
    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as f:
            raw = f.read()
        person = normalize_image(raw)
    else:
        person = Image.new("RGB", (768, 1024), (180, 140, 100))

    garment = Image.new("RGB", (768, 1024), (50, 100, 200))

    pbuf = io.BytesIO()
    person.save(pbuf, format="JPEG")
    gbuf = io.BytesIO()
    garment.save(gbuf, format="JPEG")

    return TryOnContext(
        person_image=person,
        garment_image=garment,
        category="upper",
        cache_key=compute_cache_key(pbuf.getvalue(), gbuf.getvalue(), "upper"),
        tier=tier,
    )


def benchmark(model_name: str, runs: int, image_path: str | None) -> None:
    import torch

    model = get_model(model_name)
    manager = VRAMManager()
    manager.register_model(model)

    print(f"Model:  {model_name}")
    print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"Runs:   {runs}")
    print()

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    print("Loading model...")
    t = time.monotonic()
    model.load()
    load_time = time.monotonic() - t
    print(f"  Load time: {load_time:.2f}s")

    if torch.cuda.is_available():
        vram_after_load = torch.cuda.memory_allocated() / (1024 * 1024)
        print(f"  VRAM after load: {vram_after_load:.0f} MB")
    print()

    latencies = []
    print(f"Running {runs} inferences...")
    for i in range(runs):
        ctx = make_context(image_path)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t = time.monotonic()

        ctx.result_image = model.generate(ctx)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        elapsed = time.monotonic() - t

        latencies.append(elapsed)
        print(f"  Run {i + 1}/{runs}: {elapsed:.3f}s")

    print()
    print("Results:")
    print(f"  Min latency:  {min(latencies):.3f}s")
    print(f"  Avg latency:  {statistics.mean(latencies):.3f}s")
    print(f"  Max latency:  {max(latencies):.3f}s")
    if len(latencies) > 1:
        print(f"  Std dev:      {statistics.stdev(latencies):.3f}s")

    if torch.cuda.is_available():
        vram_peak = torch.cuda.max_memory_allocated() / (1024 * 1024)
        print(f"  VRAM peak:    {vram_peak:.0f} MB")

    print()
    model.unload()
    manager.cleanup()
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a VTO model")
    parser.add_argument("--model", type=str, default="mock", help="Model name")
    parser.add_argument("--runs", type=int, default=5, help="Number of inference runs")
    parser.add_argument("--image", type=str, default=None, help="Path to test person image")
    args = parser.parse_args()

    benchmark(args.model, args.runs, args.image)


if __name__ == "__main__":
    main()
