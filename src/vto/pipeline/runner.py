from typing import Literal

from vto.core.normalizer import compute_cache_key, normalize_image
from vto.pipeline.context import TryOnContext


def build_context(
    person_bytes: bytes,
    garment_bytes: bytes,
    category: Literal["upper", "lower", "full"],
    tier: Literal["fast", "hd"],
) -> TryOnContext:
    person_image = normalize_image(person_bytes)
    garment_image = normalize_image(garment_bytes)
    cache_key = compute_cache_key(person_bytes, garment_bytes, category)

    return TryOnContext(
        person_image=person_image,
        garment_image=garment_image,
        category=category,
        cache_key=cache_key,
        tier=tier,
    )
