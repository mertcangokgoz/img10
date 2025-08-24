from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta

from ..core.config import UPLOAD_DIR, THUMBNAIL_DIR, TIMEOUT_HOURS
from ..core.database import DatabaseManager, get_db
from ..core.utils import generate_secure_id, create_thumbnail
from ..core.rate_limiter import limiter

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")

@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "img_id": None,
        "img_url": None
    })

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_image(
    request: Request, 
    file: UploadFile = File(...),
    database: DatabaseManager = Depends(get_db)
):
    """Upload image"""
    # Check file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are accepted")
    
    # Read file content
    content = await file.read()
    
    # Check file size (10MB = 10 * 1024 * 1024 bytes)
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    if len(content) > max_size:
        raise HTTPException(
            status_code=400, 
            detail=f"File size too large. Maximum allowed size is 10MB. Your file size: {len(content) / (1024*1024):.1f}MB"
        )
    
    # Validate image format and determine extension
    try:
        from PIL import Image as PILImage
        import io
        with PILImage.open(io.BytesIO(content)) as img:
            if img.format not in ['JPEG', 'PNG']:
                raise HTTPException(status_code=400, detail="Only JPEG and PNG formats are supported")
            
            # Determine file extension based on format
            if img.format == 'JPEG':
                file_extension = '.jpg'
            elif img.format == 'PNG':
                file_extension = '.png'
            else:
                file_extension = '.jpg'  # fallback
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    # Generate unique ID
    image_id = generate_secure_id()
    while database.image_exists(image_id):
        image_id = generate_secure_id()
    
    # Save file with proper extension
    image_path = UPLOAD_DIR / f"{image_id}{file_extension}"
    with open(image_path, "wb") as f:
        f.write(content)
    
    # Create thumbnail
    thumbnail_path = THUMBNAIL_DIR / f"{image_id}.jpg"
    create_thumbnail(image_path, thumbnail_path)
    
    # Save to database
    database.add_image(
        image_id=image_id,
        mime_type=file.content_type or "image/jpeg",
        file_path=str(image_path),
        thumbnail_path=str(thumbnail_path)
    )
    
    # Generate URLs
    base_url = str(request.base_url).rstrip('/')
    image_url = f"{base_url}/{image_id}{file_extension}"
    
    # Generate thumbnail URL
    thumbnail_url = f"{base_url}/t/{image_id}.jpg"
    
    # Return JSON response for API
    return JSONResponse({
        "success": True,
        "image_id": image_id,
        "img_url": image_url,
        "thumbnail_url": thumbnail_url,
        "mime_type": file.content_type
    })

@router.get("/{image_id}.{extension}")
@limiter.limit("3/minute")
async def serve_image(
    image_id: str,
    extension: str,
    request: Request,
    database: DatabaseManager = Depends(get_db)
):
    """Serve image with watermark"""
    image_data = database.get_image(image_id)
    if not image_data:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Check if image is expired
    if image_data["created_at"] < datetime.now() - timedelta(hours=TIMEOUT_HOURS):
        raise HTTPException(status_code=404, detail="Image has expired")
    
    image_path = Path(image_data["file_path"])
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(
        path=image_path,
        media_type=image_data["mime_type"],
        headers={"Content-Disposition": "inline"}
    )

@router.get("/t/{image_id}.jpg")
@limiter.limit("3/minute")
async def serve_thumbnail(
    image_id: str,
    request: Request,
    database: DatabaseManager = Depends(get_db)
):
    """Serve thumbnail"""
    image_data = database.get_image(image_id)
    if not image_data:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    # Check if image is expired
    if image_data["created_at"] < datetime.now() - timedelta(hours=TIMEOUT_HOURS):
        raise HTTPException(status_code=404, detail="Image has expired")
    
    thumbnail_path = Path(image_data["thumbnail_path"])
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    
    return FileResponse(
        path=thumbnail_path,
        media_type="image/jpeg",
        headers={"Content-Disposition": "inline"}
    )

@router.get("/tasks/cleanup")
async def cleanup_task(database: DatabaseManager = Depends(get_db)):
    """Clean up old images (for cron job)"""
    removed_count = database.cleanup_old_images()
    return {"message": "Cleanup completed", "removed_count": removed_count}
