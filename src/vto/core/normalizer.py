import hashlib
import io

from PIL import Image

from vto.api.exceptions import InvalidInputError

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FORMATS = {"JPEG", "PNG"}


def normalize_image(file_bytes: bytes) -> Image.Image:
    if len(file_bytes) > MAX_FILE_SIZE:
        raise InvalidInputError(f"Image exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit")

    try:
        img = Image.open(io.BytesIO(file_bytes))
    except Exception:
        raise InvalidInputError("Could not read image file")

    if img.format not in ALLOWED_FORMATS:
        raise InvalidInputError(f"Unsupported format: {img.format}. Use JPEG or PNG.")

    img = _strip_exif(img)
    img = img.convert("RGB")

    return img


def compute_cache_key(person_bytes: bytes, garment_bytes: bytes, category: str) -> str:
    h = hashlib.sha256()
    h.update(person_bytes)
    h.update(garment_bytes)
    h.update(category.encode("utf-8"))
    return h.hexdigest()


def _strip_exif(img: Image.Image) -> Image.Image:
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    return clean
