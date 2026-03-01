#!/usr/bin/env python3
"""
YouTube OAuth2 Setup Script.

This script authenticates with YouTube Data API v3 and saves credentials
for future automated uploads.

Instructions:
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable YouTube Data API v3
4. Go to Credentials → Create Credentials → OAuth 2.0 Client IDs
5. Download the JSON file
6. Run this script and follow the prompts
"""
import os
import sys
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config


def get_client_secrets():
    """Get OAuth client secrets from user input or environment."""
    client_id = config.get_env('YOUTUBE_CLIENT_ID')
    client_secret = config.get_env('YOUTUBE_CLIENT_SECRET')
    
    if client_id and client_secret:
        # Create client secrets file from environment
        secrets = {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': ['http://localhost']
            }
        }
        return secrets
    
    # Check for downloaded client secrets file
    secrets_path = Path(__file__).parent / 'client_secrets.json'
    if secrets_path.exists():
        with open(secrets_path) as f:
            return json.load(f)
    
    return None


def run_oauth_flow():
    """Run OAuth2 authentication flow."""
    print("=" * 60)
    print("YouTube OAuth2 Setup")
    print("=" * 60)
    
    # Get client secrets
    secrets = get_client_secrets()
    
    if not secrets:
        print("\n❌ No OAuth credentials found!")
        print("\nPlease provide credentials in one of these ways:")
        print("1. Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env")
        print("2. Download OAuth credentials from Google Cloud Console")
        print("   and save as 'client_secrets.json'")
        print("\nFollow these steps:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a new project")
        print("  3. Enable YouTube Data API v3")
        print("  4. Go to Credentials → Create Credentials → OAuth 2.0")
        print("  5. Download JSON and save as 'client_secrets.json'")
        return False
    
    # Save temporary client secrets
    temp_secrets = Path(__file__).parent / 'temp_client_secrets.json'
    with open(temp_secrets, 'w') as f:
        json.dump(secrets, f)
    
    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(temp_secrets),
            config.YOUTUBE_SCOPES
        )
        
        print("\n🔐 Opening browser for authentication...")
        print("(If no browser opens, you'll be given a URL to visit)")
        
        credentials = flow.run_local_server(
            port=8080,
            prompt='consent',
            access_type='offline',
            timeout_seconds=300
        )
        
        # Save credentials
        config.YOUTUBE_CREDENTIALS_PATH.parent.mkdir(exist_ok=True)
        with open(config.YOUTUBE_CREDENTIALS_PATH, 'w') as f:
            json.dump({
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }, f)
        
        print("\n✅ Credentials saved successfully!")
        
        # Test the credentials
        print("\n🔍 Testing credentials...")
        service = build('youtube', 'v3', credentials=credentials)
        
        response = service.channels().list(
            mine=True,
            part='snippet,statistics'
        ).execute()
        
        if response['items']:
            channel = response['items'][0]
            print(f"   Channel: {channel['snippet']['title']}")
            print(f"   Subscribers: {channel['statistics'].get('subscriberCount', 'N/A')}")
            print("\n✅ YouTube authentication complete!")
            return True
        else:
            print("❌ Could not get channel info")
            return False
            
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    
    finally:
        # Clean up temp file
        if temp_secrets.exists():
            temp_secrets.unlink()


def check_existing_credentials():
    """Check if credentials already exist."""
    creds_path = config.YOUTUBE_CREDENTIALS_PATH
    
    if not creds_path.exists():
        return False
    
    try:
        with open(creds_path) as f:
            creds_data = json.load(f)
        
        # Verify required fields
        required = ['token', 'client_id', 'client_secret']
        if all(field in creds_data for field in required):
            # Test if credentials work
            credentials = Credentials.from_authorized_user_info(creds_data, config.YOUTUBE_SCOPES)
            
            if credentials.expired and credentials.refresh_token:
                print("🔄 Refreshing expired credentials...")
                credentials.refresh()
                # Save refreshed credentials
                with open(creds_path, 'w') as f:
                    json.dump({
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes
                    }, f)
            
            # Test connection
            service = build('youtube', 'v3', credentials=credentials)
            response = service.channels().list(mine=True, part='snippet').execute()
            
            if response['items']:
                print(f"✅ Already authenticated!")
                print(f"   Channel: {response['items'][0]['snippet']['title']}")
                return True
        
    except Exception as e:
        print(f"⚠️ Credentials need re-authentication: {e}")
    
    return False


def main():
    """Main entry point."""
    print("\n🐱 YouTube Shorts Automation - OAuth Setup\n")
    
    # Check existing credentials
    if check_existing_credentials():
        print("\nYou can run videos now!")
        sys.exit(0)
    
    # Run new OAuth flow
    if run_oauth_flow():
        print("\n" + "=" * 60)
        print("🎉 Setup complete! You can now run the automation.")
        print("=" * 60)
    else:
        print("\n❌ Setup failed. Please check the instructions above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
