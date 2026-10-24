from pathlib import Path

from app.core.config import settings


def _resolve_upload_root() -> Path:
    if settings.UPLOAD_ROOT:
        return Path(settings.UPLOAD_ROOT).expanduser().resolve()
    # backend/app/core/paths.py -> repository root (local development)
    return Path(__file__).resolve().parents[3] / "uploads"


UPLOAD_ROOT = _resolve_upload_root()
