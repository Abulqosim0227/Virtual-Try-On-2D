import pytest
from PIL import Image
from pydantic import ValidationError

from vto.pipeline.context import TryOnContext


def _make_image():
    return Image.new("RGB", (10, 10))


def test_valid_context():
    ctx = TryOnContext(
        person_image=_make_image(),
        garment_image=_make_image(),
        category="upper",
        cache_key="abc123",
        tier="fast",
    )
    assert ctx.category == "upper"
    assert ctx.tier == "fast"
    assert ctx.cache_key == "abc123"


def test_all_categories():
    for cat in ("upper", "lower", "full"):
        ctx = TryOnContext(
            person_image=_make_image(),
            garment_image=_make_image(),
            category=cat,
            cache_key="x",
            tier="fast",
        )
        assert ctx.category == cat


def test_both_tiers():
    for tier in ("fast", "hd"):
        ctx = TryOnContext(
            person_image=_make_image(),
            garment_image=_make_image(),
            category="upper",
            cache_key="x",
            tier=tier,
        )
        assert ctx.tier == tier


def test_invalid_category():
    with pytest.raises(ValidationError):
        TryOnContext(
            person_image=_make_image(),
            garment_image=_make_image(),
            category="shoes",
            cache_key="x",
            tier="fast",
        )


def test_invalid_tier():
    with pytest.raises(ValidationError):
        TryOnContext(
            person_image=_make_image(),
            garment_image=_make_image(),
            category="upper",
            cache_key="x",
            tier="ultra",
        )


def test_optional_fields_default_none():
    ctx = TryOnContext(
        person_image=_make_image(),
        garment_image=_make_image(),
        category="upper",
        cache_key="x",
        tier="fast",
    )
    assert ctx.pose_keypoints is None
    assert ctx.parsed_mask is None
    assert ctx.garment_mask is None
    assert ctx.result_image is None
    assert ctx.model_used is None


def test_timings_default_empty():
    ctx = TryOnContext(
        person_image=_make_image(),
        garment_image=_make_image(),
        category="upper",
        cache_key="x",
        tier="fast",
    )
    assert ctx.timings == {}


def test_missing_required_fields():
    with pytest.raises(ValidationError):
        TryOnContext(
            person_image=_make_image(),
            category="upper",
            cache_key="x",
            tier="fast",
        )
