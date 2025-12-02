"""
News Collector for TrendMaster
Integrates RSS news sources for trend analysis
"""
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict
import hashlib


# Economic, education and trending news sources
# FOCUSED ON ECONOMICS & EDUCATION (for government official)
NEWS_SOURCES = [
    # Hungarian Economic sources (priority)
    {'name': 'Portfolio', 'url': 'https://www.portfolio.hu/rss/all.xml', 'category': 'Magyar Gazdaság', 'lang': 'hu'},
    {'name': 'HVG Gazdaság', 'url': 'https://hvg.hu/gazdasag/rss', 'category': 'Magyar Gazdaság', 'lang': 'hu'},

    # International Economics
    {'name': 'Bloomberg Markets', 'url': 'https://feeds.bloomberg.com/markets/news.rss', 'category': 'Global Markets', 'lang': 'en'},
    {'name': 'Bloomberg Economics', 'url': 'https://feeds.bloomberg.com/economics/news.rss', 'category': 'Economics', 'lang': 'en'},
    {'name': 'Financial Times', 'url': 'https://www.ft.com/rss/home', 'category': 'Finance & Economics', 'lang': 'en'},
    {'name': 'Reuters Business', 'url': 'https://feeds.reuters.com/reuters/businessNews', 'category': 'Business News', 'lang': 'en'},
    {'name': 'The Economist', 'url': 'https://www.economist.com/finance-and-economics/rss.xml', 'category': 'Economic Analysis', 'lang': 'en'},
    {'name': 'Wall Street Journal', 'url': 'https://feeds.wsj.com/rss/RSSWorldNews.xml', 'category': 'WSJ Economics', 'lang': 'en'},
    {'name': 'IMF News', 'url': 'https://www.imf.org/en/News/rss', 'category': 'IMF Updates', 'lang': 'en'},
    {'name': 'World Bank', 'url': 'https://www.worldbank.org/en/news/rss', 'category': 'World Bank', 'lang': 'en'},

    # Education & Research
    {'name': 'Inside Higher Ed', 'url': 'https://www.insidehighered.com/rss/news', 'category': 'Higher Education', 'lang': 'en'},
    {'name': 'Times Higher Education', 'url': 'https://www.timeshighereducation.com/feeds/news.rss', 'category': 'Education News', 'lang': 'en'},
    {'name': 'Education Week', 'url': 'https://www.edweek.org/rss.xml', 'category': 'Education Policy', 'lang': 'en'},
    {'name': 'OECD Education', 'url': 'https://www.oecd.org/education/rss.xml', 'category': 'OECD Education', 'lang': 'en'},

    # Google News - Trending Topics (by country)
    {'name': 'Google News HU', 'url': 'https://news.google.com/rss?hl=hu&gl=HU&ceid=HU:hu', 'category': 'Google Trends HU', 'lang': 'hu', 'is_trending': True},
    {'name': 'Google News GB', 'url': 'https://news.google.com/rss?hl=en-GB&gl=GB&ceid=GB:en', 'category': 'Google Trends UK', 'lang': 'en', 'is_trending': True},
    {'name': 'Google News US', 'url': 'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en', 'category': 'Google Trends US', 'lang': 'en', 'is_trending': True},
]


class NewsCollector:
    def __init__(self):
        """Initialize news collector"""
        self.sources = NEWS_SOURCES
        print("✅ News Collector initialized")

    def generate_article_id(self, title: str, source: str) -> str:
        """Generate unique article ID"""
        content = f"{title}-{source}".encode('utf-8')
        return hashlib.md5(content).hexdigest()[:12]

    def fetch_news_from_source(self, source: Dict, max_articles: int = 5) -> List[Dict]:
        """Fetch news from single RSS source"""
        articles = []

        try:
            print(f"📰 Fetching: {source['name']}")
            feed = feedparser.parse(source['url'])

            for entry in feed.entries[:max_articles]:
                title = entry.get('title', 'No title')
                description = entry.get('summary', entry.get('description', ''))
                link = entry.get('link', '')

                # Publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.now()

                # Only recent articles (last 24 hours)
                if datetime.now() - pub_date > timedelta(days=1):
                    continue

                article = {
                    'id': self.generate_article_id(title, source['name']),
                    'source': source['name'],
                    'title': title,
                    'description': description,
                    'link': link,
                    'pub_date': pub_date.isoformat(),
                    'category': source['category'],
                    'relevance_score': 5.0  # Default score
                }

                articles.append(article)

        except Exception as e:
            print(f"❌ Error fetching {source['name']}: {e}")

        return articles

    def collect_all_news(self, max_per_source: int = 5) -> List[Dict]:
        """Collect news from all sources"""
        print(f"\n{'='*60}")
        print(f"📰 NEWS COLLECTION STARTED")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        all_articles = []

        for source in self.sources:
            try:
                articles = self.fetch_news_from_source(source, max_per_source)
                all_articles.extend(articles)
            except Exception as e:
                print(f"❌ Error collecting from {source['name']}: {e}")

        print(f"\n✅ News collection complete! Total articles: {len(all_articles)}")
        print(f"{'='*60}\n")

        return all_articles

    def get_trending_topics_from_news(self, articles: List[Dict]) -> List[Dict]:
        """
        Extract trending topics from news articles
        Returns list of trend-like objects
        """
        trends = []

        for idx, article in enumerate(articles[:15], 1):  # Top 15 news as trends
            trends.append({
                'source': f'news_{article["source"].lower().replace(" ", "_")}',
                'topic': article['title'],
                'rank': idx,
                'relevance_score': article.get('relevance_score', 5.0),
                'metadata': f'Category: {article["category"]} | Link: {article["link"]}'
            })

        return trends
