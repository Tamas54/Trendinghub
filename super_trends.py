"""
Super Trends Detector for TrendMaster
Identifies cross-source trending topics that appear in multiple regions/platforms
"""
from typing import List, Dict, Set
from collections import defaultdict
import re


class SuperTrendsDetector:
    def __init__(self):
        """Initialize super trends detector"""
        pass

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Remove special characters, convert to lowercase
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_keywords(self, text: str, min_length: int = 4) -> Set[str]:
        """Extract significant keywords from text"""
        normalized = self.normalize_text(text)
        words = normalized.split()

        # Filter out common words (simple stopwords)
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must',
            'that', 'this', 'these', 'those', 'with', 'from', 'for', 'to', 'of',
            'in', 'on', 'at', 'by', 'about', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'over',
            'not', 'no', 'yes', 'all', 'some', 'any', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'such', 'only', 'own', 'same',
            'than', 'too', 'very', 'just', 'now', 'here', 'there', 'when',
            'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose',
            # Hungarian common words
            'egy', 'ez', 'az', 'és', 'vagy', 'de', 'hogy', 'van', 'volt',
            'lesz', 'lehet', 'nem', 'igen', 'ezt', 'azt', 'ami', 'aki',
            'amely', 'mit', 'ki', 'hol', 'mikor', 'miért', 'hogyan', 'már',
            'még', 'most', 'csak', 'is', 'el', 'fel', 'le', 'meg', 'ki',
            'be', 'vissza', 'újra', 'majd', 'után', 'előtt', 'alatt', 'felett',
            'között', 'nélkül', 'miatt', 'szerint', 'ellen', 'mellett',
            'about', 'news', 'hír', 'hírek', 'latest', 'breaking', 'new'
        }

        keywords = set()
        for word in words:
            if len(word) >= min_length and word not in stopwords:
                keywords.add(word)

        return keywords

    def calculate_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Calculate Jaccard similarity between two keyword sets"""
        if not keywords1 or not keywords2:
            return 0.0

        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        return len(intersection) / len(union) if union else 0.0

    def detect_super_trends(self, trends_by_source: Dict[str, List[Dict]],
                           min_sources: int = 3,
                           similarity_threshold: float = 0.3) -> List[Dict]:
        """
        Detect super trends that appear across multiple sources

        Args:
            trends_by_source: Dictionary mapping source names to lists of trends
            min_sources: Minimum number of sources a topic must appear in
            similarity_threshold: Minimum similarity score to consider topics as same

        Returns:
            List of super trends with aggregated information
        """
        # Prepare trend data with keywords
        all_trends = []
        for source, trends in trends_by_source.items():
            for trend in trends:
                topic = trend.get('topic') or trend.get('title', '')
                if not topic:
                    continue

                keywords = self.extract_keywords(topic)
                all_trends.append({
                    'source': source,
                    'topic': topic,
                    'keywords': keywords,
                    'data': trend
                })

        # Group similar trends
        trend_groups = []
        used_indices = set()

        for i, trend1 in enumerate(all_trends):
            if i in used_indices:
                continue

            # Start new group
            group = {
                'trends': [trend1],
                'sources': {trend1['source']},
                'all_keywords': trend1['keywords'].copy(),
                'representative_topic': trend1['topic']
            }

            # Find similar trends from other sources
            for j, trend2 in enumerate(all_trends):
                if j <= i or j in used_indices:
                    continue

                # Only consider trends from different sources
                if trend2['source'] in group['sources']:
                    continue

                # Calculate similarity
                similarity = self.calculate_similarity(trend1['keywords'], trend2['keywords'])

                if similarity >= similarity_threshold:
                    group['trends'].append(trend2)
                    group['sources'].add(trend2['source'])
                    group['all_keywords'].update(trend2['keywords'])
                    used_indices.add(j)

            # Only keep groups that appear in multiple sources
            if len(group['sources']) >= min_sources:
                trend_groups.append(group)
                used_indices.add(i)

        # Sort by number of sources (most cross-platform first)
        trend_groups.sort(key=lambda g: len(g['sources']), reverse=True)

        # Format super trends with categorization
        super_trends = []
        for idx, group in enumerate(trend_groups[:6]):  # Top 6 super trends
            # Find the best representative topic (longest, most complete)
            representative = max(group['trends'], key=lambda t: len(t['topic']))

            # Categorize: Hungarian, International, or Global
            hungarian_sources = {'google_hu', 'youtube_hu', 'google_news_hu'}
            international_sources = {'google_gb', 'google_us', 'youtube_gb', 'youtube_us',
                                    'google_news_gb', 'google_news_us'}

            sources_set = set(group['sources'])
            has_hungarian = bool(sources_set.intersection(hungarian_sources))
            has_international = bool(sources_set.intersection(international_sources))

            if has_hungarian and has_international:
                category = 'global'
                category_label = '🌍 GLOBÁLIS'
            elif has_hungarian:
                category = 'hungarian'
                category_label = '🇭🇺 MAGYAR'
            else:
                category = 'international'
                category_label = '🌎 NEMZETKÖZI'

            super_trend = {
                'id': f'super_{idx + 1}',
                'topic': representative['topic'],
                'source_count': len(group['sources']),
                'sources': list(group['sources']),
                'keywords': list(group['all_keywords'])[:10],  # Top 10 keywords
                'trends': [t['data'] for t in group['trends']],
                'relevance_score': len(group['sources']) * 10,  # Simple scoring
                'category': category,
                'category_label': category_label
            }

            super_trends.append(super_trend)

        return super_trends


# Global instance
detector = SuperTrendsDetector()
