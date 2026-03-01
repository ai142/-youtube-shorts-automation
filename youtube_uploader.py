"""
YouTube Data API v3 Integration.
Handles OAuth2 authentication and video uploads.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

import google.oauth2.credentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

import config
from database import get_database


class YouTubeUploader:
    """YouTube Data API v3 uploader with OAuth2."""
    
    def __init__(self):
        self.credentials_path = config.YOUTUBE_CREDENTIALS_PATH
        self.service = None
        self._credentials = None
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load OAuth credentials from file."""
        if not self.credentials_path.exists():
            return None
        
        try:
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            return google.oauth2.credentials.Credentials.from_authorized_user_info(
                creds_data, config.YOUTUBE_SCOPES
            )
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _save_credentials(self, credentials: Credentials):
        """Save OAuth credentials to file."""
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open(self.credentials_path, 'w') as f:
            json.dump(creds_data, f)
    
    def _get_service(self):
        """Build YouTube Data API service."""
        if self._credentials is None:
            self._credentials = self._load_credentials()
        
        if not self._credentials:
            raise ValueError("No valid YouTube credentials. Run setup_youtube_oauth.py first.")
        
        # Check if token needs refresh
        if self._credentials.expired and self._credentials.refresh_token:
            self._credentials.refresh()
            self._save_credentials(self._credentials)
        
        return build('youtube', 'v3', credentials=self._credentials)
    
    async def upload_video(self, video_path: Path, title: str, description: str,
                          tags: list, category_id: str = '15',
                          privacy_status: str = 'private') -> Optional[str]:
        """
        Upload video to YouTube.
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of hashtags/tags
            category_id: YouTube category ID (15 = Pets & Animals)
            privacy_status: 'private', 'public', or 'unlisted'
        
        Returns:
            YouTube video ID if successful, None otherwise
        """
        db = await get_database()
        
        try:
            youtube = self._get_service()
            
            # Prepare request body
            body = {
                'snippet': {
                    'title': title[:100],  # YouTube title limit
                    'description': description[:5000],  # Description limit
                    'tags': tags[:20],  # Max 20 tags
                    'categoryId': category_id,
                    'defaultLanguage': 'en'
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Upload video
            media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
            
            request = youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            # Execute upload with progress
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"Upload progress: {progress}%")
            
            video_id = response.get('id')
            
            await db.log_activity('youtube_upload',
                f"Successfully uploaded {video_id}", success=True)
            
            return video_id
            
        except HttpError as e:
            error_msg = f"YouTube API error: {e.error_details}"
            await db.log_activity('youtube_upload', error_msg, success=False)
            print(f"HTTP Error: {e.resp.status} - {e.content}")
            return None
            
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            await db.log_activity('youtube_upload', error_msg, success=False)
            print(f"Error: {e}")
            return None
    
    async def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Set custom thumbnail for uploaded video."""
        try:
            youtube = self._get_service()
            
            media = MediaFileUpload(str(thumbnail_path))
            
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"Thumbnail upload failed: {e}")
            return False
    
    async def get_upload_playlist(self) -> Optional[str]:
        """Get the upload playlist ID for the authenticated channel."""
        try:
            youtube = self._get_service()
            
            response = youtube.channels().list(
                mine=True,
                part='contentDetails'
            ).execute()
            
            if response['items']:
                return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
        except Exception as e:
            print(f"Failed to get upload playlist: {e}")
        
        return None
    
    async def check_quota(self) -> Dict:
        """Check YouTube API quota usage (approximate)."""
        try:
            youtube = self._get_service()
            
            # Get channel info (counts as 1 quota unit)
            response = youtube.channels().list(
                mine=True,
                part='snippet,statistics'
            ).execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    'channel_title': channel['snippet']['title'],
                    'view_count': channel['statistics'].get('viewCount', 0),
                    'subscriber_count': channel['statistics'].get('subscriberCount', 0),
                    'video_count': channel['statistics'].get('videoCount', 0),
                    'quota_note': 'Check Google Cloud Console for actual quota'
                }
            
        except Exception as e:
            print(f"Quota check failed: {e}")
        
        return {}


async def upload_to_youtube(video_path: Path, title: str, description: str,
                           tags: list) -> Optional[str]:
    """Convenience function to upload video."""
    uploader = YouTubeUploader()
    return await uploader.upload_video(video_path, title, description, tags)


async def check_youtube_connection() -> bool:
    """Check if YouTube API is properly configured."""
    try:
        uploader = YouTubeUploader()
        await uploader.check_quota()
        return True
    except:
        return False
