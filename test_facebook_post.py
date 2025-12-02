#!/usr/bin/env python3
"""
Teszt script a Facebook poster kipróbálására
"""
from facebook_poster import publish_to_facebook_sync

# Teszt adatok
test_post = """🚀 Teszt poszt Firefox session-nel!

Ez egy automatikus teszt, hogy lássuk működik-e minden."""

test_image = "/home/tamas/ytanalyzer/Fbposztiro/trending-hub/Screenshot from 2025-11-22 15-05-38.png"
test_comment = "Forrás: https://example.com/article"

print("\n" + "="*60)
print("🧪 FACEBOOK POSTER TESZT")
print("="*60)

result = publish_to_facebook_sync(
    post_content=test_post,
    image_path=test_image,
    comment_text=test_comment
)

print("\n" + "="*60)
print("EREDMÉNY:")
print("="*60)
print(f"Success: {result.get('success')}")
print(f"Message: {result.get('message')}")
if result.get('screenshot'):
    print(f"Screenshot: {result.get('screenshot')}")
print("="*60 + "\n")
