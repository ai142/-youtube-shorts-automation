"""
Hashtag and title generator using OpenAI.
Generates engaging, viral-optimized content metadata.
"""
import os
import json
from typing import List, Dict, Optional
import config
from database import get_database

# Initialize OpenAI client
client = None
try:
    from openai import OpenAI
    api_key = config.get_env('OPENAI_API_KEY')
    if api_key:
        client = OpenAI(api_key=api_key)
except (ImportError, Exception) as e:
    print(f"Warning: OpenAI client not available: {e}")


class HashtagGenerator:
    """Generate hashtags, titles, and descriptions using OpenAI."""
    
    # Viral cat-related hashtags for YouTube Shorts
    BASE_HASHTAGS = [
        '#catsoftiktok', '#catlover', '#cattok', '#funnycat', '#cutekitten',
        '#petlife', '#viral', '#fyp', '#foryou', '#trending', '#cats',
        '#meow', '#catvideo', '#funnyvideos', '#cutecat', '#catmemes',
        '#kitty', '#kitten', '#catcomedy', '#catfail', '#adorable'
    ]
    
    def __init__(self):
        self.client = client
    
    async def generate_hashtags(self, category: str, count: int = None) -> List[str]:
        """Generate trending hashtags for the video category."""
        count = count or config.MAX_HASHTAGS
        count = max(config.MIN_HASHTAGS, min(count, config.MAX_HASHTAGS))
        
        # Try OpenAI generation first
        if self.client:
            try:
                hashtags = await self._generate_with_openai(category, count)
                if hashtags:
                    return hashtags
            except Exception as e:
                db = await get_database()
                await db.log_activity('hashtag_generation', 
                    f"OpenAI failed: {str(e)}", success=False)
        
        # Fallback to template-based generation
        return self._generate_fallback_hashtags(category, count)
    
    async def _generate_with_openai(self, category: str, count: int) -> List[str]:
        """Generate hashtags using OpenAI API."""
        prompt = f"""Generate {count} YouTube Shorts hashtags for a viral {category} video.
        
Requirements:
- Include mix of popular (#viral, #fyp, #trending) and niche cat hashtags
- Total {count} hashtags
- Return ONLY hashtags separated by spaces, no other text
- Use trending TikTok/YouTube Shorts format

Example: #catsoftiktok #cutekitten #viral #fyp #meow #funnycat #foryou"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a social media expert specializing in viral YouTube Shorts content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        hashtags = [h.strip() for h in content.split() if h.startswith('#')]
        
        # Ensure we have the right count
        while len(hashtags) < count:
            hashtags.extend(self.BASE_HASHTAGS[:count - len(hashtags)])
        
        return hashtags[:count]
    
    def _generate_fallback_hashtags(self, category: str, count: int) -> List[str]:
        """Generate hashtags using template-based approach."""
        # Select random base hashtags
        import random
        selected = random.sample(self.BASE_HASHTAGS, min(count, len(self.BASE_HASHTAGS)))
        
        # Add category-specific hashtags
        category_tags = {
            'funny': ['#funnycat', '#catcomedy', '#catmemes', '#funnyvideos'],
            'cute': ['#cutecat', '#adorable', '#sweetkitty', '#cutekitten'],
            'fail': ['#catfail', '#fail', '#oops', '#embarrassed'],
            'sleeping': ['#sleepingcat', '#sleepykitty', '#nap time', '#cozy'],
            'playing': ['#playfulcat', '#funnyvideos', '#toys', '#playtime'],
        }
        
        for key, tags in category_tags.items():
            if key in category.lower():
                selected.extend(tags)
        
        return list(set(selected))[:count]
    
    async def generate_title(self, category: str, video_id: str) -> str:
        """Generate an engaging, click-worthy title."""
        if self.client:
            try:
                title = await self._generate_title_with_openai(category, video_id)
                if title:
                    return title
            except Exception as e:
                db = await get_database()
                await db.log_activity('title_generation',
                    f"OpenAI failed: {str(e)}", success=False)
        
        return self._generate_fallback_title(category)
    
    async def _generate_title_with_openai(self, category: str, video_id: str) -> str:
        """Generate title using OpenAI."""
        prompt = f"""Generate a catchy YouTube Shorts title for a {category} video.
        
Requirements:
- 30-100 characters
- Include emoji if appropriate
- Make it curiosity-inducing and clickable
- Use capital letters for important words
- Add numbers if relevant (e.g., "will make you LAUGH", "can't stop watching")

Example: "😱 This Cat's Reaction is UNBELIEVABLE!" """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a viral YouTube title expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.9
        )
        
        title = response.choices[0].message.content.strip()
        
        # Ensure title is within length limits
        if len(title) > config.TITLE_MAX_LENGTH:
            title = title[:config.TITLE_MAX_LENGTH - 3] + "..."
        
        return title
    
    def _generate_fallback_title(self, category: str) -> str:
        """Generate title using templates."""
        import random
        
        templates = [
            "😱 {category} - You CAN'T MISS THIS!",
            "POV: Your cat when {category}",
            "This {category} is HILARIOUS! 🐱",
            "Watch this {category} until the END!",
            "The cutest {category} you'll see today!",
            "{category} that will make your day!",
        ]
        
        template = random.choice(templates)
        category_clean = category.replace('cat ', '').replace('cat', '').strip()
        title = template.format(category=f"{category_clean} cat" if category_clean else "cat")
        
        return title
    
    async def generate_description(self, title: str, hashtags: List[str],
                                   category: str) -> str:
        """Generate video description."""
        if self.client:
            try:
                desc = await self._generate_description_with_openai(title, category)
                if desc:
                    return desc
            except Exception as e:
                db = await get_database()
                await db.log_activity('description_generation',
                    f"OpenAI failed: {str(e)}", success=False)
        
        return self._generate_fallback_description(title, hashtags, category)
    
    async def _generate_description_with_openai(self, title: str, category: str) -> str:
        """Generate description using OpenAI."""
        prompt = f"""Generate a YouTube Shorts description for a video titled "{title}" about {category}.

Requirements:
- 100-300 characters
- Include call to action (like, comment, subscribe)
- Add hashtags at the end
- Be engaging and friendly"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a social media content creator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_fallback_description(self, title: str, hashtags: List[str],
                                       category: str) -> str:
        """Generate description using templates."""
        hashtag_str = ' '.join(hashtags[:5])
        
        description = f"""🐱 {title}

Watch this adorable {category}! 

👍 Like if you enjoyed!
💬 Comment below what you think!
📤 Share with a friend who loves cats!
🔔 Subscribe for more cute cat content!

{hashtag_str}

#Shorts #CatVideos #PetTok"""
        
        return description
    
    async def generate_all(self, category: str, video_id: str) -> Dict:
        """Generate all metadata at once."""
        hashtags = await self.generate_hashtags(category)
        title = await self.generate_title(category, video_id)
        description = await self.generate_description(title, hashtags, category)
        
        return {
            'title': title,
            'description': description,
            'hashtags': hashtags,
            'hashtag_string': ' '.join(hashtags)
        }


async def generate_metadata(category: str, video_id: str) -> Dict:
    """Convenience function to generate all metadata."""
    generator = HashtagGenerator()
    return await generator.generate_all(category, video_id)
