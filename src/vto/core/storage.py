import hashlib
import hmac
import time
from pathlib import Path

import structlog
from PIL import Image

from vto.config import settings

logger = structlog.get_logger()


class ResultStorage:
    def __init__(self) -> None:
        self._dir = Path(settings.results_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, image: Image.Image, filename: str) -> Path:
        path = self._dir / filename
        image.save(path, format="JPEG", quality=95)
        logger.info("result_saved", filename=filename)
        return path

    def get_path(self, filename: str) -> Path | None:
        path = self._dir / filename
        if path.exists():
            return path
        return None

    def get_signed_url(self, filename: str, base_url: str) -> str:
        expires_at = int(time.time()) + settings.result_ttl_hours * 3600
        signature = _sign(filename, expires_at)
        return f"{base_url}/results/{filename}?sig={signature}&exp={expires_at}"

    def verify_signature(self, filename: str, signature: str, expires_at: int) -> bool:
        if time.time() > expires_at:
            return False
        expected = _sign(filename, expires_at)
        return hmac.compare_digest(signature, expected)

    def delete(self, filename: str) -> None:
        path = self._dir / filename
        if path.exists():
            path.unlink()
            logger.info("result_deleted", filename=filename)

    def cleanup_expired(self) -> int:
        cutoff = time.time() - settings.result_ttl_hours * 3600
        count = 0
        for path in self._dir.iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                count += 1
        if count > 0:
            logger.info("cleanup_expired", deleted=count)
        return count


def _sign(filename: str, expires_at: int) -> str:
    msg = f"{filename}:{expires_at}".encode("utf-8")
    key = settings.api_key.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]
