# YouTube Shorts Automation Tool

AI-powered YouTube Shorts automation for viral cat content.

## Features

- 🎬 AI Video Generation - Generate viral cat videos using free/affordable AI APIs
- #️⃣ Hashtag Generation - OpenAI-powered trending hashtags
- 📝 Title & Description - Engaging, click-worthy metadata
- 🖼️ Thumbnail Generation - Leonardo.ai powered thumbnails
- ⏰ Viral Timing - Optimized posting schedule
- 📤 YouTube Upload - Automatic video upload with metadata
- 🔄 State Management - SQLite tracking to prevent duplicates

## Quick Start

### 1. Clone & Setup

```bash
cd /home/engine/project
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required API keys:
- `OPENAI_API_KEY` - For hashtag/title generation
- `YOUTUBE_CLIENT_ID` - YouTube Data API OAuth
- `YOUTUBE_CLIENT_SECRET` - YouTube Data API OAuth
- `LEONARDO_API_KEY` - For thumbnail generation (optional)
- `WEBHOOK_URL` - For failure notifications (optional)
- `EMAIL_USER` / `EMAIL_PASSWORD` - For email notifications (optional)

### 3. YouTube OAuth Setup

Run the OAuth setup script:

```bash
python setup_youtube_oauth.py
```

This will open a browser for authentication and save credentials to `youtube_credentials.json`.

### 4. Test Locally

```bash
python main.py
```

### 5. Deploy to Render.com

1. Push code to GitHub
2. Connect repo to Render.com
3. Use `render.yaml` for automatic deployment
4. Add environment variables in Render dashboard

## Project Structure

```
.
├── main.py                 # Main automation script
├── config.py               # Configuration management
├── video_generator.py      # AI video generation
├── hashtag_generator.py    # Hashtag & title generation
├── thumbnail_generator.py  # Thumbnail creation
├── youtube_uploader.py     # YouTube API integration
├── scheduler.py            # Viral timing optimization
├── database.py             # SQLite state management
├── notifications.py        # Email/webhook notifications
├── setup_youtube_oauth.py  # OAuth authentication
├── render.yaml             # Render.com configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

## Configuration

### Viral Posting Times (UTC)

| Time Range | Quality |
|------------|---------|
| 12:00-14:00 | Excellent |
| 18:00-20:00 | Excellent |
| 21:00-23:00 | Great |
| 09:00-11:00 | Good |
| 15:00-17:00 | Good |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `YOUTUBE_CLIENT_ID` | Yes | YouTube OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | Yes | YouTube OAuth client secret |
| `LEONARDO_API_KEY` | No | Leonardo.ai API key |
| `WEBHOOK_URL` | No | Discord/Slack webhook |
| `EMAIL_USER` | No | Email for notifications |
| `EMAIL_PASSWORD` | No | Email password |
| `EMAIL_TO` | No | Notification recipient |
| `RENDER` | No | Set when deployed on Render |

## Deployment on Render.com

### Automatic Deployment

The `render.yaml` file enables automatic deployment:

1. Push to GitHub
2. Create new Web Service on Render
3. Connect your GitHub repository
4. Add all environment variables
5. Deploy starts automatically

### Manual Deployment

```bash
# Install Render CLI
brew install render-cli
render deploy
```

## License

MIT
