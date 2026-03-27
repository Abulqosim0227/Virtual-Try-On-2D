import io

import pytest
from PIL import Image

from vto.api.exceptions import InvalidInputError
from vto.core.normalizer import (
    MAX_FILE_SIZE,
    compute_cache_key,
    normalize_image,
)


def _to_jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_jpeg_returns_rgb():
    raw = _to_jpeg(Image.new("RGB", (400, 600)))
    result = normalize_image(raw)
    assert result.mode == "RGB"


def test_jpeg_preserves_original_size():
    raw = _to_jpeg(Image.new("RGB", (400, 600)))
    result = normalize_image(raw)
    assert result.size == (400, 600)


def test_png_returns_rgb():
    raw = _to_png(Image.new("RGB", (400, 600)))
    result = normalize_image(raw)
    assert result.mode == "RGB"


def test_rgba_converted_to_rgb():
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    raw = _to_png(img)
    result = normalize_image(raw)
    assert result.mode == "RGB"


def test_oversized_file_rejected():
    with pytest.raises(InvalidInputError, match="exceeds"):
        normalize_image(b"x" * (MAX_FILE_SIZE + 1))


def test_invalid_format_rejected():
    with pytest.raises(InvalidInputError, match="Could not read"):
        normalize_image(b"not an image at all")


def test_bmp_format_rejected():
    img = Image.new("RGB", (10, 10))
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    with pytest.raises(InvalidInputError, match="Unsupported format"):
        normalize_image(buf.getvalue())


def test_exif_stripped():
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    raw = _to_jpeg(img)
    result = normalize_image(raw)
    assert not hasattr(result, "_getexif") or result._getexif() is None


def test_cache_key_deterministic():
    a = b"person_bytes"
    b_bytes = b"garment_bytes"
    key1 = compute_cache_key(a, b_bytes, "upper")
    key2 = compute_cache_key(a, b_bytes, "upper")
    assert key1 == key2
    assert len(key1) == 64


def test_cache_key_differs_on_category():
    a = b"same"
    b_bytes = b"same"
    key_upper = compute_cache_key(a, b_bytes, "upper")
    key_lower = compute_cache_key(a, b_bytes, "lower")
    assert key_upper != key_lower


def test_cache_key_differs_on_input():
    key1 = compute_cache_key(b"person_a", b"garment", "upper")
    key2 = compute_cache_key(b"person_b", b"garment", "upper")
    assert key1 != key2
