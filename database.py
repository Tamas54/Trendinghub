"""
SQLite Database Manager for TrendMaster
Handles trends and generated posts storage
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


class Database:
    def __init__(self, db_path='trending_hub.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Trends table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                topic TEXT NOT NULL,
                rank INTEGER,
                fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL DEFAULT 0.0,
                metadata TEXT,
                UNIQUE(source, topic, fetch_time)
            )
        ''')

        # Generated posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trend_id INTEGER,
                post_text TEXT NOT NULL,
                char_count INTEGER,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trend_id) REFERENCES trends(id) ON DELETE CASCADE
            )
        ''')

        # News articles table (for RSS integration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_articles (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                link TEXT,
                pub_date TIMESTAMP,
                category TEXT,
                fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL DEFAULT 0.0
            )
        ''')

        # Social connections table (for Nango integration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_connections (
                provider TEXT PRIMARY KEY,
                connection_id TEXT NOT NULL,
                profile_name TEXT,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Scheduled posts table (for time-based publishing)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_content TEXT NOT NULL,
                image_path TEXT,
                video_path TEXT,
                scheduled_time TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                platform TEXT DEFAULT 'facebook',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                error_message TEXT
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ SQLite database initialized")

    def save_trends(self, trends: List[Dict]) -> int:
        """Save trends to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        saved = 0

        for trend in trends:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO trends (source, topic, rank, relevance_score, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    trend.get('source'),
                    trend.get('topic'),
                    trend.get('rank', 0),
                    trend.get('relevance_score', 0.0),
                    trend.get('metadata', '')
                ))
                if cursor.rowcount > 0:
                    saved += 1
            except sqlite3.Error as e:
                print(f"❌ Error saving trend: {e}")

        conn.commit()
        conn.close()
        return saved

    def get_latest_trends(self, source: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get latest trends by source"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if source:
            cursor.execute('''
                SELECT * FROM trends
                WHERE source = ?
                ORDER BY fetch_time DESC, rank ASC
                LIMIT ?
            ''', (source, limit))
        else:
            cursor.execute('''
                SELECT * FROM trends
                ORDER BY fetch_time DESC, rank ASC
                LIMIT ?
            ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_trend_by_id(self, trend_id: int) -> Optional[Dict]:
        """Get single trend by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM trends WHERE id = ?', (trend_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def save_generated_post(self, trend_id: int, post_text: str) -> int:
        """Save generated post"""
        conn = self.get_connection()
        cursor = conn.cursor()

        char_count = len(post_text)
        cursor.execute('''
            INSERT INTO generated_posts (trend_id, post_text, char_count)
            VALUES (?, ?, ?)
        ''', (trend_id, post_text, char_count))

        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return post_id

    def get_posts_for_trend(self, trend_id: int) -> List[Dict]:
        """Get all generated posts for a trend"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM generated_posts
            WHERE trend_id = ?
            ORDER BY generated_at DESC
        ''', (trend_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def save_news_article(self, article: Dict) -> bool:
        """Save news article from RSS feed"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO news_articles
                (id, source, title, description, link, pub_date, category, relevance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('id'),
                article.get('source'),
                article.get('title'),
                article.get('description'),
                article.get('link'),
                article.get('pub_date'),
                article.get('category'),
                article.get('relevance_score', 0.0)
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"❌ Error saving news article: {e}")
            conn.close()
            return False

    def get_latest_news(self, limit: int = 20) -> List[Dict]:
        """Get latest news articles"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM news_articles
            ORDER BY fetch_time DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def cleanup_old_data(self, days: int = 7) -> int:
        """Clean up old trends and posts"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM trends
            WHERE fetch_time < datetime('now', '-' || ? || ' days')
        ''', (days,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM trends')
        total_trends = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM generated_posts')
        total_posts = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM news_articles')
        total_news = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(fetch_time) FROM trends')
        last_fetch = cursor.fetchone()[0]

        conn.close()

        return {
            'total_trends': total_trends,
            'total_posts': total_posts,
            'total_news': total_news,
            'last_fetch': last_fetch
        }

    def save_connection(self, provider: str, connection_id: str, profile_name: Optional[str] = None) -> bool:
        """Save or update social media connection"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO social_connections (provider, connection_id, profile_name)
                VALUES (?, ?, ?)
            ''', (provider, connection_id, profile_name))
            conn.commit()
            conn.close()
            print(f"✅ Saved connection for {provider}")
            return True
        except sqlite3.Error as e:
            print(f"❌ Error saving connection: {e}")
            conn.close()
            return False

    def get_connection_id(self, provider: str) -> Optional[str]:
        """Get connection ID for a social media provider"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT connection_id FROM social_connections WHERE provider = ?', (provider,))
        row = cursor.fetchone()
        conn.close()

        return row['connection_id'] if row else None

    def schedule_post(self, post_content: str, scheduled_time: str,
                      image_path: Optional[str] = None, video_path: Optional[str] = None,
                      platform: str = 'facebook') -> int:
        """Schedule a post for future publishing"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO scheduled_posts (post_content, image_path, video_path, scheduled_time, platform)
            VALUES (?, ?, ?, ?, ?)
        ''', (post_content, image_path, video_path, scheduled_time, platform))

        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return post_id

    def get_pending_scheduled_posts(self, current_time: Optional[str] = None) -> List[Dict]:
        """Get all pending scheduled posts that should be published now"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if current_time is None:
            current_time = datetime.now().isoformat()

        cursor.execute('''
            SELECT * FROM scheduled_posts
            WHERE status = 'pending' AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
        ''', (current_time,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_all_scheduled_posts(self) -> List[Dict]:
        """Get all scheduled posts (pending and completed)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM scheduled_posts
            ORDER BY scheduled_time DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_scheduled_post_status(self, post_id: int, status: str,
                                     published_at: Optional[str] = None,
                                     error_message: Optional[str] = None) -> bool:
        """Update the status of a scheduled post"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE scheduled_posts
                SET status = ?, published_at = ?, error_message = ?
                WHERE id = ?
            ''', (status, published_at, error_message, post_id))

            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"❌ Error updating scheduled post: {e}")
            conn.close()
            return False

    def delete_scheduled_post(self, post_id: int) -> bool:
        """Delete a scheduled post"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM scheduled_posts WHERE id = ?', (post_id,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"❌ Error deleting scheduled post: {e}")
            conn.close()
            return False


# Global database instance
db = Database()
