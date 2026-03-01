#!/usr/bin/env python3
"""
Render.com Deployment Guide Script

Run this to get step-by-step deployment instructions.
"""
import os
import sys


def print_step(number, title, description):
    """Print a formatted step."""
    print(f"\n{'='*60}")
    print(f"STEP {number}: {title}")
    print(f"{'='*60}")
    print(description)


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║     YouTube Shorts Automation - Deployment Guide          ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    print_step(1, "Prepare Your Code",
        """Push your code to a GitHub repository:
        
1. Create a new GitHub repository
2. Add all files:
   git init
   git add .
   git commit -m "Initial commit"
3. Create GitHub repo and push:
   git remote add origin https://github.com/YOUR_USERNAME/repo.git
   git branch -M main
   git push -u origin main
        """)
    
    print_step(2, "Get OpenAI API Key",
        """1. Go to https://platform.openai.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new secret key
5. Copy the key (you won't see it again!)
        """)
    
    print_step(3, "Get YouTube API Credentials",
        """1. Go to https://console.cloud.google.com/
2. Create a new project (name it "YouTube Shorts Bot")
3. Enable "YouTube Data API v3"
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Set application type to "Desktop app"
6. Download the JSON file
7. Copy client_id and client_secret from the JSON
        """)
    
    print_step(4, "Connect to Render.com",
        """1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository with your code
        """)
    
    print_step(5, "Configure Environment Variables",
        """Add these environment variables in Render:
        
Required:
- OPENAI_API_KEY: sk-...
- YOUTUBE_CLIENT_ID: ...apps.googleusercontent.com
- YOUTUBE_CLIENT_SECRET: ...

Optional (for notifications):
- WEBHOOK_URL: Discord/Slack webhook URL
- EMAIL_USER: your-email@gmail.com
- EMAIL_PASSWORD: app-specific password
- EMAIL_TO: recipient email
        """)
    
    print_step(6, "Run OAuth Setup",
        """After deployment, run the OAuth setup:

1. Open a shell on Render.com
2. Run: python setup_youtube_oauth.py
3. Follow the browser authentication
4. Credentials will be saved to youtube_credentials.json
        """)
    
    print_step(7, "Deploy",
        """1. Click "Create Web Service" on Render
2. Wait for build to complete
3. Check logs for any errors
4. Your automation is now running!

The cron job will run daily at 12:00 UTC.
        """)
    
    print("\n" + "="*60)
    print("🎉 You're all set!")
    print("="*60)
    print("""
Quick Commands:
- Run manually: python main.py
- Run with forced timing: python main.py --force
- Check status: Look at the database for upload history

Troubleshooting:
- Check logs in Render dashboard
- Verify all API keys are correct
- Re-run OAuth setup if credentials expired
    """)


if __name__ == '__main__':
    main()
