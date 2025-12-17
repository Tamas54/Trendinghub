"""
Facebook Post Generator for TrendMaster
Uses OpenAI API to generate engaging Facebook posts
"""
from openai import OpenAI
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GPT-5 models (latest generation)
OPENAI_MODEL = 'gpt-5-mini'  # Primary model for post generation
OPENAI_TEXT_MODEL = 'gpt-5-mini'  # Model for text generation


def get_rag_style_context(topic: str) -> str:
    """
    Get RAG style context for a given topic.
    Returns empty string if RAG store is not available or has no data.
    """
    try:
        from rag_store import get_rag_store
        rag_store = get_rag_store()
        context = rag_store.get_style_context(topic, max_tokens=800)
        if context:
            print(f"🎭 RAG style context added ({len(context)} chars)")
        return context
    except Exception as e:
        # RAG store not available or error - silently continue without it
        return ""


class PostGenerator:
    def __init__(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            print("⚠️ OPENAI_API_KEY not found in environment")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                print("✅ OpenAI API initialized")
            except Exception as e:
                print(f"❌ OpenAI initialization failed: {e}")
                self.client = None

    def generate_facebook_posts(self, trend_topic: str, source: str, metadata: str = "") -> List[str]:
        """
        Generate 3 Facebook post variations for a trend

        Args:
            trend_topic: The trending topic
            source: Source of the trend (e.g., google_hu, youtube_us)
            metadata: Additional context about the trend

        Returns:
            List of 3 generated Facebook posts
        """
        if not self.client:
            return [
                f"❌ OpenAI API nem elérhető\n\nTéma: {trend_topic}",
                f"❌ OpenAI API nem elérhető\n\nTéma: {trend_topic}",
                f"❌ OpenAI API nem elérhető\n\nTéma: {trend_topic}"
            ]

        # ALWAYS generate in Hungarian (for Hungarian government official)
        language = "magyar"

        # Get RAG style context if available
        rag_context = get_rag_style_context(trend_topic)

        prompt = f"""
        Készíts 3 különböző Facebook posztot a következő trending témáról.

        TÉMA: {trend_topic}
        FORRÁS: {source}

        RÉSZLETES TARTALOM (HASZNÁLD EZT A POSZT MEGÍRÁSÁHOZ!):
        {metadata}

        {rag_context}

        ⚠️ KÖTELEZŐ: Használd fel a fenti RÉSZLETES TARTALOM információit a poszt megírásához! Ne csak a címre hagyatkozz!

        ⚠️ FONTOS: A posztokat MINDIG MAGYAR NYELVEN írd, még akkor is, ha a téma angol nyelvű!
        Ha a téma angol, fordítsd le a tartalmat magyarra, de úgy, hogy érthető és természetes legyen.

        KÖVETELMÉNYEK (KÖTELEZŐ):

        1. **CÉLKÖZÖNSÉG**: Kormánybiztosnak szánt tartalom
           - Professzionális, de barátságos hangnem
           - Humoros, de méltóságteljes
           - Informatív és lényegre törő
           - Szakmai hitelességet sugall

        2. **FACEBOOK ALGORITMUS BARÁT ELEMEK**:
           - Használj 2-3 jól megválasztott emojit (nem túl sok!)
           - Alkalmazz **vastag betűs** kiemeléseket a lényeges pontoknál
           - Használj különleges karaktereket mértékkel (✓, →, •)
           - Kérdéseket vagy felkiáltásokat a bevonzásért

        3. **SZERKEZET**:
           - Figyelemfelkeltő első mondat (hook)
           - 3-4 informatív mondatban részletesen fejtsd ki a témát
           - Kontextus: miért fontos ez most, milyen hatásai vannak
           - Érzelmi kapcsolódási pont vagy perspektíva
           - Gondolatébresztő lezárás vagy kérdés

        4. **HOSSZ ÉS STÍLUS**:
           - 500-800 karakter összesen (részletesebb, informatívabb, tartalmas)
           - Jól strukturált, koherens mondatok
           - Könnyen olvasható, de tartalmas
           - Húzónevek/kulcsszavak kiemelése
           - Releváns részletek, adatok, összefüggések bemutatása
           - Legyen elég hosszú ahhoz, hogy értékes információt adjon!

        5. **POLITIKAI TARTALOM**: MEGENGEDETT
           - Objektív, tényszerű megközelítés
           - Kiegyensúlyozott álláspont
           - Több nézőpont bemutatása

        6. **HÁROM KÜLÖNBÖZŐ STÍLUS**:
           - **1. poszt**: Informatív, profi, tényközpontú
           - **2. poszt**: Humoros, közérthető, relatable
           - **3. poszt**: Gondolatébresztő, elemző, stratégiai

        FONTOS:
        - NE használj hashtag-eket (#)
        - NE írj link placeholder-eket
        - NE használj túl sok emojit (max 3 összesen)
        - NE legyél túl formális vagy unalmas

        VÁLASZ FORMÁTUM (PONTOSAN ÍGY):
        ---POST1---
        [első poszt szövege]
        ---POST2---
        [második poszt szövege]
        ---POST3---
        [harmadik poszt szövege]
        """

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,  # GPT-5 mini - latest generation
                messages=[
                    {
                        "role": "system",
                        "content": """Te egy szakértő közösségi média menedzser vagy, aki kormánybiztosok számára készít professzionális, de engaging Facebook posztokat.

FONTOS KÖVETELMÉNYEK:
• Érted a Facebook ALGORITMUSÁT és tudod, hogyan kell olyan tartalmat készíteni, ami tetszik mind az ALGORITMUSNAK, mind a KÖZÖNSÉGNEK
• Használj TÖBB EMOJIT, mivel ez Facebook poszt - az emojik növelik az engagement-et
• A poszt szakmailag hiteles maradjon, de legyen érdekes és figyelemfelkeltő
• MINDEN posztot KÖTELEZŐEN ezzel a mondattal fejezd be: "link a kommentben"

STÍLUS: Professzionális, de barátságos és engaging. Emojikkal fokozd a figyelmet és az olvashatóságot."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                # GPT-5-mini only supports default temperature (1), don't set it
                max_completion_tokens=2000  # Enough for 3 detailed posts of 500-800 chars each
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()

            # Extract posts
            posts = []
            parts = response_text.split('---POST')

            for part in parts[1:]:  # Skip first empty part
                # Extract content between --- markers
                content = part.split('---')[1].strip() if '---' in part else part.strip()

                # Clean up post
                content = content.replace('POST1', '').replace('POST2', '').replace('POST3', '')
                content = content.strip()

                if content:
                    posts.append(content)

            # Ensure we have exactly 3 posts
            while len(posts) < 3:
                posts.append(f"📢 {trend_topic}\n\nEz a téma most felkapott! Mit gondolsz róla?")

            print(f"✅ Generated {len(posts)} Facebook posts for: {trend_topic[:50]}...")

            return posts[:3]

        except Exception as e:
            print(f"❌ Error generating posts: {e}")
            # Fallback posts
            return [
                f"📊 **{trend_topic}**\n\nEz a téma most a figyelem középpontjában! Érdemes figyelni.",
                f"🔥 {trend_topic}\n\nAz emberek ezt keresik most! Mit gondolsz, miért lehet ennyire aktuális?",
                f"💡 **Trending most**: {trend_topic}\n\nÉrdekes kérdés, hogy ez hogyan hat a jövőre."
            ]

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using GPT-4 (generic text generation)

        Args:
            prompt: The prompt to generate text from

        Returns:
            Generated text string
        """
        if not self.client:
            return "❌ OpenAI API nem elérhető"

        try:
            print(f"📝 Generating text with {OPENAI_TEXT_MODEL}: {prompt[:50]}...")

            response = self.client.chat.completions.create(
                model=OPENAI_TEXT_MODEL,  # GPT-5 mini
                messages=[
                    {"role": "system", "content": "Te egy kreatív tartalomíró vagy, aki social media posztokat és videó scripteket készít."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1000  # GPT-5 uses max_completion_tokens, no temperature support
            )

            if response.choices:
                return response.choices[0].message.content.strip()
            else:
                return "❌ Nem sikerült szöveget generálni"

        except Exception as e:
            print(f"❌ Error generating text with GPT-4: {e}")
            return f"❌ Hiba a szöveg generálás során: {str(e)}"

    def generate_posts_batch(self, trends: List[Dict], max_trends: int = 5) -> Dict[int, List[str]]:
        """
        Generate posts for multiple trends

        Args:
            trends: List of trend dictionaries
            max_trends: Maximum number of trends to process

        Returns:
            Dictionary mapping trend_id to list of posts
        """
        results = {}

        for idx, trend in enumerate(trends[:max_trends]):
            print(f"\n🤖 Generating posts {idx+1}/{min(len(trends), max_trends)}")

            trend_id = trend.get('id')
            topic = trend.get('topic', 'Unknown topic')
            source = trend.get('source', 'unknown')
            metadata = trend.get('metadata', '')

            posts = self.generate_facebook_posts(topic, source, metadata)
            results[trend_id] = posts

        return results

    def generate_image_prompt(self, post_text: str) -> str:
        """
        Generate an optimized image prompt from post text using GPT-5

        Args:
            post_text: The social media post text

        Returns:
            Optimized image prompt for AI image generation
        """
        if not self.client:
            return f"Social media visual for: {post_text[:200]}"

        try:
            print(f"📝 Generating image prompt from post...")

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """Te egy AI képgeneráló prompt szakértő vagy. A feladatod, hogy social media posztokból készíts optimalizált képgeneráló promptokat.

A prompt legyen:
- Angol nyelvű (a legjobb képgenerátorok angolul működnek)
- Vizuálisan leíró és konkrét
- Stílus megjelöléssel (pl. "professional photography", "digital illustration", "minimalist design")
- Színek és hangulat megjelölésével
- Max 100 szavas"""
                    },
                    {
                        "role": "user",
                        "content": f"Készíts egy képgeneráló promptot ehhez a poszthoz:\n\n{post_text}\n\nCsak a promptot írd, semmi mást!"
                    }
                ],
                max_completion_tokens=1000  # GPT-5 uses reasoning tokens too, needs more space
            )

            prompt = response.choices[0].message.content.strip()
            print(f"✅ Image prompt generated: {prompt[:50]}...")
            return prompt
        except Exception as e:
            print(f"❌ Error generating image prompt: {e}")
            return f"Professional social media visual representing: {post_text[:100]}"

    def generate_image(self, prompt: str) -> str:
        """
        Generate an image using DALL-E 3 (fallback)

        Args:
            prompt: Text description for image generation

        Returns:
            URL of the generated image
        """
        if not self.client:
            # Return a placeholder if no API key
            print("⚠️ OpenAI API not available, using placeholder image")
            return "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=1000"

        try:
            print(f"🎨 Generating image with DALL-E 3 for: {prompt[:50]}...")
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=f"Social media image for: {prompt}. High quality, professional, engaging style.",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            print(f"✅ Image generated successfully")
            return image_url
        except Exception as e:
            print(f"❌ Image generation failed: {e}")
            # Error fallback
            return "https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1000"

    def generate_video(self, prompt: str, duration: int = 5) -> str:
        """
        Generate a video using OpenAI Sora 2

        Args:
            prompt: Text description for video generation
            duration: Video duration in seconds (4, 8, or 12)

        Returns:
            Path to the generated video file
        """
        if not self.client:
            print("⚠️ OpenAI API not available for video generation")
            return None

        try:
            import requests
            import tempfile
            import uuid
            import time

            print(f"🎬 Generating video with Sora 2: {prompt[:50]}...")

            # Map duration to allowed values
            allowed_durations = {4: "4", 5: "4", 8: "8", 12: "12"}
            seconds_str = allowed_durations.get(duration, "4")
            if duration not in [4, 5, 8, 12]:
                print(f"⚠️ Duration {duration}s not allowed, using 4s instead")

            api_key = os.getenv('OPENAI_API_KEY')

            # Step 1: Create video generation job
            create_url = "https://api.openai.com/v1/videos"
            headers = {
                "Authorization": f"Bearer {api_key}"
            }

            # Use multipart/form-data as per API docs
            files = {
                'model': (None, 'sora-2'),
                'prompt': (None, f"Professional social media video: {prompt}"),
                'seconds': (None, seconds_str),
                'size': (None, '1280x720')
            }

            print(f"📤 Creating video job...")
            create_response = requests.post(create_url, headers=headers, files=files)

            if create_response.status_code != 200:
                print(f"❌ Failed to create video job: {create_response.status_code}")
                print(f"Response: {create_response.text}")
                return None

            job_data = create_response.json()
            video_id = job_data.get('id')
            print(f"✅ Video job created: {video_id}")
            print(f"   Status: {job_data.get('status')}")

            # Step 2: Poll job status until completed
            retrieve_url = f"https://api.openai.com/v1/videos/{video_id}"
            max_wait_time = 300  # 5 minutes max
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                time.sleep(5)  # Check every 5 seconds

                status_response = requests.get(retrieve_url, headers=headers)
                if status_response.status_code != 200:
                    print(f"❌ Failed to check status: {status_response.status_code}")
                    return None

                status_data = status_response.json()
                current_status = status_data.get('status')
                progress = status_data.get('progress', 0)

                print(f"⏳ Status: {current_status} ({progress}%)")

                if current_status == 'completed':
                    # Video is ready!
                    video_url = status_data.get('url')
                    if not video_url:
                        print("❌ No video URL in response")
                        return None

                    # Step 3: Download video
                    print(f"📥 Downloading video from: {video_url[:50]}...")

                    temp_dir = tempfile.gettempdir()
                    temp_filename = f"sora_{uuid.uuid4()}.mp4"
                    temp_path = os.path.join(temp_dir, temp_filename)

                    video_response = requests.get(video_url)
                    with open(temp_path, 'wb') as f:
                        f.write(video_response.content)

                    print(f"✅ Video generated successfully with Sora 2")
                    return temp_path

                elif current_status == 'failed':
                    print(f"❌ Video generation failed")
                    return None

            print(f"❌ Video generation timed out after {max_wait_time}s")
            return None

        except Exception as e:
            print(f"❌ Sora video generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
