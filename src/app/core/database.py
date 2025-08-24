"""Database management module."""

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.app.core.config import TIMEOUT_HOURS
from src.app.core.constants import DATABASE_PATH
from src.app.core.models import ImageData

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for image storage."""

    def __init__(self, db_path: str = DATABASE_PATH) -> None:
        """Initialize database manager."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with tables."""
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

    def add_image(
        self,
        image_id: str,
        mime_type: str,
        file_path: str,
        thumbnail_path: str,
    ) -> None:
        """Add image to database."""
        with sqlite3.connect(self.db_path) as conn:
            query = (
                "INSERT INTO images (id, mime_type, file_path, thumbnail_path, "
                "created_at) VALUES (?, ?, ?, ?, ?)"
            )
            conn.execute(
                query,
                (
                    image_id,
                    mime_type,
                    file_path,
                    thumbnail_path,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()

    def get_image(self, image_id: str) -> ImageData | None:
        """Get image data from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM images WHERE id = ?",
                (image_id,),
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                # Convert created_at string to datetime object
                if data.get("created_at"):
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                return ImageData(**data)
            return None

    def image_exists(self, image_id: str) -> bool:
        """Check if image exists."""
        return self.get_image(image_id) is not None

    def cleanup_old_images(self) -> int:
        """Remove images older than TIMEOUT_HOURS."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=TIMEOUT_HOURS)
        removed_count = 0

        with sqlite3.connect(self.db_path) as conn:
            # Get old images
            cursor = conn.execute(
                "SELECT file_path, thumbnail_path FROM images WHERE created_at < ?",
                (cutoff_time,),
            )
            old_images = cursor.fetchall()

            # Remove files
            for row in old_images:
                try:
                    Path(row[0]).unlink(missing_ok=True)
                    Path(row[1]).unlink(missing_ok=True)
                    removed_count += 1
                except (OSError, PermissionError) as err:
                    logger.warning("Failed to remove file: %s", err)

            # Remove from database
            conn.execute(
                "DELETE FROM images WHERE created_at < ?",
                (cutoff_time,),
            )
            conn.commit()

        return removed_count

    def get_stats(self) -> dict[str, Any]:
        """Get image statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Get total count
            cursor = conn.execute("SELECT COUNT(*) FROM images")
            total_images = cursor.fetchone()[0]

            # Get oldest and newest timestamps
            cursor = conn.execute("SELECT MIN(created_at), MAX(created_at) FROM images")
            result = cursor.fetchone()
            oldest_image = None
            newest_image = None

            if result[0] and result[1]:
                oldest_image = datetime.fromisoformat(result[0])
                newest_image = datetime.fromisoformat(result[1])

            return {
                "total_images": total_images,
                "oldest_image": oldest_image,
                "newest_image": newest_image,
            }

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            self._init_db()
        except (sqlite3.Error, OSError):
            return False
        else:
            return True


# Global database instance
db = DatabaseManager()


def get_db() -> DatabaseManager:
    """Dependency to get database instance."""
    return db
