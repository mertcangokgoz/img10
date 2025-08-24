"""Utility functions for image processing."""

import secrets
from pathlib import Path

from PIL import Image as PILImage

from src.app.core.constants import (
    DEFAULT_THUMBNAIL_SIZE,
    JPEG_QUALITY,
    RGB_MODE,
    SECURE_ID_LENGTH,
)


def generate_secure_id() -> str:
    """Generate a secure random ID."""
    return secrets.token_urlsafe(SECURE_ID_LENGTH)


def create_thumbnail(
    image_path: Path,
    thumbnail_path: Path,
    size: tuple[int, int] = DEFAULT_THUMBNAIL_SIZE,
) -> None:
    """Create a thumbnail from an image maintaining aspect ratio."""
    with PILImage.open(image_path) as img:
        # Convert to RGB if necessary
        img_rgb = img.convert(RGB_MODE) if img.mode != RGB_MODE else img

        img_rgb.thumbnail(size, PILImage.Resampling.LANCZOS)

        img_rgb.save(thumbnail_path, "JPEG", quality=JPEG_QUALITY)
