import numpy as np
import pytest
from PIL import Image

from vto.pipeline.context import TryOnContext
from vto.pipeline.preprocessors.base import BasePreprocessor


class FakePosePreprocessor(BasePreprocessor):
    @property
    def name(self) -> str:
        return "fake_pose"

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def process(self, context: TryOnContext) -> TryOnContext:
        context.pose_keypoints = np.zeros((18, 3), dtype=np.float32)
        return context

    def vram_estimate_mb(self) -> int:
        return 100


class FakeParsingPreprocessor(BasePreprocessor):
    @property
    def name(self) -> str:
        return "fake_parsing"

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def process(self, context: TryOnContext) -> TryOnContext:
        w, h = context.person_image.size
        context.parsed_mask = np.zeros((h, w), dtype=np.uint8)
        return context

    def vram_estimate_mb(self) -> int:
        return 100


class FakeGarmentMaskPreprocessor(BasePreprocessor):
    @property
    def name(self) -> str:
        return "fake_garment_mask"

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def process(self, context: TryOnContext) -> TryOnContext:
        context.garment_mask = context.garment_image.copy()
        return context

    def vram_estimate_mb(self) -> int:
        return 50


def _make_context() -> TryOnContext:
    return TryOnContext(
        person_image=Image.new("RGB", (768, 1024)),
        garment_image=Image.new("RGB", (768, 1024)),
        category="upper",
        cache_key="test",
        tier="fast",
    )


def test_base_preprocessor_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BasePreprocessor()


def test_fake_pose_sets_keypoints():
    pre = FakePosePreprocessor()
    pre.load()
    ctx = pre.process(_make_context())
    assert ctx.pose_keypoints is not None
    assert ctx.pose_keypoints.shape == (18, 3)
    pre.unload()


def test_fake_parsing_sets_mask():
    pre = FakeParsingPreprocessor()
    pre.load()
    ctx = pre.process(_make_context())
    assert ctx.parsed_mask is not None
    assert ctx.parsed_mask.shape == (1024, 768)
    pre.unload()


def test_fake_garment_mask_sets_image():
    pre = FakeGarmentMaskPreprocessor()
    pre.load()
    ctx = pre.process(_make_context())
    assert ctx.garment_mask is not None
    assert ctx.garment_mask.size == (768, 1024)
    pre.unload()


def test_sequential_preprocessing():
    ctx = _make_context()
    assert ctx.pose_keypoints is None
    assert ctx.parsed_mask is None
    assert ctx.garment_mask is None

    preprocessors = [
        FakePosePreprocessor(),
        FakeParsingPreprocessor(),
        FakeGarmentMaskPreprocessor(),
    ]
    for p in preprocessors:
        p.load()
        ctx = p.process(ctx)

    assert ctx.pose_keypoints is not None
    assert ctx.parsed_mask is not None
    assert ctx.garment_mask is not None


def test_preprocessor_name():
    assert FakePosePreprocessor().name == "fake_pose"
    assert FakeParsingPreprocessor().name == "fake_parsing"
    assert FakeGarmentMaskPreprocessor().name == "fake_garment_mask"


def test_preprocessor_vram_estimate():
    assert FakePosePreprocessor().vram_estimate_mb() == 100
    assert FakeParsingPreprocessor().vram_estimate_mb() == 100
    assert FakeGarmentMaskPreprocessor().vram_estimate_mb() == 50
