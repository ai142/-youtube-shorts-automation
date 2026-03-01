"""
State Manager for YouTube Shorts Automation
Handles saving and resuming state between GitHub Actions runs
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

class StateManager:
    """Manages automation state persistence across runs"""
    
    def __init__(self, state_file: str = "data/automation_state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self.load_state()
        
    def load_state(self) -> Dict[str, Any]:
        """Load state from file, or create default state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Default state
        return {
            "last_run": None,
            "current_stage": "idle",
            "stage_progress": 0,
            "timer_remaining": 0,
            "timer_target": None,
            "current_video": None,
            "videos_generated": 0,
            "videos_uploaded": 0,
            "last_upload_time": None,
            "next_upload_time": None,
            "errors": [],
            "pending_uploads": [],
            "run_count": 0
        }
    
    def save_state(self):
        """Save current state to file"""
        self.state["last_run"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def set_stage(self, stage: str, progress: int = 0):
        """Update current stage and progress"""
        self.state["current_stage"] = stage
        self.state["stage_progress"] = progress
        self.save_state()
    
    def set_timer(self, seconds: int):
        """Set countdown timer with target time"""
        self.state["timer_remaining"] = seconds
        self.state["timer_target"] = (datetime.now() + timedelta(seconds=seconds)).isoformat()
        self.save_state()
    
    def get_timer_remaining(self) -> int:
        """Get remaining timer seconds (resumes from saved state)"""
        if self.state.get("timer_target"):
            target = datetime.fromisoformat(self.state["timer_target"])
            remaining = (target - datetime.now()).total_seconds()
            return max(0, int(remaining))
        return self.state.get("timer_remaining", 0)
    
    def is_timer_active(self) -> bool:
        """Check if there's an active timer"""
        return self.get_timer_remaining() > 0
    
    def clear_timer(self):
        """Clear the timer"""
        self.state["timer_remaining"] = 0
        self.state["timer_target"] = None
        self.save_state()
    
    def start_video_generation(self, video_id: str):
        """Mark video generation as started"""
        self.state["current_video"] = {
            "id": video_id,
            "stage": "generating",
            "started_at": datetime.now().isoformat()
        }
        self.save_state()
    
    def update_video_stage(self, stage: str):
        """Update current video's stage"""
        if self.state.get("current_video"):
            self.state["current_video"]["stage"] = stage
            self.state["current_video"]["updated_at"] = datetime.now().isoformat()
            self.save_state()
    
    def complete_video(self, youtube_id: str = None):
        """Mark video as completed"""
        if self.state.get("current_video"):
            self.state["current_video"]["stage"] = "completed"
            self.state["current_video"]["youtube_id"] = youtube_id
            self.state["current_video"]["completed_at"] = datetime.now().isoformat()
            self.state["videos_uploaded"] += 1
            self.state["last_upload_time"] = datetime.now().isoformat()
            self.save_state()
    
    def add_pending_upload(self, video_path: str, metadata: dict):
        """Add video to pending uploads queue"""
        self.state["pending_uploads"].append({
            "video_path": video_path,
            "metadata": metadata,
            "added_at": datetime.now().isoformat(),
            "attempts": 0
        })
        self.save_state()
    
    def get_pending_uploads(self) -> list:
        """Get list of pending uploads"""
        return self.state.get("pending_uploads", [])
    
    def remove_pending_upload(self, video_path: str):
        """Remove completed upload from queue"""
        self.state["pending_uploads"] = [
            v for v in self.state["pending_uploads"] 
            if v["video_path"] != video_path
        ]
        self.save_state()
    
    def increment_attempts(self, video_path: str):
        """Increment upload attempt count"""
        for v in self.state["pending_uploads"]:
            if v["video_path"] == video_path:
                v["attempts"] += 1
                v["last_attempt"] = datetime.now().isoformat()
        self.save_state()
    
    def add_error(self, error: str, stage: str):
        """Record an error"""
        self.state["errors"].append({
            "error": error,
            "stage": stage,
            "time": datetime.now().isoformat()
        })
        # Keep only last 50 errors
        self.state["errors"] = self.state["errors"][-50:]
        self.save_state()
    
    def should_resume(self) -> bool:
        """Check if we should resume from previous state"""
        return (
            self.state.get("current_stage") != "idle" and
            self.state.get("current_stage") != "completed"
        ) or len(self.get_pending_uploads()) > 0 or self.is_timer_active()
    
    def get_resume_info(self) -> Dict[str, Any]:
        """Get information about what to resume"""
        return {
            "stage": self.state.get("current_stage"),
            "timer_remaining": self.get_timer_remaining(),
            "current_video": self.state.get("current_video"),
            "pending_uploads": self.get_pending_uploads(),
            "videos_uploaded": self.state.get("videos_uploaded", 0)
        }
    
    def set_next_upload_time(self, dt: datetime):
        """Set the next scheduled upload time"""
        self.state["next_upload_time"] = dt.isoformat()
        self.save_state()
    
    def get_next_upload_time(self) -> Optional[datetime]:
        """Get next scheduled upload time"""
        if self.state.get("next_upload_time"):
            return datetime.fromisoformat(self.state["next_upload_time"])
        return None
    
    def increment_run_count(self):
        """Increment the run counter"""
        self.state["run_count"] = self.state.get("run_count", 0) + 1
        self.save_state()
    
    def reset_for_new_cycle(self):
        """Reset state for a new automation cycle"""
        self.state["current_stage"] = "idle"
        self.state["stage_progress"] = 0
        self.state["current_video"] = None
        self.save_state()


# Singleton instance
_state_manager = None

def get_state_manager() -> StateManager:
    """Get the state manager singleton"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
