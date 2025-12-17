"""
Google AI Generator for TrendMaster
Uses Gemini 3, Nano Banana Pro (Gemini 3 Pro Image), and Veo 3.1 (Video) APIs
"""
import google.generativeai as genai
from google import genai as genai_new  # New SDK for image and video generation
from google.genai import types as genai_types
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()


class GoogleAIGenerator:
    def __init__(self):
        """Initialize Google AI client"""
        api_key = os.getenv('GOOGLE_API_KEY')

        if not api_key:
            print("⚠️ GOOGLE_API_KEY not found in environment")
            self.client = None
            self.new_client = None
        else:
            try:
                genai.configure(api_key=api_key)

                # Initialize models
                self.text_model_name = os.getenv('GEMINI_TEXT_MODEL', 'gemini-3-pro-preview')
                self.image_model_name = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-3-pro-image-preview')
                self.video_model_name = os.getenv('GEMINI_VIDEO_MODEL', 'veo-3.1-generate-preview')

                # Test connection with Gemini 3 (old API for text)
                self.text_model = genai.GenerativeModel(self.text_model_name)

                # Initialize new client for image/video (Nano Banana, Veo)
                self.new_client = genai_new.Client(api_key=api_key)

                print("✅ Google AI API initialized")
                print(f"   • Text: {self.text_model_name}")
                print(f"   • Image: {self.image_model_name} (Nano Banana)")
                print(f"   • Video: {self.video_model_name}")
            except Exception as e:
                print(f"❌ Google AI initialization failed: {e}")
                self.client = None
                self.new_client = None

    def generate_facebook_posts(self, trend_topic: str, source: str, metadata: str = "") -> List[str]:
        """
        Generate 3 Facebook post variations using Gemini 3

        Args:
            trend_topic: The trending topic
            source: Source of the trend
            metadata: Additional context

        Returns:
            List of 3 generated Facebook posts
        """
        if not hasattr(self, 'text_model'):
            return [
                f"❌ Google AI nem elérhető\n\nTéma: {trend_topic}",
                f"❌ Google AI nem elérhető\n\nTéma: {trend_topic}",
                f"❌ Google AI nem elérhető\n\nTéma: {trend_topic}"
            ]

        prompt = f"""
        Készíts 3 különböző Facebook posztot a következő trending témáról.

        TÉMA: {trend_topic}
        FORRÁS: {source}
        EXTRA INFO: {metadata}

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
           - 200-350 karakter összesen (részletesebb, informatívabb)
           - Jól strukturált, koherens mondatok
           - Könnyen olvasható, de tartalmas
           - Húzónevek/kulcsszavak kiemelése
           - Releváns részletek, adatok, összefüggések bemutatása

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
            response = self.text_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.8,
                    'max_output_tokens': 800,
                }
            )

            # Parse response
            response_text = response.text.strip()

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

            print(f"✅ Generated {len(posts)} Facebook posts for: {trend_topic[:50]}... (via Gemini 3)")

            return posts[:3]

        except Exception as e:
            print(f"❌ Error generating posts with Gemini 3: {e}")
            # Fallback posts
            return [
                f"📊 **{trend_topic}**\n\nEz a téma most a figyelem középpontjában! Érdemes figyelni.",
                f"🔥 {trend_topic}\n\nAz emberek ezt keresik most! Mit gondolsz, miért lehet ennyire aktuális?",
                f"💡 **Trending most**: {trend_topic}\n\nÉrdekes kérdés, hogy ez hogyan hat a jövőre."
            ]

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Gemini 3 (generic text generation)

        Args:
            prompt: The prompt to generate text from

        Returns:
            Generated text string
        """
        if not hasattr(self, 'text_model'):
            return "❌ Google AI nem elérhető"

        try:
            print(f"📝 Generating text with Gemini 3: {prompt[:50]}...")

            response = self.text_model.generate_content(prompt)

            if response and response.text:
                return response.text.strip()
            else:
                return "❌ Nem sikerült szöveget generálni"

        except Exception as e:
            print(f"❌ Error generating text with Gemini 3: {e}")
            return f"❌ Hiba a szöveg generálás során: {str(e)}"

    def generate_image(self, prompt: str) -> str:
        """
        Generate an image using Nano Banana Pro (Gemini 3 Pro Image)
        Uses the new google.genai SDK with response_modalities=['TEXT', 'IMAGE']

        Args:
            prompt: Text description for image generation

        Returns:
            Path to the generated image file (to be served via Flask)
        """
        if not self.new_client:
            print("⚠️ Google AI new client not available, using fallback")
            return "https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1000"

        try:
            print(f"🎨 Generating image with Nano Banana (Gemini 3 Pro Image): {prompt[:50]}...")

            import tempfile
            import uuid

            # Clean the prompt for safety filters
            import re
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"
                u"\U0001F300-\U0001F5FF"
                u"\U0001F680-\U0001F6FF"
                u"\U0001F1E0-\U0001F1FF"
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE)
            clean_prompt = emoji_pattern.sub('', prompt)
            clean_prompt = re.sub(r'\*\*|\*|__|_|`|#', '', clean_prompt)
            clean_prompt = re.sub(r'[<>{}[\]|\\^~]', '', clean_prompt).strip()

            full_prompt = f"Create a professional, cinematic image: {clean_prompt}. High quality, photorealistic style."

            # Use new SDK for image generation
            response = self.new_client.models.generate_content(
                model=self.image_model_name,  # "gemini-3-pro-image-preview"
                contents=[full_prompt],
                config=genai_types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                    image_config=genai_types.ImageConfig(
                        aspect_ratio="1:1",
                        image_size="2K"
                    ),
                )
            )

            # Extract and save image from response
            temp_dir = tempfile.gettempdir()
            temp_filename = f"nano_banana_{uuid.uuid4()}.png"
            temp_path = os.path.join(temp_dir, temp_filename)

            for part in response.parts:
                if part.text is not None:
                    print(f"   Gemini: {part.text[:100]}...")
                elif image := part.as_image():
                    image.save(temp_path)
                    print(f"✅ Image generated successfully with Nano Banana")
                    return temp_path

            raise ValueError("No image generated in response")

        except Exception as e:
            print(f"❌ Nano Banana image generation failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback image
            return "https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1000"

    def generate_video(self, prompt: str, duration: int = 5) -> str:
        """
        Generate a video using Veo 3.1

        Args:
            prompt: Text description for video generation
            duration: Video duration in seconds (4, 6, or 8)

        Returns:
            Path to the generated video file
        """
        try:
            import tempfile
            import uuid

            print(f"🎬 Generating video with Veo 3.1: {prompt[:50]}...")

            # Map duration to allowed values (4, 6, 8 seconds)
            allowed_durations = {4: "4", 5: "4", 6: "6", 8: "8"}
            duration_str = str(allowed_durations.get(duration, "4"))
            if duration not in [4, 5, 6, 8]:
                print(f"⚠️ Duration {duration}s not allowed, using 4s instead")

            # Clean prompt: Remove emojis, markdown, and special formatting
            # Veo 3.1 generates audio natively, so clean text works better
            import re
            cleaned_prompt = prompt

            # Remove emojis
            cleaned_prompt = re.sub(r'[^\w\s\.,!?\-áéíóöőúüűÁÉÍÓÖŐÚÜŰ]', '', cleaned_prompt)

            # Remove markdown formatting
            cleaned_prompt = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_prompt)  # **bold**
            cleaned_prompt = re.sub(r'\*([^*]+)\*', r'\1', cleaned_prompt)      # *italic*

            # Clean up extra spaces
            cleaned_prompt = ' '.join(cleaned_prompt.split())

            print(f"🧹 Cleaned prompt: {cleaned_prompt[:80]}...")

            # Initialize new GenAI client for Veo
            api_key = os.getenv('GOOGLE_API_KEY')
            client = genai_new.Client(api_key=api_key)

            # Step 1: Create video generation job
            print(f"📤 Creating Veo 3.1 video job...")
            operation = client.models.generate_videos(
                model=self.video_model_name,  # "veo-3.1-generate-preview"
                prompt=f"Professional social media video: {cleaned_prompt}",
                config=genai_new.types.GenerateVideosConfig(
                    duration_seconds=duration_str,
                    aspect_ratio="16:9",
                    resolution="720p"
                )
            )

            print(f"✅ Video job created: {operation.name}")

            # Step 2: Poll operation status until completed
            max_wait_time = 360  # 6 minutes max
            start_time = time.time()
            poll_interval = 10  # Check every 10 seconds

            while not operation.done:
                if time.time() - start_time > max_wait_time:
                    print(f"❌ Video generation timed out after {max_wait_time}s")
                    return None

                print(f"⏳ Waiting for video generation to complete...")
                time.sleep(poll_interval)

                # Refresh operation status
                operation = client.operations.get(operation)

            print(f"✅ Video generation completed!")

            # Step 3: Check if video was filtered by safety system
            if hasattr(operation.response, 'rai_media_filtered_count') and operation.response.rai_media_filtered_count and operation.response.rai_media_filtered_count > 0:
                print(f"🚫 Video generation blocked by Veo safety filter!")
                if hasattr(operation.response, 'rai_media_filtered_reasons'):
                    for reason in operation.response.rai_media_filtered_reasons:
                        print(f"   📋 {reason}")
                return None

            # Check if generated_videos exists and is not empty
            if not operation.response or not hasattr(operation.response, 'generated_videos'):
                print(f"❌ No generated_videos in response")
                return None

            if not operation.response.generated_videos:
                print(f"❌ generated_videos is empty")
                return None

            generated_video = operation.response.generated_videos[0]

            temp_dir = tempfile.gettempdir()
            temp_filename = f"veo3_{uuid.uuid4()}.mp4"
            temp_path = os.path.join(temp_dir, temp_filename)

            print(f"📥 Downloading video...")
            client.files.download(file=generated_video.video)
            generated_video.video.save(temp_path)

            print(f"✅ Video generated successfully with Veo 3.1")
            print(f"   Saved to: {temp_path}")

            return temp_path

        except Exception as e:
            print(f"❌ Veo 3.1 video generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_video_prompt_from_post(self, post_text: str) -> str:
        """
        Generate a clean video prompt from Facebook post text

        Args:
            post_text: The Facebook post text

        Returns:
            A clean, simple visual description for Veo 3.1
        """
        if not hasattr(self, 'text_model'):
            return "Egy szép tájkép napfelkeltekor."

        prompt = f"""
        Alakítsd át ezt a Facebook post szöveget egy egyszerű, rövid vizuális leírássá videó generáláshoz.

        KÖVETELMÉNYEK:
        - Maximum 80 karakter
        - Nincs emoji, markdown formatting, speciális karakter
        - Nincs valós személy neve (politikusok, celebrityek)
        - Egyszerű, konkrét vizuális jelenet leírása
        - Magyar nyelven
        - Csak egy egyszerű mondat vagy két rövid mondat

        PÉLDÁK:
        Post: "🔥 **Trump béketerve** – politikai vihar közeleg!"
        Videó prompt: "Diplomáciai tárgyalás egy modern irodában, emberek vitatkoznak."

        Post: "Új gazdasági válság jöhet! 📊 Mit gondolsz?"
        Videó prompt: "Egy tőzsde kereskedési terem, monitor grafikonokkal."

        Post: "Gyönyörű napfelkelte a hegyekben! 🏔️✨"
        Videó prompt: "Napfelkelte a havas hegyek felett, arany fény."

        FACEBOOK POST:
        {post_text}

        Válasz CSAK a videó prompttal, semmi mással! Ne írj semmilyen magyarázatot!
        """

        try:
            response = self.text_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 100,
                }
            )

            # Clean response
            video_prompt = response.text.strip()

            # Remove any quotes if present
            video_prompt = video_prompt.strip('"').strip("'")

            # Limit to 80 characters
            if len(video_prompt) > 80:
                video_prompt = video_prompt[:77] + "..."

            print(f"✅ Generated video prompt: {video_prompt}")

            return video_prompt

        except Exception as e:
            print(f"❌ Error generating video prompt: {e}")
            return "Egy dinamikus jelenet modern környezetben."

    def generate_posts_batch(self, trends: List[Dict], max_trends: int = 5) -> Dict[int, List[str]]:
        """
        Generate posts for multiple trends using Gemini 3

        Args:
            trends: List of trend dictionaries
            max_trends: Maximum number of trends to process

        Returns:
            Dictionary mapping trend_id to list of posts
        """
        results = {}

        for idx, trend in enumerate(trends[:max_trends]):
            print(f"\n🤖 Generating posts {idx+1}/{min(len(trends), max_trends)} (Gemini 3)")

            trend_id = trend.get('id')
            topic = trend.get('topic', 'Unknown topic')
            source = trend.get('source', 'unknown')
            metadata = trend.get('metadata', '')

            posts = self.generate_facebook_posts(topic, source, metadata)
            results[trend_id] = posts

            # Rate limiting for Google AI
            time.sleep(1)

        return results
