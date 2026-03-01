#!/usr/bin/env python3
"""
YouTube Shorts Automation Tool - Main Entry Point

This script orchestrates the entire automation workflow:
1. Generate video metadata (title, hashtags, description)
2. Generate/fetch cat video content
3. Generate thumbnail
4. Upload to YouTube
5. Handle notifications and error tracking
"""
import asyncio
import sys
import random
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from database import get_database, close_database
from video_generator import generate_video
from hashtag_generator import generate_metadata
from thumbnail_generator import generate_thumbnail
from youtube_uploader import YouTubeUploader
from scheduler import ViralTimingOptimizer, should_post
from notifications import send_failure_alert, send_success_alert


class ShortsAutomation:
    """Main automation orchestrator."""
    
    def __init__(self):
        self.db = None
        self.uploader = None
        self.scheduler = ViralTimingOptimizer()
    
    async def initialize(self):
        """Initialize components."""
        self.db = await get_database()
        self.uploader = YouTubeUploader()
        
        await self.db.log_activity('automation_start',
            f"Starting automation at {datetime.utcnow().isoformat()}")
    
    async def cleanup(self):
        """Cleanup resources."""
        await close_database()
    
    async def run(self, force: bool = False) -> bool:
        """
        Run the automation workflow.
        
        Args:
            force: Force run regardless of optimal timing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check timing unless forced
            if not force:
                timing = self.scheduler.get_current_time_quality()
                if not timing['is_optimal']:
                    print(f"⏰ Not optimal time ({timing['quality']}). "
                          f"Next window: {timing['next_window']}")
                    
                    # Still run but log it
                    await self.db.log_activity('timing',
                        f"Not optimal - quality: {timing['quality']}")
            
            # Step 1: Select category
            category = random.choice(config.CAT_CATEGORIES)
            print(f"🎬 Selected category: {category}")
            
            # Step 2: Generate video content
            print("📹 Generating video content...")
            video_data = await generate_video(category)
            video_id = video_data['video_id']
            
            # Check for duplicates
            if await self.db.is_uploaded(video_id):
                print(f"⏭️ Video {video_id} already uploaded, skipping.")
                return True
            
            # Step 3: Generate metadata
            print("✍️  Generating title, hashtags, description...")
            metadata = await generate_metadata(category, video_id)
            
            # Step 4: Generate thumbnail
            print("🖼️  Generating thumbnail...")
            thumbnail_path = await generate_thumbnail(
                metadata['title'], category, video_id
            )
            
            # For demo purposes, we'll simulate the video
            # In production, you'd have actual video files
            video_path = Path(config.DATABASE_PATH).parent / 'videos' / f"{video_id}.mp4"
            
            if not video_path.exists():
                print(f"📝 Note: Video file not found at {video_path}")
                print("   In production, integrate with AI video generation API")
                
                # Create placeholder for demo
                video_path.parent.mkdir(exist_ok=True)
                # Skip actual upload in demo mode - create placeholder
                await self.db.add_upload(
                    video_id=video_id,
                    title=metadata['title'],
                    description=metadata['description'],
                    hashtags=metadata['hashtag_string'],
                    category=category
                )
                
                # For demo, mark as completed without actual upload
                await self.db.update_upload_status(
                    video_id, 'completed', 
                    youtube_video_id=f"demo_{video_id[:8]}"
                )
                
                print(f"✅ Demo upload recorded: {video_id}")
                
                # Send notification (if configured)
                await send_success_alert(
                    video_id, 
                    f"demo_{video_id[:8]}",
                    metadata['title']
                )
                
                return True
            
            # Step 5: Upload to YouTube
            print("⬆️  Uploading to YouTube...")
            
            # Prepare tags from hashtags
            tags = [h.replace('#', '') for h in metadata['hashtags']]
            tags.extend(['cats', 'catvideos', 'shorts', 'viral'])
            tags = list(set(tags))[:20]  # YouTube max 20 tags
            
            youtube_id = await self.uploader.upload_video(
                video_path=video_path,
                title=metadata['title'],
                description=metadata['description'],
                tags=tags
            )
            
            if not youtube_id:
                raise Exception("YouTube upload failed")
            
            # Step 6: Set thumbnail
            print("🖼️  Setting thumbnail...")
            await self.uploader.set_thumbnail(youtube_id, thumbnail_path)
            
            # Step 7: Update database
            await self.db.update_upload_status(video_id, 'completed', youtube_id)
            
            # Step 8: Send success notification
            await send_success_alert(video_id, youtube_id, metadata['title'])
            
            print(f"✅ Upload complete! YouTube ID: {youtube_id}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            
            # Log error
            if self.db:
                await self.db.log_activity('automation_error', error_msg, success=False)
                
                # Send failure notification
                await send_failure_alert(video_id, error_msg, category)
            
            return False


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🐱 YouTube Shorts Automation Tool")
    print("=" * 60)
    print(f"⏰ Current time: {datetime.now()}")
    
    # Check timing
    scheduler = ViralTimingOptimizer()
    timing = scheduler.get_current_time_quality()
    print(f"📊 Current time quality: {timing['quality'].upper()}")
    
    # Parse arguments
    force = '--force' in sys.argv or '-f' in sys.argv
    
    if force:
        print("⚡ Forced run enabled")
    
    # Run automation
    automation = ShortsAutomation()
    
    try:
        await automation.initialize()
        success = await automation.run(force=force)
        
        if success:
            print("\n✅ Automation completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Automation completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
        
    finally:
        await automation.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
