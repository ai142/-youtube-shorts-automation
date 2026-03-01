#!/usr/bin/env python3
"""
YouTube Shorts Automation - Main Entry Point
Supports state persistence and resume from interruptions
"""

import argparse
import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

from config import Config
from state_manager import get_state_manager
from video_generator import VideoGenerator
from hashtag_generator import HashtagGenerator
from thumbnail_generator import ThumbnailGenerator
from youtube_uploader import YouTubeUploader
from scheduler import ViralScheduler
from database import Database
from notifications import Notifier
from logger import setup_logger

logger = setup_logger()
state = get_state_manager()

# Track if we're shutting down gracefully
shutting_down = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutting_down
    if not shutting_down:
        shutting_down = True
        logger.info("Received shutdown signal, saving state...")
        state.save_state()
        logger.info("State saved. Exiting gracefully.")
        sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def run_automation(resume: bool = False):
    """Main automation loop with state persistence"""
    
    config = Config()
    db = Database()
    scheduler = ViralScheduler()
    video_gen = VideoGenerator(config)
    hashtag_gen = HashtagGenerator(config)
    thumbnail_gen = ThumbnailGenerator(config)
    uploader = YouTubeUploader(config)
    notifier = Notifier(config)
    
    state.increment_run_count()
    
    # Check if we should resume from previous state
    if resume and state.should_resume():
        resume_info = state.get_resume_info()
        logger.info(f"Resuming from previous run...")
        logger.info(f"Stage: {resume_info['stage']}")
        logger.info(f"Timer remaining: {resume_info['timer_remaining']}s")
        logger.info(f"Pending uploads: {len(resume_info['pending_uploads'])}")
        
        # Handle pending uploads first
        if resume_info['pending_uploads']:
            logger.info("Processing pending uploads...")
            for pending in resume_info['pending_uploads']:
                if pending['attempts'] < 3:  # Max 3 attempts
                    try:
                        process_pending_upload(pending, uploader, db, notifier)
                    except Exception as e:
                        logger.error(f"Failed to upload {pending['video_path']}: {e}")
                        state.increment_attempts(pending['video_path'])
                        state.add_error(str(e), "upload_resume")
        
        # Handle active timer
        if state.is_timer_active():
            timer_remaining = state.get_timer_remaining()
            logger.info(f"Resuming timer: {timer_remaining}s remaining")
            wait_with_state(timer_remaining)
        
        # Handle video in progress
        if resume_info['current_video'] and resume_info['current_video']['stage'] != 'completed':
            logger.info(f"Found incomplete video: {resume_info['current_video']['id']}")
            # Will continue with new video generation
    
    # Main automation loop
    while not shutting_down:
        try:
            # Check if it's time to upload
            next_upload = scheduler.get_next_upload_time()
            
            if next_upload:
                wait_seconds = (next_upload - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"Waiting {int(wait_seconds)}s until next upload at {next_upload}")
                    state.set_timer(int(wait_seconds))
                    state.set_next_upload_time(next_upload)
                    wait_with_state(wait_seconds)
            
            # Generate new video
            state.set_stage("generating_video", 0)
            logger.info("Generating new AI cat video...")
            
            video_id = f"cat_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            state.start_video_generation(video_id)
            
            # Generate video
            video_path = video_gen.generate()
            state.update_video_stage("video_complete")
            logger.info(f"Video generated: {video_path}")
            
            # Generate hashtags and title
            state.set_stage("generating_metadata", 50)
            logger.info("Generating hashtags and title...")
            metadata = hashtag_gen.generate()
            state.update_video_stage("metadata_complete")
            logger.info(f"Title: {metadata['title']}")
            logger.info(f"Hashtags: {metadata['hashtags']}")
            
            # Generate thumbnail
            state.set_stage("generating_thumbnail", 70)
            logger.info("Generating thumbnail...")
            thumbnail_path = thumbnail_gen.generate(metadata['title'])
            state.update_video_stage("thumbnail_complete")
            logger.info(f"Thumbnail generated: {thumbnail_path}")
            
            # Upload to YouTube
            state.set_stage("uploading", 80)
            logger.info("Uploading to YouTube...")
            
            try:
                youtube_id = uploader.upload(
                    video_path=video_path,
                    title=metadata['title'],
                    description=metadata['description'],
                    tags=metadata['tags'],
                    thumbnail_path=thumbnail_path
                )
                state.complete_video(youtube_id)
                logger.info(f"✅ Successfully uploaded! YouTube ID: {youtube_id}")
                
                # Save to database
                db.add_video(
                    video_id=video_id,
                    title=metadata['title'],
                    youtube_id=youtube_id,
                    hashtags=metadata['hashtags'],
                    thumbnail_path=thumbnail_path
                )
                
                # Send success notification
                notifier.send_success(
                    title=metadata['title'],
                    youtube_id=youtube_id,
                    video_path=video_path
                )
                
            except Exception as upload_error:
                logger.error(f"Upload failed: {upload_error}")
                state.add_error(str(upload_error), "upload")
                
                # Add to pending uploads for retry
                state.add_pending_upload(video_path, metadata)
                state.update_video_stage("upload_failed")
                
                notifier.send_error(
                    error=str(upload_error),
                    stage="upload"
                )
            
            # Reset for next cycle
            state.reset_for_new_cycle()
            
            # Calculate next upload time
            next_upload = scheduler.get_next_upload_time()
            state.set_next_upload_time(next_upload)
            logger.info(f"Next upload scheduled for: {next_upload}")
            
            # In GitHub Actions, exit after one upload to save minutes
            if config.is_github_actions:
                logger.info("Running in GitHub Actions - completing run")
                break
                
        except Exception as e:
            logger.error(f"Automation error: {e}")
            state.add_error(str(e), state.state.get("current_stage", "unknown"))
            
            # Send error notification
            notifier.send_error(error=str(e), stage=state.state.get("current_stage", "unknown"))
            
            if config.is_github_actions:
                # In GitHub Actions, save state and exit on error
                state.save_state()
                sys.exit(1)
            else:
                # Wait before retrying
                time.sleep(300)  # 5 minutes
    
    logger.info("Automation completed")

def wait_with_state(seconds: float):
    """Wait while periodically saving state"""
    end_time = time.time() + seconds
    check_interval = 60  # Save state every minute
    
    while time.time() < end_time and not shutting_down:
        remaining = end_time - time.time()
        if remaining <= 0:
            break
        
        # Wait for check_interval or remaining time, whichever is less
        wait_time = min(check_interval, remaining)
        time.sleep(wait_time)
        
        # Update state
        state.state["timer_remaining"] = int(remaining - wait_time)
        if remaining > 60:  # Only save periodically, not every second
            state.save_state()
    
    state.clear_timer()

def process_pending_upload(pending: dict, uploader, db, notifier):
    """Process a pending upload from previous run"""
    video_path = pending['video_path']
    metadata = pending['metadata']
    
    logger.info(f"Retrying upload: {video_path} (attempt {pending['attempts'] + 1})")
    
    # Check if video file still exists
    if not Path(video_path).exists():
        logger.warning(f"Video file no longer exists: {video_path}")
        state.remove_pending_upload(video_path)
        return
    
    try:
        youtube_id = uploader.upload(
            video_path=video_path,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            thumbnail_path=metadata.get('thumbnail_path')
        )
        
        logger.info(f"✅ Successfully uploaded pending video! YouTube ID: {youtube_id}")
        state.remove_pending_upload(video_path)
        
        db.add_video(
            video_id=Path(video_path).stem,
            title=metadata['title'],
            youtube_id=youtube_id,
            hashtags=metadata.get('hashtags', [])
        )
        
        notifier.send_success(
            title=metadata['title'],
            youtube_id=youtube_id,
            video_path=video_path
        )
        
    except Exception as e:
        logger.error(f"Failed to upload pending video: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation")
    parser.add_argument('--resume', action='store_true', 
                        help='Resume from previous state if interrupted')
    parser.add_argument('--once', action='store_true',
                        help='Run only one upload cycle')
    parser.add_argument('--test', action='store_true',
                        help='Test mode - skip actual upload')
    
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("YouTube Shorts Automation Starting")
    logger.info(f"Run count: {state.state.get('run_count', 0) + 1}")
    logger.info(f"Resume mode: {args.resume}")
    logger.info("=" * 50)
    
    try:
        run_automation(resume=args.resume)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        state.save_state()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        state.add_error(str(e), "fatal")
        state.save_state()
        sys.exit(1)
    
    logger.info("Automation finished")

if __name__ == "__main__":
    main()
