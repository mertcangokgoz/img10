"""API routes for image upload and serving."""

import io
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from PIL import Image as PILImage

from src.app.core.config import THUMBNAIL_DIR, TIMEOUT_HOURS, UPLOAD_DIR
from src.app.core.constants import (
    ERROR_FILE_TOO_LARGE,
    ERROR_IMAGE_EXPIRED,
    ERROR_IMAGE_FILE_NOT_FOUND,
    ERROR_IMAGE_FILES_ONLY,
    ERROR_IMAGE_NOT_FOUND,
    ERROR_UNSUPPORTED_FORMAT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    JPEG_FORMAT,
    MAX_FILE_SIZE,
    PNG_FORMAT,
    SERVE_RATE_LIMIT,
    UPLOAD_RATE_LIMIT,
)
from src.app.core.database import DatabaseManager, get_db
from src.app.core.models import (
    CleanupResponse,
    HealthCheck,
    ImageStats,
    ImageUploadResponse,
)
from src.app.core.rate_limiter import limiter
from src.app.core.utils import create_thumbnail, generate_secure_id

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")


def _validate_file_type(content_type: str | None) -> None:
    """Validate file type."""
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ERROR_IMAGE_FILES_ONLY,
        )


def _validate_file_size(content: bytes) -> None:
    """Validate file size."""
    if len(content) > MAX_FILE_SIZE:
        file_size_mb = len(content) / (1024 * 1024)
        detail = f"{ERROR_FILE_TOO_LARGE} Your file size: {file_size_mb:.1f}MB"
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=detail)


def _raise_unsupported_format_error() -> None:
    """Raise error for unsupported image format."""
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail=ERROR_UNSUPPORTED_FORMAT,
    )


def _validate_image_format(content: bytes) -> str:
    """Validate image format and return file extension."""
    try:
        with PILImage.open(io.BytesIO(content)) as img:
            if img.format not in [JPEG_FORMAT, PNG_FORMAT]:
                _raise_unsupported_format_error()

            # Determine file extension based on format
            if img.format == JPEG_FORMAT:
                return ".jpg"
            if img.format == PNG_FORMAT:
                return ".png"
            return ".jpg"  # fallback
    except Exception as err:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        ) from err


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request) -> HTMLResponse:
    """Main page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@router.post("/upload")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_image(
    request: Request,
    file: Annotated[UploadFile, File()],
    database: Annotated[DatabaseManager, Depends(get_db)],
) -> ImageUploadResponse:
    """Upload image."""
    # Check file type
    _validate_file_type(file.content_type)

    # Read file content
    content = await file.read()

    # Check file size
    _validate_file_size(content)

    # Validate image format and determine extension
    file_extension = _validate_image_format(content)

    # Generate unique ID
    image_id = generate_secure_id()
    while database.image_exists(image_id):
        image_id = generate_secure_id()

    # Save file with proper extension
    image_path = UPLOAD_DIR / f"{image_id}{file_extension}"
    image_path.write_bytes(content)

    # Create thumbnail
    thumbnail_path = THUMBNAIL_DIR / f"{image_id}.jpg"
    create_thumbnail(image_path, thumbnail_path)

    # Save to database
    database.add_image(
        image_id=image_id,
        mime_type=file.content_type or "image/jpeg",
        file_path=str(image_path),
        thumbnail_path=str(thumbnail_path),
    )

    # Generate URLs
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/{image_id}{file_extension}"

    # Generate thumbnail URL
    thumbnail_url = f"{base_url}/t/{image_id}.jpg"

    # Return Pydantic model
    return ImageUploadResponse(
        success=True,
        image_id=image_id,
        img_url=image_url,
        thumbnail_url=thumbnail_url,
        mime_type=file.content_type or "image/jpeg",
    )


@router.get("/{image_id}.{extension}")
@limiter.limit(SERVE_RATE_LIMIT)
async def serve_image(
    image_id: str,
    extension: str,
    request: Request,  # noqa: ARG001
    database: Annotated[DatabaseManager, Depends(get_db)],
) -> FileResponse:
    """Serve image."""
    # Validate extension
    allowed_extensions = ["jpg", "jpeg", "png"]
    if not any(extension.lower() == ext for ext in allowed_extensions):
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Invalid file extension",
        )

    image_data = database.get_image(image_id)
    if not image_data:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=ERROR_IMAGE_NOT_FOUND,
        )

    # Check if image is expired
    if image_data.created_at < datetime.now(UTC) - timedelta(
        hours=TIMEOUT_HOURS,
    ):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=ERROR_IMAGE_EXPIRED)

    image_path = Path(image_data.file_path)
    if not image_path.exists():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=ERROR_IMAGE_FILE_NOT_FOUND,
        )

    return FileResponse(
        path=image_path,
        media_type=image_data.mime_type,
        headers={"Content-Disposition": "inline"},
    )


@router.get("/t/{image_id}.jpg")
@limiter.limit(SERVE_RATE_LIMIT)
async def serve_thumbnail(
    image_id: str,
    request: Request,  # noqa: ARG001
    database: Annotated[DatabaseManager, Depends(get_db)],
) -> FileResponse:
    """Serve thumbnail."""
    image_data = database.get_image(image_id)
    if not image_data:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Thumbnail not found",
        )

    # Check if image is expired
    if image_data.created_at < datetime.now(UTC) - timedelta(
        hours=TIMEOUT_HOURS,
    ):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=ERROR_IMAGE_EXPIRED)

    thumbnail_path = Path(image_data.thumbnail_path)
    if not thumbnail_path.exists():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Thumbnail file not found",
        )

    return FileResponse(
        path=thumbnail_path,
        media_type="image/jpeg",
        headers={"Content-Disposition": "inline"},
    )


@router.get("/tasks/cleanup")
async def cleanup_task(
    database: Annotated[DatabaseManager, Depends(get_db)],
) -> CleanupResponse:
    """Clean up old images (for cron job)."""
    removed_count = database.cleanup_old_images()
    return CleanupResponse(
        message="Cleanup completed",
        removed_count=removed_count,
    )


@router.get("/health")
async def health_check(
    database: Annotated[DatabaseManager, Depends(get_db)],
) -> HealthCheck:
    """Health check endpoint."""
    db_connected = database.test_connection()

    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(UTC),
        version="1.0.0",
        database_connected=db_connected,
    )


@router.get("/stats")
async def get_stats(
    database: Annotated[DatabaseManager, Depends(get_db)],
) -> ImageStats:
    """Get image statistics."""
    stats = database.get_stats()
    return ImageStats(**stats)
