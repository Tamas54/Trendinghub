"""
TrendMaster SaaS Database Extension
Multi-tenant támogatás, Agent kezelés, Task rendszer

Ez a modul kiegészíti a meglévő database.py-t a SaaS funkciókkal.
"""
import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    POST = "post"
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    STORY = "story"


class Platform(Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"


class SaaSDatabase:
    """
    SaaS Database Extension
    Kezeli: Users, Agents, Tasks, Platform Accounts
    """
    
    def __init__(self, db_path='trending_hub.db'):
        self.db_path = db_path
        self.init_saas_tables()
    
    def get_connection(self):
        """Get database connection with Row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_saas_tables(self):
        """Initialize SaaS-specific tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ═══════════════════════════════════════════════════════════════
        # USERS TÁBLA - SaaS felhasználók
        # ═══════════════════════════════════════════════════════════════
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                plan TEXT DEFAULT 'free',
                api_key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                settings TEXT DEFAULT '{}'
            )
        ''')
        
        # ═══════════════════════════════════════════════════════════════
        # AGENTS TÁBLA - Desktop Agent-ek
        # ═══════════════════════════════════════════════════════════════
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                hwid_hash TEXT,
                version TEXT DEFAULT '2.0.0',
                status TEXT DEFAULT 'offline',
                last_heartbeat TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                capabilities TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # ═══════════════════════════════════════════════════════════════
        # PLATFORM_ACCOUNTS TÁBLA - Social media fiókok (agent-hez kötve)
        # ═══════════════════════════════════════════════════════════════
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                account_name TEXT,
                is_active INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
                UNIQUE(agent_id, platform, account_name)
            )
        ''')
        
        # ═══════════════════════════════════════════════════════════════
        # TASKS TÁBLA - Végrehajtandó feladatok
        # ═══════════════════════════════════════════════════════════════
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                agent_id TEXT,
                platform TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                content TEXT,
                target_url TEXT,
                media_urls TEXT DEFAULT '[]',
                scheduled_at TIMESTAMP,
                assigned_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                result TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
            )
        ''')
        
        # ═══════════════════════════════════════════════════════════════
        # TASK_LOGS TÁBLA - Végrehajtási napló
        # ═══════════════════════════════════════════════════════════════
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                message TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # ═══════════════════════════════════════════════════════════════
        # INDEXEK a gyorsabb lekérdezéshez
        # ═══════════════════════════════════════════════════════════════
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks(scheduled_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agents_user ON agents(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)')
        
        conn.commit()
        conn.close()
        print("✅ SaaS tables initialized")
    
    # ═══════════════════════════════════════════════════════════════════════
    # USER MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def create_user(self, email: str, password: str, name: str = None) -> Optional[Dict]:
        """Create new user with API key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            user_id = secrets.token_hex(16)
            api_key = f"tm_{secrets.token_hex(24)}"
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO users (id, email, password_hash, name, api_key)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, email, password_hash, name, api_key))
            
            conn.commit()
            
            return {
                'id': user_id,
                'email': email,
                'name': name,
                'api_key': api_key
            }
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by API key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE api_key = ? AND is_active = 1', (api_key,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def verify_user(self, email: str, password: str) -> Optional[Dict]:
        """Verify user credentials"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user['password_hash'] != password_hash:
            return None
        
        # Update last login
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                      (datetime.now().isoformat(), user['id']))
        conn.commit()
        conn.close()
        
        return user
    
    # ═══════════════════════════════════════════════════════════════════════
    # AGENT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def register_agent(self, user_id: str, name: str, hwid_hash: str = None, 
                       version: str = "2.0.0", capabilities: List[str] = None) -> Optional[Dict]:
        """Register new agent for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            import json
            agent_id = f"agent_{secrets.token_hex(12)}"
            caps_json = json.dumps(capabilities or ['facebook', 'instagram', 'twitter'])
            
            cursor.execute('''
                INSERT INTO agents (id, user_id, name, hwid_hash, version, capabilities, status)
                VALUES (?, ?, ?, ?, ?, ?, 'online')
            ''', (agent_id, user_id, name, hwid_hash, version, caps_json))
            
            conn.commit()
            
            return {
                'agent_id': agent_id,
                'name': name,
                'status': 'online'
            }
        except sqlite3.Error as e:
            print(f"❌ Agent registration error: {e}")
            return None
        finally:
            conn.close()
    
    def update_agent_heartbeat(self, agent_id: str, platforms: List[str] = None) -> bool:
        """Update agent heartbeat and status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE agents 
                SET last_heartbeat = ?, status = 'online'
                WHERE id = ?
            ''', (datetime.now().isoformat(), agent_id))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM agents WHERE id = ?', (agent_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_user_agents(self, user_id: str) -> List[Dict]:
        """Get all agents for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM agents WHERE user_id = ?
            ORDER BY registered_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_online_agents(self, user_id: str, platform: str = None) -> List[Dict]:
        """Get online agents for user, optionally filtered by platform capability"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Agent is online if heartbeat within last 2 minutes
        threshold = (datetime.now() - timedelta(minutes=2)).isoformat()
        
        cursor.execute('''
            SELECT * FROM agents 
            WHERE user_id = ? AND last_heartbeat > ?
            ORDER BY last_heartbeat DESC
        ''', (user_id, threshold))
        
        rows = cursor.fetchall()
        conn.close()
        
        agents = [dict(row) for row in rows]
        
        # Filter by platform if specified
        if platform:
            import json
            agents = [a for a in agents if platform in json.loads(a.get('capabilities', '[]'))]
        
        return agents
    
    def mark_offline_agents(self) -> int:
        """Mark agents as offline if no heartbeat in 2 minutes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        threshold = (datetime.now() - timedelta(minutes=2)).isoformat()
        
        cursor.execute('''
            UPDATE agents SET status = 'offline'
            WHERE last_heartbeat < ? AND status = 'online'
        ''', (threshold,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    # ═══════════════════════════════════════════════════════════════════════
    # PLATFORM ACCOUNT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_platform_account(self, user_id: str, agent_id: str, platform: str, 
                             account_name: str) -> Optional[Dict]:
        """Add platform account to agent"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            account_id = f"acc_{secrets.token_hex(8)}"
            
            cursor.execute('''
                INSERT INTO platform_accounts (id, user_id, agent_id, platform, account_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (account_id, user_id, agent_id, platform, account_name))
            
            conn.commit()
            
            return {
                'id': account_id,
                'platform': platform,
                'account_name': account_name
            }
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_agent_platforms(self, agent_id: str) -> List[Dict]:
        """Get all platform accounts for agent"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM platform_accounts 
            WHERE agent_id = ? AND is_active = 1
        ''', (agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════════════════
    # TASK MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def create_task(self, user_id: str, platform: str, task_type: str,
                    content: str = None, target_url: str = None,
                    media_urls: List[str] = None, scheduled_at: str = None,
                    priority: int = 5) -> Optional[Dict]:
        """Create new task"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            import json
            task_id = f"task_{secrets.token_hex(12)}"
            media_json = json.dumps(media_urls or [])
            
            # Ha scheduled_at nincs megadva, azonnal pending
            status = 'pending' if not scheduled_at else 'scheduled'
            
            cursor.execute('''
                INSERT INTO tasks (id, user_id, platform, task_type, status, priority,
                                   content, target_url, media_urls, scheduled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, user_id, platform, task_type, status, priority,
                  content, target_url, media_json, scheduled_at))
            
            conn.commit()
            
            # Log task creation
            self._log_task_event(task_id, None, 'created', f'Task created: {task_type} on {platform}')
            
            return {
                'task_id': task_id,
                'status': status,
                'platform': platform,
                'task_type': task_type
            }
        except sqlite3.Error as e:
            print(f"❌ Task creation error: {e}")
            return None
        finally:
            conn.close()
    
    def get_next_task(self, agent_id: str, platforms: List[str]) -> Optional[Dict]:
        """
        Get next available task for agent.
        Prioritás: 
        1. scheduled_at <= now
        2. priority (magasabb = fontosabb)
        3. created_at (FIFO)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get agent's user
        cursor.execute('SELECT user_id FROM agents WHERE id = ?', (agent_id,))
        agent_row = cursor.fetchone()
        if not agent_row:
            conn.close()
            return None
        
        user_id = agent_row['user_id']
        now = datetime.now().isoformat()
        
        # Platform placeholder for IN clause
        placeholders = ','.join(['?' for _ in platforms])
        
        # Find next task
        query = f'''
            SELECT * FROM tasks
            WHERE user_id = ?
            AND platform IN ({placeholders})
            AND status = 'pending'
            AND (scheduled_at IS NULL OR scheduled_at <= ?)
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        '''
        
        cursor.execute(query, [user_id] + platforms + [now])
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        task = dict(row)
        
        # Assign task to agent
        cursor.execute('''
            UPDATE tasks SET status = 'assigned', agent_id = ?, assigned_at = ?
            WHERE id = ?
        ''', (agent_id, now, task['id']))
        
        conn.commit()
        conn.close()
        
        # Log assignment
        self._log_task_event(task['id'], agent_id, 'assigned', f'Assigned to agent {agent_id}')
        
        return task
    
    def update_task_status(self, task_id: str, status: str, agent_id: str = None,
                           error_message: str = None, result: str = None) -> bool:
        """Update task status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            if status == 'in_progress':
                cursor.execute('''
                    UPDATE tasks SET status = ?, started_at = ?
                    WHERE id = ?
                ''', (status, now, task_id))
            elif status in ['completed', 'failed']:
                cursor.execute('''
                    UPDATE tasks SET status = ?, completed_at = ?, error_message = ?, result = ?
                    WHERE id = ?
                ''', (status, now, error_message, result, task_id))
            else:
                cursor.execute('''
                    UPDATE tasks SET status = ?
                    WHERE id = ?
                ''', (status, task_id))
            
            conn.commit()
            
            # Log status change
            self._log_task_event(task_id, agent_id, f'status_{status}', 
                               error_message or f'Status changed to {status}')
            
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def retry_failed_task(self, task_id: str) -> bool:
        """Retry failed task if retries available"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT retry_count, max_retries FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        
        if not row or row['retry_count'] >= row['max_retries']:
            conn.close()
            return False
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'pending', retry_count = retry_count + 1,
                agent_id = NULL, assigned_at = NULL, started_at = NULL
            WHERE id = ?
        ''', (task_id,))
        
        conn.commit()
        conn.close()
        
        self._log_task_event(task_id, None, 'retry', f'Retry #{row["retry_count"] + 1}')
        
        return True
    
    def get_user_tasks(self, user_id: str, status: str = None, limit: int = 50) -> List[Dict]:
        """Get tasks for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM tasks WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, status, limit))
        else:
            cursor.execute('''
                SELECT * FROM tasks WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get single task by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # ═══════════════════════════════════════════════════════════════════════
    # TASK LOGGING
    # ═══════════════════════════════════════════════════════════════════════
    
    def _log_task_event(self, task_id: str, agent_id: str, event_type: str, 
                        message: str, details: str = None):
        """Internal: Log task event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO task_logs (task_id, agent_id, event_type, message, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, agent_id, event_type, message, details))
            conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def get_task_logs(self, task_id: str) -> List[Dict]:
        """Get logs for task"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM task_logs WHERE task_id = ?
            ORDER BY created_at ASC
        ''', (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get statistics for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Agent counts
        cursor.execute('SELECT COUNT(*) FROM agents WHERE user_id = ?', (user_id,))
        total_agents = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM agents 
            WHERE user_id = ? AND last_heartbeat > ?
        ''', (user_id, (datetime.now() - timedelta(minutes=2)).isoformat()))
        online_agents = cursor.fetchone()[0]
        
        # Task counts
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,))
        total_tasks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = ?', 
                      (user_id, 'completed'))
        completed_tasks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = ?', 
                      (user_id, 'failed'))
        failed_tasks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = ?', 
                      (user_id, 'pending'))
        pending_tasks = cursor.fetchone()[0]
        
        # Platform accounts
        cursor.execute('SELECT COUNT(*) FROM platform_accounts WHERE user_id = ?', (user_id,))
        total_accounts = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'agents': {
                'total': total_agents,
                'online': online_agents
            },
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'pending': pending_tasks,
                'success_rate': round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
            },
            'accounts': {
                'total': total_accounts
            }
        }


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════
saas_db = SaaSDatabase()
