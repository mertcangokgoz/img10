"""Pydantic models for data validation."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ImageUploadResponse(BaseModel):
    """Response model for image upload."""

    success: bool = Field(description="Upload success status")
    image_id: str = Field(description="Unique image identifier")
    img_url: str = Field(description="Direct image URL")
    thumbnail_url: str = Field(description="Thumbnail image URL")
    mime_type: str = Field(description="Image MIME type")


class ImageData(BaseModel):
    """Database image data model."""

    id: str = Field(description="Image identifier")
    mime_type: str = Field(description="Image MIME type")
    file_path: str = Field(description="File system path")
    thumbnail_path: str = Field(description="Thumbnail file path")
    created_at: datetime = Field(description="Creation timestamp")


class CleanupResponse(BaseModel):
    """Response model for cleanup operation."""

    message: str = Field(description="Operation message")
    removed_count: int = Field(description="Number of removed images")


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str = Field(description="Error message")
    status_code: int = Field(description="HTTP status code")


class UploadRequest(BaseModel):
    """Upload request validation model."""

    file_size: int = Field(gt=0, le=10 * 1024 * 1024, description="File size in bytes")
    content_type: str = Field(pattern=r"^image/", description="Image MIME type")

    @field_validator("content_type")
    def validate_image_type(cls, v: str) -> str:  # noqa: N805
        """Validate that content type is an image."""
        allowed_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
        ]
        if v not in allowed_types:
            error_msg = f"Content type must be one of: {', '.join(allowed_types)}"
            raise ValueError(error_msg)
        return v


class ImageStats(BaseModel):
    """Image statistics model."""

    total_images: int = Field(description="Total number of images")
    oldest_image: datetime | None = Field(description="Oldest image timestamp")
    newest_image: datetime | None = Field(description="Newest image timestamp")


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service status")
    timestamp: datetime = Field(description="Check timestamp")
    version: str = Field(description="API version")
    database_connected: bool = Field(description="Database connection status")
