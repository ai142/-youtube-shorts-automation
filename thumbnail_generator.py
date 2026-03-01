"""
Thumbnail Generator using Leonardo.ai API.
Creates eye-catching 1280x720 thumbnails for YouTube Shorts.
"""
import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import config
from database import get_database


class ThumbnailGenerator:
    """Generate thumbnails using Leonardo.ai or fallback methods."""
    
    def __init__(self):
        self.api_key = config.get_env('LEONARDO_API_KEY')
        self.output_dir = Path(__file__).parent / 'thumbnails'
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_thumbnail(self, title: str, category: str,
                                 video_id: str) -> Optional[Path]:
        """Generate a thumbnail for the video."""
        db = await get_database()
        
        thumbnail_path = self.output_dir / f"{video_id}_thumbnail.jpg"
        
        # Try Leonardo.ai first
        if self.api_key:
            try:
                result = await self._generate_with_leonardo(title, category, video_id)
                if result:
                    return result
            except Exception as e:
                await db.log_activity('thumbnail_generation',
                    f"Leonardo.ai failed: {str(e)}", success=False)
        
        # Fallback to generate locally
        return await self._generate_local_thumbnail(title, category, video_id)
    
    async def _generate_with_leonardo(self, title: str, category: str,
                                      video_id: str) -> Optional[Path]:
        """Generate thumbnail using Leonardo.ai API."""
        # Leonardo.ai API endpoint for image generation
        url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        
        prompt = self._build_thumbnail_prompt(title, category)
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'prompt': prompt,
            'model': 'Leonardo Creative',
            'width': 1280,
            'height': 720,
            'num_images': 1,
            'guidance_scale': 7.5,
            'prompt_magic': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Get generation ID and wait for result
                    generation_id = data.get('sd-generation-job', {}).get('generationId')
                    
                    if generation_id:
                        return await self._wait_for_generation(
                            session, generation_id, video_id
                        )
        
        return None
    
    async def _wait_for_generation(self, session: aiohttp.ClientSession,
                                   generation_id: str, video_id: str,
                                   max_attempts: int = 30) -> Optional[Path]:
        """Wait for Leonardo.ai generation to complete."""
        url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        headers = {'Authorization': f'Bearer {self.api_key}'}
        
        for _ in range(max_attempts):
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get('generations_by_pk', {}).get('status')
                    
                    if status == 'COMPLETE':
                        # Get the generated image URL
                        images = data.get('generations_by_pk', {}).get('generated_images', [])
                        if images:
                            image_url = images[0].get('url')
                            return await self._download_thumbnail(image_url, video_id)
                    
                    elif status == 'FAILED':
                        return None
            
            await asyncio.sleep(2)  # Wait 2 seconds between checks
        
        return None
    
    async def _download_thumbnail(self, url: str, video_id: str) -> Path:
        """Download generated thumbnail."""
        thumbnail_path = self.output_dir / f"{video_id}_thumbnail.jpg"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(thumbnail_path, 'wb') as f:
                        f.write(content)
        
        return thumbnail_path
    
    def _build_thumbnail_prompt(self, title: str, category: str) -> str:
        """Build prompt for thumbnail generation."""
        base_prompt = f"""YouTube thumbnail for cat video: {title}
        
Style requirements:
- High contrast, eye-catching
- Bright colors, vibrant
- Text overlay-friendly
- Professional quality
- Cat in {category} setting
- Clear focal point
- Digital art, trending on artstation"""
        
        return base_prompt
    
    async def _generate_local_thumbnail(self, title: str, category: str,
                                        video_id: str) -> Path:
        """Generate thumbnail locally using Pillow."""
        from PIL import Image, ImageDraw, ImageFont
        
        # Create thumbnail
        width, height = config.THUMBNAIL_WIDTH, config.THUMBNAIL_HEIGHT
        img = Image.new('RGB', (width, height), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        
        # Add gradient overlay
        for i in range(height):
            color = int(30 + (20 * i / height))
            draw.line([(0, i), (width, i)], fill=(color, color, color))
        
        # Add cat emoji/icon placeholder
        emoji = "🐱"
        
        # Try to use default font
        try:
            # Use default system font
            font_size = 120
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Draw emoji
        text_bbox = draw.textbbox((0, 0), emoji, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2 - 30
        
        draw.text((x, y), emoji, fill=(255, 255, 255), font=font)
        
        # Add title text
        title_short = title[:40] + "..." if len(title) > 40 else title
        draw.text((width // 2, height - 80), title_short, 
                 fill=(255, 255, 255), font=font, anchor='mm')
        
        # Save thumbnail
        thumbnail_path = self.output_dir / f"{video_id}_thumbnail.jpg"
        img.save(thumbnail_path, 'JPEG', quality=85)
        
        return thumbnail_path
    
    async def create_default_thumbnail(self, video_id: str) -> Path:
        """Create a simple default thumbnail."""
        return await self._generate_local_thumbnail(
            "Cat Video", "cute", video_id
        )


async def generate_thumbnail(title: str, category: str, video_id: str) -> Path:
    """Convenience function to generate a thumbnail."""
    generator = ThumbnailGenerator()
    path = await generator.generate_thumbnail(title, category, video_id)
    
    if not path or not path.exists():
        path = await generator.create_default_thumbnail(video_id)
    
    return path
