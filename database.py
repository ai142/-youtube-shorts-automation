"""
SQLite database for tracking uploads and preventing duplicates.
"""
import asyncio
import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import config

class Database:
    """SQLite database for upload tracking."""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Initialize database connection and create tables."""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
    
    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist."""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                youtube_video_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                hashtags TEXT,
                category TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                uploaded_at TEXT,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                error_message TEXT
            )
        ''')
        
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await self._connection.commit()
    
    async def add_upload(self, video_id: str, title: str, description: str,
                        hashtags: str, category: str) -> int:
        """Add a new upload record."""
        cursor = await self._connection.execute(
            '''INSERT INTO uploads 
               (video_id, title, description, hashtags, category, status)
               VALUES (?, ?, ?, ?, ?, 'pending')''',
            (video_id, title, description, hashtags, category)
        )
        await self._connection.commit()
        return cursor.lastrowid
    
    async def update_upload_status(self, video_id: str, status: str,
                                   youtube_video_id: str = None,
                                   error_message: str = None):
        """Update upload status."""
        uploaded_at = datetime.utcnow().isoformat() if status == 'completed' else None
        
        await self._connection.execute(
            '''UPDATE uploads 
               SET status = ?, youtube_video_id = ?, uploaded_at = ?, error_message = ?
               WHERE video_id = ?''',
            (status, youtube_video_id, uploaded_at, error_message, video_id)
        )
        await self._connection.commit()
    
    async def is_uploaded(self, video_id: str) -> bool:
        """Check if a video has already been uploaded."""
        cursor = await self._connection.execute(
            '''SELECT COUNT(*) FROM uploads 
               WHERE video_id = ? AND status = 'completed' ''',
            (video_id,)
        )
        result = await cursor.fetchone()
        return result[0] > 0
    
    async def get_upload_history(self, limit: int = 10) -> List[Dict]:
        """Get recent upload history."""
        cursor = await self._connection.execute(
            '''SELECT * FROM uploads 
               ORDER BY uploaded_at DESC LIMIT ?''',
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def log_activity(self, action: str, details: str = None,
                          success: bool = True, error_message: str = None):
        """Log an activity."""
        await self._connection.execute(
            '''INSERT INTO activity_log (action, details, success, error_message)
               VALUES (?, ?, ?, ?)''',
            (action, details, 1 if success else 0, error_message)
        )
        await self._connection.commit()
    
    async def get_activities(self, limit: int = 50) -> List[Dict]:
        """Get recent activities."""
        cursor = await self._connection.execute(
            '''SELECT * FROM activity_log 
               ORDER BY created_at DESC LIMIT ?''',
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_statistics(self) -> Dict:
        """Get upload statistics."""
        cursor = await self._connection.execute(
            '''SELECT 
               COUNT(*) as total,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
               FROM uploads'''
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


# Global database instance
_db: Optional[Database] = None


async def get_database() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db


async def close_database():
    """Close database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
