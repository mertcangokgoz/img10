"""Constants used throughout the application."""

# File and image processing constants
RGB_MODE = "RGB"
JPEG_QUALITY = 50
DEFAULT_THUMBNAIL_SIZE = (200, 200)
JPEG_FORMAT = "JPEG"
PNG_FORMAT = "PNG"

# File size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Security constants
SECURE_ID_LENGTH = 16

# Rate limiting constants
UPLOAD_RATE_LIMIT = "120/minute"
SERVE_RATE_LIMIT = "10/minute"

# HTTP status codes
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404

# Error messages
ERROR_IMAGE_FILES_ONLY = "Only image files are accepted"
ERROR_FILE_TOO_LARGE = "File size too large. Maximum allowed size is 10MB."
ERROR_IMAGE_NOT_FOUND = "Image not found"
ERROR_IMAGE_EXPIRED = "Image has expired"
ERROR_IMAGE_FILE_NOT_FOUND = "Image file not found"
ERROR_UNSUPPORTED_FORMAT = "Unsupported image format. Only JPEG and PNG are supported."

# Database constants
DATABASE_PATH = "config/images.db"

# Application settings
APP_TITLE = "img10 - Temporary Image Hosting"
APP_DESCRIPTION = "Temporary image hosting service"
