"""
Trend Collector for TrendMaster
Collects trending topics from Google Trends and YouTube
"""
from pytrends.request import TrendReq
from googleapiclient.discovery import build
from datetime import datetime
from typing import List, Dict
import os
import time


class TrendCollector:
    def __init__(self):
        """Initialize trend collector with API keys"""
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = None

        if self.youtube_api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
                print("✅ YouTube API initialized")
            except Exception as e:
                print(f"⚠️ YouTube API initialization failed: {e}")

        # Initialize pytrends
        try:
            self.pytrends = TrendReq(hl='en-US', tz=360)
            print("✅ PyTrends initialized")
        except Exception as e:
            print(f"⚠️ PyTrends initialization failed: {e}")
            self.pytrends = None

    def collect_google_trends(self, country_code: str = 'HU') -> List[Dict]:
        """
        Collect Google Trends for specified country
        NOTE: PyTrends API deprecated, using Google News RSS instead
        This is handled by news_collector.py now
        """
        print(f"ℹ️ Google Trends collection moved to Google News RSS (see news_collector.py)")
        return []

    def collect_youtube_trending(self, region_code: str = 'HU') -> List[Dict]:
        """
        Collect YouTube trending videos
        region_code: HU, US, GB
        """
        if not self.youtube:
            print(f"⚠️ YouTube API not available for {region_code}")
            return []

        trends = []
        source_name = f'youtube_{region_code.lower()}'

        try:
            print(f"📡 Fetching YouTube Trending for {region_code}...")

            # Get trending videos
            request = self.youtube.videos().list(
                part='snippet,statistics',
                chart='mostPopular',
                regionCode=region_code,
                maxResults=10
            )
            response = request.execute()

            for rank, item in enumerate(response.get('items', []), 1):
                snippet = item['snippet']
                stats = item['statistics']

                # Extract topic from title
                topic = snippet['title']

                # Calculate relevance score based on views and engagement
                view_count = int(stats.get('viewCount', 0))
                like_count = int(stats.get('likeCount', 0))
                comment_count = int(stats.get('commentCount', 0))

                # Simple engagement score
                engagement_score = (like_count + comment_count) / max(view_count, 1) * 10000

                trends.append({
                    'source': source_name,
                    'topic': topic,
                    'rank': rank,
                    'relevance_score': engagement_score,
                    'metadata': f'Views: {view_count:,} | Likes: {like_count:,} | Channel: {snippet["channelTitle"]}'
                })

            print(f"✅ Collected {len(trends)} YouTube trends from {region_code}")
            time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"❌ Error collecting YouTube trends for {region_code}: {e}")

        return trends

    def collect_all_trends(self) -> Dict[str, List[Dict]]:
        """
        Collect all trends from all sources
        Returns dictionary with source as key
        """
        print(f"\n{'='*60}")
        print(f"🔥 TRENDMASTER - TREND COLLECTION STARTED")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        all_trends = {}

        # Google Trends - HU, UK, US
        for country in ['HU', 'GB', 'US']:
            try:
                trends = self.collect_google_trends(country)
                if trends:
                    all_trends[f'google_{country.lower()}'] = trends
            except Exception as e:
                print(f"❌ Failed to collect Google Trends for {country}: {e}")

        # YouTube Trending - HU, GB, US
        for region in ['HU', 'GB', 'US']:
            try:
                trends = self.collect_youtube_trending(region)
                if trends:
                    all_trends[f'youtube_{region.lower()}'] = trends
            except Exception as e:
                print(f"❌ Failed to collect YouTube trends for {region}: {e}")

        total_trends = sum(len(trends) for trends in all_trends.values())
        print(f"\n✅ Collection complete! Total trends: {total_trends}")
        print(f"{'='*60}\n")

        return all_trends

    def get_flat_trends_list(self) -> List[Dict]:
        """Get all trends as flat list"""
        all_trends = self.collect_all_trends()
        flat_list = []
        for trends in all_trends.values():
            flat_list.extend(trends)
        return flat_list
