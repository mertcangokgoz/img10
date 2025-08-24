import secrets
from pathlib import Path
from PIL import Image as PILImage

def generate_secure_id() -> str:
    """Generate a secure random ID"""
    return secrets.token_urlsafe(16)

def create_thumbnail(image_path: Path, thumbnail_path: Path, size: tuple = (200, 200)) -> None:
    """Create a thumbnail from an image"""
    with PILImage.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize maintaining aspect ratio
        img.thumbnail(size, PILImage.Resampling.LANCZOS)
        
        # Save thumbnail
        img.save(thumbnail_path, 'JPEG', quality=50)
