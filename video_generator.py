"""
AI Video Generator for YouTube Shorts.
Fetches viral cat videos from free APIs and prepares them for upload.
"""
import os
import json
import hashlib
import random
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import aiohttp
import config
from database import get_database

# Video sources - free cat video APIs
CAT_VIDEO_SOURCES = [
    {
        'name': 'TheCatAPI',
        'url': 'https://api.thecatapi.com/v1/images/search',
        'type': 'images'  # API returns images, not videos
    },
    {
        'name': 'cataas',
        'url': 'https://cataas.com/cat',
        'type': 'images'
    },
]


class VideoGenerator:
    """Generate/fetch cat videos for YouTube Shorts."""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent / 'videos'
        self.output_dir.mkdir(exist_ok=True)
        self.thumbnails_dir = Path(__file__).parent / 'thumbnails'
        self.thumbnails_dir.mkdir(exist_ok=True)
    
    async def get_random_cat_content(self, category: str = None) -> Dict:
        """Get random cat content from available sources."""
        db = await get_database()
        
        try:
            # Try TheCatAPI first
            content = await self._fetch_from_catapi(category)
            if content:
                return content
            
            # Fallback to local generation
            return await self._generate_local_content(category)
            
        except Exception as e:
            await db.log_activity('video_fetch', str(e), success=False)
            raise
    
    async def _fetch_from_catapi(self, category: str = None) -> Optional[Dict]:
        """Fetch cat image/video from TheCatAPI."""
        async with aiohttp.ClientSession() as session:
            # Get random cat image
            params = {'mime_types': 'jpg,png,gif'}
            if category:
                # Search by category if supported
                params['category'] = category
            
            async with session.get(
                'https://api.thecatapi.com/v1/images/search',
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        cat = data[0]
                        return {
                            'source': 'thecatapi',
                            'url': cat.get('url'),
                            'width': cat.get('width'),
                            'height': cat.get('height'),
                            'id': cat.get('id'),
                            'type': 'image'
                        }
        return None
    
    async def _generate_local_content(self, category: str = None) -> Dict:
        """Generate content using local approach when APIs unavailable."""
        # Generate a unique video ID
        video_id = self._generate_video_id(category)
        
        # Use sample/placeholder content
        # In production, this would integrate with AI video APIs
        return {
            'source': 'local',
            'video_id': video_id,
            'category': category or random.choice(config.CAT_CATEGORIES),
            'type': 'placeholder',
            'note': 'AI video generation would happen here'
        }
    
    def _generate_video_id(self, category: str = None) -> str:
        """Generate unique video ID."""
        timestamp = datetime.utcnow().isoformat()
        data = f"{timestamp}-{category or 'random'}-{random.randint(1000, 9999)}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    async def prepare_video(self, content: Dict) -> Dict:
        """Prepare video for upload - download, resize, format."""
        db = await get_database()
        
        video_id = content.get('video_id', self._generate_video_id())
        
        await db.log_activity('video_prepare', f"Preparing video {video_id}")
        
        # For image content, we'd need video generation
        # This is a simplified version - full implementation would
        # use services like RunwayML, Pika, or similar
        
        output = {
            'video_id': video_id,
            'path': str(self.output_dir / f"{video_id}.mp4"),
            'thumbnail_path': str(self.thumbnails_dir / f"{video_id}.jpg"),
            'duration': random.randint(15, 60),  # 15-60 seconds
            'aspect_ratio': '9:16',
            'resolution': '1080x1920',
            'category': content.get('category', 'cat'),
            'source': content.get('source', 'generated')
        }
        
        return output
    
    async def download_asset(self, url: str, save_path: Path) -> bool:
        """Download video/image asset from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        return True
        except Exception as e:
            print(f"Download failed: {e}")
        return False


async def generate_video(category: str = None) -> Dict:
    """Convenience function to generate a video."""
    generator = VideoGenerator()
    
    # Get cat content
    content = await generator.get_random_cat_content(category)
    
    # Prepare for upload
    prepared = await generator.prepare_video(content)
    
    return prepared


async def get_video_path(video_id: str) -> Optional[Path]:
    """Get path to existing video."""
    generator = VideoGenerator()
    video_path = generator.output_dir / f"{video_id}.mp4"
    
    if video_path.exists():
        return video_path
    return None
