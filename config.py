"""
Configuration management for YouTube Shorts Automation Tool.
Loads environment variables and provides defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if exists
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# YouTube API Configuration
YOUTUBE_SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

# Video Configuration
VIDEO_ASPECT_RATIO = "9:16"
VIDEO_MAX_DURATION = 60  # seconds
VIDEO_RESOLUTION = "1080x1920"  # Vertical HD
THUMBNAIL_RESOLUTION = "1280x720"

# Thumbnail Configuration
THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720

# Database Configuration
DATABASE_PATH = Path(__file__).parent / 'uploads.db'

# Credentials paths
YOUTUBE_CREDENTIALS_PATH = Path(__file__).parent / 'youtube_credentials.json'

# Viral posting times (UTC) - optimized for YouTube Shorts engagement
VIRAL_POSTING_TIMES = [
    {'start': '12:00', 'end': '14:00', 'quality': 'excellent'},
    {'start': '18:00', 'end': '20:00', 'quality': 'excellent'},
    {'start': '21:00', 'end': '23:00', 'quality': 'great'},
    {'start': '09:00', 'end': '11:00', 'quality': 'good'},
    {'start': '15:00', 'end': '17:00', 'quality': 'good'},
]

# Hashtag Configuration
MIN_HASHTAGS = 5
MAX_HASHTAGS = 10

# Title Configuration
TITLE_MIN_LENGTH = 30
TITLE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 5000

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# API Rate Limiting
YOUTUBE_QUOTA_BUFFER = 10000  # Keep buffer for manual uploads

# Notification retry
NOTIFICATION_MAX_RETRIES = 2

# Default categories for cat content
CAT_CATEGORIES = [
    'funny cat',
    'cute cat',
    'cat fails',
    'cat compilation',
    'sleeping cat',
    'playing cat',
    'cat reactions',
    'kitten',
]

# Viral cat hashtag templates
CAT_HASHTAG_TEMPLATES = [
    '#catsoftiktok #catlover #cattok #funnycat #cutekitten #petlife',
    '#viral #fyp #foryou #trending #cats #meow',
    '#catvideo #funnyvideos #cutecat #catmemes #kitty',
]


def get_env(key: str, default: str = None) -> str:
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def get_required_env(key: str) -> str:
    """Get required environment variable, raise if missing."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def is_render() -> bool:
    """Check if running on Render.com."""
    return os.getenv('RENDER', '').lower() == 'true'

def is_github_actions() -> bool:
    """Check if running in GitHub Actions."""
    return os.getenv('GITHUB_ACTIONS', '').lower() == 'true'

class Config:
    """Configuration class for automation"""
    
    def __init__(self):
        self.openai_api_key = get_env('OPENAI_API_KEY')
        self.youtube_client_id = get_env('YOUTUBE_CLIENT_ID')
        self.youtube_client_secret = get_env('YOUTUBE_CLIENT_SECRET')
        self.leonardo_api_key = get_env('LEONARDO_API_KEY')
        self.webhook_url = get_env('WEBHOOK_URL')
        self.email_user = get_env('EMAIL_USER')
        self.email_password = get_env('EMAIL_PASSWORD')
        self.email_to = get_env('EMAIL_TO')
        
        # Check if running in GitHub Actions
        self.is_github_actions = is_github_actions()
        
        # Paths
        self.output_dir = Path('output')
        self.credentials_dir = Path('credentials')
        self.data_dir = Path('data')
        self.logs_dir = Path('logs')
        
        # Create directories
        for d in [self.output_dir, self.credentials_dir, self.data_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """Validate required configuration"""
        missing = []
        if not self.openai_api_key:
            missing.append('OPENAI_API_KEY')
        if not self.youtube_client_id:
            missing.append('YOUTUBE_CLIENT_ID')
        if not self.youtube_client_secret:
            missing.append('YOUTUBE_CLIENT_SECRET')
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
