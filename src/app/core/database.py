import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from src.app.core.config import TIMEOUT_HOURS

class DatabaseManager:
    def __init__(self, db_path: str = "config/images.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    mime_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def add_image(self, image_id: str, mime_type: str, file_path: str, thumbnail_path: str) -> None:
        """Add image to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO images (id, mime_type, file_path, thumbnail_path, created_at) VALUES (?, ?, ?, ?, ?)",
                (image_id, mime_type, file_path, thumbnail_path, datetime.now().isoformat())
            )
            conn.commit()
    
    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image data from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM images WHERE id = ?",
                (image_id,)
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                # Convert created_at string to datetime object
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                return data
            return None
    
    def image_exists(self, image_id: str) -> bool:
        """Check if image exists"""
        return self.get_image(image_id) is not None
    
    def cleanup_old_images(self) -> int:
        """Remove images older than TIMEOUT_HOURS"""
        cutoff_time = datetime.now() - timedelta(hours=TIMEOUT_HOURS)
        removed_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            # Get old images
            cursor = conn.execute(
                "SELECT file_path, thumbnail_path FROM images WHERE created_at < ?",
                (cutoff_time,)
            )
            old_images = cursor.fetchall()
            
            # Remove files
            for row in old_images:
                try:
                    Path(row[0]).unlink(missing_ok=True)
                    Path(row[1]).unlink(missing_ok=True)
                    removed_count += 1
                except Exception:
                    pass
            
            # Remove from database
            conn.execute(
                "DELETE FROM images WHERE created_at < ?",
                (cutoff_time,)
            )
            conn.commit()
        
        return removed_count

# Global database instance
db = DatabaseManager()

def get_db() -> DatabaseManager:
    """Dependency to get database instance"""
    return db
