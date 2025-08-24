"""Image upload and sharing service"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.app.core.config import THUMBNAIL_DIR, UPLOAD_DIR

from .api.routes import router

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="img10 - Temporary Image Hosting",
    description="Temporary image hosting service",
)

# Add rate limiting to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/templates")

# Include API routes
app.include_router(router)