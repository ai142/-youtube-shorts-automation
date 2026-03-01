"""
Notifications module for email and webhook alerts.
Handles failure notifications via Discord/Slack webhooks and email.
"""
import os
import asyncio
import aiohttp
from typing import Optional, Dict
from datetime import datetime
import config
from database import get_database


class NotificationManager:
    """Manage notifications for upload successes and failures."""
    
    def __init__(self):
        self.webhook_url = config.get_env('WEBHOOK_URL')
        self.email_user = config.get_env('EMAIL_USER')
        self.email_password = config.get_env('EMAIL_PASSWORD')
        self.email_to = config.get_env('EMAIL_TO')
    
    async def notify_success(self, video_id: str, youtube_id: str, title: str):
        """Send success notification."""
        await self._send_discord_embed(
            title="✅ Video Uploaded Successfully!",
            color=0x00FF00,
            fields=[
                {"name": "Video ID", "value": video_id, "inline": True},
                {"name": "YouTube ID", "value": youtube_id, "inline": True},
                {"name": "Title", "value": title[:50] + "..." if len(title) > 50 else title},
            ]
        )
        
        await self._send_email(
            subject=f"🎬 Video Uploaded: {title[:30]}",
            body=f"Video uploaded successfully to YouTube!\n\nVideo ID: {video_id}\nYouTube ID: {youtube_id}\nTitle: {title}"
        )
    
    async def notify_failure(self, video_id: str, error: str, category: str = None):
        """Send failure notification."""
        db = await get_database()
        
        await self._send_discord_embed(
            title="❌ Video Upload Failed",
            color=0xFF0000,
            fields=[
                {"name": "Video ID", "value": video_id, "inline": True},
                {"name": "Category", "value": category or "N/A", "inline": True},
                {"name": "Error", "value": error[:100]},
            ]
        )
        
        await self._send_email(
            subject=f"⚠️ Upload Failed: {video_id}",
            body=f"Video upload failed!\n\nVideo ID: {video_id}\nCategory: {category}\nError: {error}\n\nTime: {datetime.utcnow().isoformat()}"
        )
        
        # Log the failure
        await db.log_activity('notification', f"Failure notified: {error}", success=False)
    
    async def notify_daily_summary(self, stats: Dict):
        """Send daily summary notification."""
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        
        message = f"📊 Daily Summary\n\n"
        message += f"Total Uploads: {total}\n"
        message += f"Completed: {completed}\n"
        message += f"Failed: {failed}\n"
        
        await self._send_discord_embed(
            title="📊 Daily Upload Summary",
            color=0x3498DB,
            fields=[
                {"name": "Total", "value": str(total), "inline": True},
                {"name": "Completed", "value": str(completed), "inline": True},
                {"name": "Failed", "value": str(failed), "inline": True},
            ]
        )
    
    async def _send_discord_embed(self, title: str, color: int, 
                                  fields: list = None) -> bool:
        """Send Discord webhook embed."""
        if not self.webhook_url:
            return False
        
        embed = {
            "title": title,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": fields or []
        }
        
        payload = {
            "embeds": [embed],
            "username": "YouTube Shorts Bot",
            "avatar_url": "https://i.imgur.com/cQ8r4pE.png"
        }
        
        for attempt in range(config.NOTIFICATION_MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url, 
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 204 or response.status == 200:
                            return True
                        
            except Exception as e:
                print(f"Webhook attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)
        
        return False
    
    async def _send_email(self, subject: str, body: str) -> bool:
        """Send email notification."""
        if not all([self.email_user, self.email_password, self.email_to]):
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.email_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Note: In production, use environment variables for sensitive data
            # and consider using a proper email service
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.sendmail(self.email_user, self.email_to, msg.as_string())
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Email notification failed: {e}")
            return False
    
    async def test_notifications(self) -> Dict:
        """Test notification channels."""
        results = {
            'webhook': False,
            'email': False
        }
        
        # Test webhook
        if self.webhook_url:
            results['webhook'] = await self._send_discord_embed(
                title="🧪 Test Notification",
                color=0xFFFF00,
                fields=[{"name": "Status", "value": "Notifications working!"}]
            )
        
        # Test email
        if all([self.email_user, self.email_password, self.email_to]):
            results['email'] = await self._send_email(
                subject="Test - YouTube Shorts Bot",
                body="This is a test notification from YouTube Shorts Automation Bot."
            )
        
        return results


async def send_failure_alert(video_id: str, error: str, category: str = None):
    """Convenience function to send failure alert."""
    notifier = NotificationManager()
    await notifier.notify_failure(video_id, error, category)


async def send_success_alert(video_id: str, youtube_id: str, title: str):
    """Convenience function to send success alert."""
    notifier = NotificationManager()
    await notifier.notify_success(video_id, youtube_id, title)
