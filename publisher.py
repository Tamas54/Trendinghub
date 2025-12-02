"""
Social Media Publisher for TrendMaster
Publishes posts to Facebook via Nango Proxy
"""
import requests
import os
import tempfile
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SocialPublisher:
    def __init__(self):
        """Initialize Nango connection and optional media spoofer"""
        self.nango_secret = os.getenv('NANGO_SECRET_KEY')
        self.nango_url = os.getenv('NANGO_SERVER_URL', 'https://api.nango.dev')

        # Optional: Initialize media spoofer for EXIF manipulation
        try:
            from media_spoofer import MediaSpoofer
            self.spoofer = MediaSpoofer()
            self.has_spoofer = True
        except ImportError:
            self.spoofer = None
            self.has_spoofer = False

    def publish_to_facebook(self, connection_id: str, message: str, image_url: str = None) -> Dict[str, Any]:
        """
        Publish content to Facebook via Nango Proxy

        Args:
            connection_id: Nango connection ID for Facebook
            message: Post text content
            image_url: Optional image URL to attach

        Returns:
            Dictionary with success status and result
        """
        if not self.nango_secret:
            return {"success": False, "error": "Nango Secret Key missing"}

        # Nango Proxy Endpoint for Facebook Page Feed
        # Using /photos endpoint if image exists, else /feed
        if image_url:
            endpoint = "/proxy/facebook-pages/v18.0/me/photos"
            payload = {"url": image_url, "message": message}
        else:
            endpoint = "/proxy/facebook-pages/v18.0/me/feed"
            payload = {"message": message}

        url = f"{self.nango_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.nango_secret}",
            "Connection-Id": connection_id,
            "Provider-Config-Key": "facebook-pages",
            "Content-Type": "application/json"
        }

        try:
            print(f"🚀 Publishing to Facebook via Nango... ({endpoint})")
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                return {"success": True, "id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_and_spoof_image(self, image_url: str, device_key: str = "random") -> str:
        """
        Download an image from URL and apply EXIF spoofing

        NOTE: This requires a storage solution (S3, local server, etc.) to upload
        the spoofed image and get a new URL. Currently returns the original URL.

        To enable full spoofing:
        1. Download image from URL
        2. Apply EXIF spoofing with self.spoofer.spoof_photo()
        3. Upload spoofed image to storage (S3, Firebase, etc.)
        4. Return new URL

        Args:
            image_url: Original image URL
            device_key: Device profile for EXIF data

        Returns:
            New URL of spoofed image (currently returns original)
        """
        if not self.has_spoofer:
            print("⚠️ Media spoofer not available")
            return image_url

        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to download image: {response.status_code}")
                return image_url

            # Save to temp file
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"temp_image_{os.getpid()}.jpg")

            with open(temp_path, 'wb') as f:
                f.write(response.content)

            # Apply EXIF spoofing
            success = self.spoofer.spoof_photo(temp_path, device_key=device_key)

            if not success:
                print("❌ Failed to spoof image EXIF")
                os.remove(temp_path)
                return image_url

            print(f"✅ Image EXIF spoofed successfully ({device_key})")

            # TODO: Upload spoofed image to storage and get new URL
            # For now, just clean up and return original URL
            #
            # Example with S3:
            # import boto3
            # s3 = boto3.client('s3')
            # s3.upload_file(temp_path, 'bucket-name', 'spoofed_image.jpg')
            # new_url = f"https://bucket-name.s3.amazonaws.com/spoofed_image.jpg"
            # os.remove(temp_path)
            # return new_url

            os.remove(temp_path)
            return image_url

        except Exception as e:
            print(f"❌ Error in download_and_spoof_image: {e}")
            return image_url
