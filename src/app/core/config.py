from pathlib import Path

# Configuration
UPLOAD_DIR = Path("uploads")
THUMBNAIL_DIR = Path("thumbnails")
TIMEOUT_HOURS = 24  # Images expire after 24 hours

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)
