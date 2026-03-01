"""
Viral Timing Optimizer for YouTube Shorts.
Analyzes and schedules uploads during peak engagement times.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
import config
from database import get_database


class ViralTimingOptimizer:
    """Optimize posting times for maximum engagement."""
    
    # Best posting times for YouTube Shorts (UTC)
    VIRAL_WINDOWS = [
        {'start': '12:00', 'end': '14:00', 'quality': 'excellent', 'day_weight': 1.2},
        {'start': '18:00', 'end': '20:00', 'quality': 'excellent', 'day_weight': 1.3},
        {'start': '21:00', 'end': '23:00', 'quality': 'great', 'day_weight': 1.1},
        {'start': '09:00', 'end': '11:00', 'quality': 'good', 'day_weight': 1.0},
        {'start': '15:00', 'end': '17:00', 'quality': 'good', 'day_weight': 0.9},
    ]
    
    # Day of week weights (Friday-Sunday tend to perform better)
    DAY_WEIGHTS = {
        0: 0.9,  # Monday
        1: 0.9,  # Tuesday
        2: 1.0,  # Wednesday
        3: 1.0,  # Thursday
        4: 1.2,  # Friday
        5: 1.3,  # Saturday
        6: 1.3,  # Sunday
    }
    
    def __init__(self, timezone: str = 'UTC'):
        self.timezone = pytz.timezone(timezone)
    
    def get_next_optimal_time(self, min_wait_hours: int = 1) -> datetime:
        """
        Get the next optimal posting time.
        
        Args:
            min_wait_hours: Minimum hours to wait before next post
            
        Returns:
            datetime of next optimal posting window
        """
        now = datetime.now(self.timezone)
        min_time = now + timedelta(hours=min_wait_hours)
        
        # Check next 7 days for optimal windows
        for day_offset in range(7):
            check_date = now + timedelta(days=day_offset)
            day_of_week = check_date.weekday()
            day_weight = self.DAY_WEIGHTS.get(day_of_week, 1.0)
            
            for window in self.VIRAL_WINDOWS:
                start_hour, end_hour = map(int, window['start'].split(':'))
                
                # Calculate window start time
                window_start = check_date.replace(
                    hour=start_hour, minute=0, second=0, microsecond=0
                )
                window_end = check_date.replace(
                    hour=end_hour, minute=0, second=0, microsecond=0
                )
                
                # Apply day weight to quality
                effective_quality = window.get('quality', 'good')
                
                # Check if window is in the future and meets minimum wait
                if window_start > min_time:
                    # Add some randomness within the window
                    import random
                    minutes_offset = random.randint(0, 30)
                    scheduled_time = window_start + timedelta(minutes=minutes_offset)
                    
                    return scheduled_time
        
        # Fallback: return time tomorrow during a good window
        return min_time + timedelta(hours=4)
    
    def get_current_time_quality(self) -> Dict:
        """Get the quality rating for the current time."""
        now = datetime.now(self.timezone)
        current_hour = now.hour
        day_of_week = now.weekday()
        
        for window in self.VIRAL_WINDOWS:
            start_hour, end_hour = map(int, window['start'].split(':'))
            
            if start_hour <= current_hour < end_hour:
                day_weight = self.DAY_WEIGHTS.get(day_of_week, 1.0)
                return {
                    'quality': window['quality'],
                    'score': self._quality_to_score(window['quality']) * day_weight,
                    'is_optimal': True,
                    'next_window': self.get_next_optimal_time()
                }
        
        return {
            'quality': 'poor',
            'score': 0.2,
            'is_optimal': False,
            'next_window': self.get_next_optimal_time()
        }
    
    def _quality_to_score(self, quality: str) -> float:
        """Convert quality to numeric score."""
        scores = {
            'excellent': 1.0,
            'great': 0.8,
            'good': 0.6,
            'poor': 0.2
        }
        return scores.get(quality, 0.5)
    
    def should_post_now(self) -> bool:
        """Check if we should post now based on timing."""
        quality_info = self.get_current_time_quality()
        return quality_info['is_optimal'] and quality_info['score'] >= 0.6
    
    def get_schedule_summary(self) -> List[Dict]:
        """Get summary of today's optimal posting times."""
        now = datetime.now(self.timezone)
        today = now.date()
        summary = []
        
        for window in self.VIRAL_WINDOWS:
            start_hour, end_hour = map(int, window['start'].split(':'))
            
            window_start = datetime.combine(today, 
                datetime.min.time()).replace(hour=start_hour, tzinfo=self.timezone)
            
            if window_start > now:
                day_weight = self.DAY_WEIGHTS.get(now.weekday(), 1.0)
                summary.append({
                    'time': window['start'],
                    'end': window['end'],
                    'quality': window['quality'],
                    'score': self._quality_to_score(window['quality']) * day_weight,
                    'hours_until': (window_start - now).total_seconds() / 3600
                })
        
        return sorted(summary, key=lambda x: x['hours_until'])
    
    async def get_posting_stats(self) -> Dict:
        """Get statistics about posting patterns."""
        db = await get_database()
        
        # Get recent uploads
        uploads = await db.get_upload_history(limit=20)
        
        if not uploads:
            return {
                'total_uploads': 0,
                'avg_time_quality': 'N/A',
                'recommendation': 'No data yet - post during excellent times'
            }
        
        # Analyze upload times
        quality_scores = []
        for upload in uploads:
            if upload.get('uploaded_at'):
                upload_time = datetime.fromisoformat(upload['uploaded_at'])
                hour = upload_time.hour
                
                # Check which window this falls in
                for window in self.VIRAL_WINDOWS:
                    start, end = map(int, window['start'].split(':'))
                    if start <= hour < end:
                        quality_scores.append(
                            self._quality_to_score(window['quality'])
                        )
                        break
                else:
                    quality_scores.append(0.2)
        
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        quality_label = 'poor'
        if avg_score >= 0.8:
            quality_label = 'excellent'
        elif avg_score >= 0.6:
            quality_label = 'good'
        elif avg_score >= 0.4:
            quality_label = 'fair'
        
        return {
            'total_uploads': len(uploads),
            'avg_time_quality': quality_label,
            'avg_score': round(avg_score, 2),
            'recommendation': self._get_recommendation(avg_score)
        }
    
    def _get_recommendation(self, avg_score: float) -> str:
        """Get recommendation based on average score."""
        if avg_score >= 0.8:
            return "Great job! Your posting times are optimal."
        elif avg_score >= 0.6:
            return "Good timing. Consider posting during excellent windows."
        else:
            return "Improve timing - aim for 12-14, 18-20, or 21-23 UTC"


async def get_next_post_time() -> datetime:
    """Convenience function to get next optimal posting time."""
    optimizer = ViralTimingOptimizer()
    return optimizer.get_next_optimal_time()


async def should_post() -> bool:
    """Convenience function to check if should post now."""
    optimizer = ViralTimingOptimizer()
    return optimizer.should_post_now()
