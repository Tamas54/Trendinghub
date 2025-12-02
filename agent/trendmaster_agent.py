"""
TrendMaster Desktop Agent - SaaS Edition
Verzió: 3.0.0 - "Königstiger SaaS"

Funkciók:
- Szerver API kommunikáció
- Cookie titkosítás (Fernet + HWID)
- Anti-detection (Stealth mode)
- Jitter-alapú polling
- Szigorú task validáció
- Robusztus szelektorok
- Multi-platform támogatás
"""

import json
import os
import sys
import threading
import logging
import secrets
import hashlib
import platform
import uuid
import random
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from enum import Enum
from datetime import datetime
import base64
import time

import requests
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog

# Titkosítás
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Playwright + Stealth
from playwright.sync_api import sync_playwright, Page, BrowserContext
from playwright_stealth import stealth_sync

# Pydantic validáció
from pydantic import BaseModel, Field, validator, ValidationError


# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURÁCIÓ
# ═══════════════════════════════════════════════════════════════════════════

# Szerver URL - környezeti változóból vagy alapértelmezett
SERVER_URL = os.getenv("TRENDMASTER_SERVER", "https://your-railway-app.up.railway.app")
LOCAL_SESSION_DIR = os.path.expanduser("~/.trendmaster/sessions")
LOG_DIR = os.path.expanduser("~/.trendmaster/logs")
CONFIG_FILE = os.path.expanduser("~/.trendmaster/config.json")

# Polling beállítások (anti-detection)
POLL_MIN_SEC = 8
POLL_MAX_SEC = 18
LOGIN_TIMEOUT_MS = 300_000
REQUEST_TIMEOUT_SEC = 30

# Engedélyezett task típusok
ALLOWED_TASK_TYPES: Set[str] = {"post", "like", "comment", "share", "story"}
MAX_CONTENT_LENGTH = 5000

# Agent verzió
AGENT_VERSION = "3.0.0"

# Mappák létrehozása
os.makedirs(LOCAL_SESSION_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f'agent_{datetime.now():%Y%m%d}.log'),
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# BIZTONSÁGI RÉTEG - Cookie Titkosítás
# ═══════════════════════════════════════════════════════════════════════════

class SecureStorage:
    """
    Titkosított tárolás HWID + API kulcs alapú kulcsszármaztatással.
    A cookie-k soha nem kerülnek plain text-be a lemezre.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._fernet = self._derive_key()

    def _get_hwid(self) -> str:
        """
        Hardware ID generálása a gép egyedi azonosításához.
        Kombinálja: MAC cím + Processzor + Gépnév + Machine
        """
        components = [
            str(uuid.getnode()),
            platform.processor(),
            platform.node(),
            platform.machine()
        ]
        hwid_string = "|".join(components)
        return hashlib.sha256(hwid_string.encode()).hexdigest()

    def _derive_key(self) -> Fernet:
        """
        Fernet kulcs származtatása PBKDF2-vel.
        Salt = HWID, Password = API kulcs
        """
        hwid = self._get_hwid()
        salt = hwid[:32].encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(self.api_key.encode()))
        return Fernet(key)

    def encrypt(self, data: dict) -> bytes:
        """Dict titkosítása"""
        json_bytes = json.dumps(data).encode('utf-8')
        return self._fernet.encrypt(json_bytes)

    def decrypt(self, encrypted_data: bytes) -> Optional[dict]:
        """Titkosított adat visszafejtése"""
        try:
            decrypted = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
        except (InvalidToken, json.JSONDecodeError) as e:
            logger.error(f"Dekódolási hiba: {e}")
            return None

    def save_cookies(self, platform_name: str, cookies: List[dict]) -> bool:
        """Cookie-k titkosított mentése"""
        try:
            encrypted = self.encrypt({
                "cookies": cookies,
                "saved_at": datetime.now().isoformat()
            })
            path = os.path.join(LOCAL_SESSION_DIR, f"{platform_name}.enc")

            with open(path, "wb") as f:
                f.write(encrypted)

            logger.info(f"Cookie-k titkosítva mentve: {platform_name}")
            return True
        except Exception as e:
            logger.error(f"Cookie mentési hiba: {e}")
            return False

    def load_cookies(self, platform_name: str) -> Optional[List[dict]]:
        """Titkosított cookie-k betöltése"""
        path = os.path.join(LOCAL_SESSION_DIR, f"{platform_name}.enc")

        if not os.path.exists(path):
            return None

        try:
            with open(path, "rb") as f:
                encrypted = f.read()

            data = self.decrypt(encrypted)
            if data:
                return data.get("cookies")
            return None
        except Exception as e:
            logger.error(f"Cookie betöltési hiba: {e}")
            return None

    def get_hwid_hash(self) -> str:
        """HWID hash lekérése (regisztrációhoz)"""
        return self._get_hwid()


# ═══════════════════════════════════════════════════════════════════════════
# TASK VALIDÁCIÓ - Pydantic Séma
# ═══════════════════════════════════════════════════════════════════════════

class TaskContent(BaseModel):
    """Poszt tartalom validáció"""
    text: str = Field(default="", max_length=MAX_CONTENT_LENGTH)
    media_urls: List[str] = Field(default_factory=list, max_items=10)

    @validator('text')
    def sanitize_text(cls, v):
        # XSS védelem
        v = re.sub(r'<script[^>]*>.*?</script>', '', v, flags=re.IGNORECASE | re.DOTALL)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        return v.strip()

    @validator('media_urls', each_item=True)
    def validate_media_url(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('Csak HTTPS URL-ek engedélyezettek')
        blocked = ['localhost', '127.0.0.1', '0.0.0.0', 'file://']
        if v and any(b in v.lower() for b in blocked):
            raise ValueError('Tiltott URL')
        return v


class Task(BaseModel):
    """Task séma validáció"""
    id: str = Field(..., min_length=8, max_length=64)
    platform: str
    task_type: str
    content: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    target_url: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)

    class Config:
        extra = 'ignore'

    @validator('platform')
    def validate_platform(cls, v):
        allowed = {'facebook', 'instagram', 'twitter', 'linkedin', 'tiktok'}
        if v.lower() not in allowed:
            raise ValueError(f'Ismeretlen platform: {v}')
        return v.lower()

    @validator('task_type')
    def validate_task_type(cls, v):
        if v.lower() not in ALLOWED_TASK_TYPES:
            raise ValueError(f'Tiltott task típus: {v}')
        return v.lower()


def validate_task(raw_task: dict) -> Optional[Task]:
    """Szigorú task validáció"""
    try:
        task = Task(**raw_task)
        logger.info(f"Task validálva: {task.id} ({task.platform}/{task.task_type})")
        return task
    except ValidationError as e:
        logger.warning(f"Érvénytelen task elutasítva: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# ANTI-DETECTION RÉTEG
# ═══════════════════════════════════════════════════════════════════════════

class StealthBrowser:
    """Anti-detection böngésző wrapper"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]

    VIEWPORTS = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
    ]

    @classmethod
    def create_context(cls, browser, headless: bool = True) -> BrowserContext:
        """Stealth kontextus létrehozása"""
        viewport = random.choice(cls.VIEWPORTS)
        user_agent = random.choice(cls.USER_AGENTS)

        context = browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale='hu-HU',
            timezone_id='Europe/Budapest',
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
            geolocation={'longitude': 19.0402, 'latitude': 47.4979},
            permissions=['geolocation'],
            color_scheme='light',
        )

        return context

    @classmethod
    def apply_stealth(cls, page: Page) -> None:
        """Stealth beállítások alkalmazása"""
        stealth_sync(page)

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin'},
                    {name: 'Chrome PDF Viewer'},
                    {name: 'Native Client'}
                ]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['hu-HU', 'hu', 'en-US', 'en']
            });
        """)

    @classmethod
    def human_delay(cls, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Emberi késleltetés"""
        delay = random.randint(min_ms, max_ms) / 1000
        time.sleep(delay)

    @classmethod
    def human_type(cls, page: Page, selector: str, text: str) -> None:
        """Emberi gépelés szimuláció"""
        element = page.locator(selector)
        element.click()
        cls.human_delay(200, 500)

        for char in text:
            element.type(char, delay=random.randint(50, 150))

            if random.random() < 0.05 and len(text) > 10:
                wrong_char = random.choice('abcdefghijklmnop')
                element.type(wrong_char, delay=100)
                cls.human_delay(100, 300)
                page.keyboard.press('Backspace')


# ═══════════════════════════════════════════════════════════════════════════
# PLATFORM KONFIGURÁCIÓ
# ═══════════════════════════════════════════════════════════════════════════

class Platform(Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"


@dataclass
class PlatformConfig:
    name: str
    url: str
    button_color: str
    emoji: str
    selectors: Dict[str, List[str]] = field(default_factory=dict)


PLATFORM_CONFIGS: Dict[Platform, PlatformConfig] = {
    Platform.FACEBOOK: PlatformConfig(
        name="Facebook",
        url="https://www.facebook.com",
        button_color="#3b5998",
        emoji="🔵",
        selectors={
            "post_box": [
                '[aria-label*="Mi jár a fejedben"]',
                '[aria-label*="What\'s on your mind"]',
                '[role="textbox"][contenteditable="true"]',
            ],
            "post_button": [
                '[aria-label="Közzététel"]',
                '[aria-label="Post"]',
                'button:has-text("Közzététel")',
                'button:has-text("Post")',
            ],
        }
    ),
    Platform.INSTAGRAM: PlatformConfig(
        name="Instagram",
        url="https://www.instagram.com",
        button_color="#E1306C",
        emoji="📸",
        selectors={
            "new_post": [
                '[aria-label="Új bejegyzés"]',
                '[aria-label="New post"]',
            ],
        }
    ),
    Platform.TWITTER: PlatformConfig(
        name="X (Twitter)",
        url="https://twitter.com",
        button_color="#000000",
        emoji="✖️",
        selectors={
            "tweet_box": [
                '[data-testid="tweetTextarea_0"]',
                '[aria-label*="Tweet"]',
                '[aria-label*="Post"]',
            ],
            "tweet_button": [
                '[data-testid="tweetButtonInline"]',
                'button:has-text("Post")',
            ],
        }
    ),
    Platform.LINKEDIN: PlatformConfig(
        name="LinkedIn",
        url="https://www.linkedin.com",
        button_color="#0077B5",
        emoji="💼",
        selectors={}
    ),
    Platform.TIKTOK: PlatformConfig(
        name="TikTok",
        url="https://www.tiktok.com",
        button_color="#000000",
        emoji="🎵",
        selectors={}
    ),
}


def find_element_robust(page: Page, selectors: List[str], timeout: int = 10000) -> Optional[Any]:
    """Több szelektor próbálása sorban"""
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=timeout // len(selectors)):
                logger.debug(f"Elem megtalálva: {selector}")
                return element
        except Exception:
            continue

    logger.warning(f"Egyik szelektor sem működött: {selectors}")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# API KLIENS
# ═══════════════════════════════════════════════════════════════════════════

class TrendMasterAPI:
    """API kommunikáció a szerverrel"""

    def __init__(self, api_key: str, server_url: str = SERVER_URL):
        self.api_key = api_key
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': f'TrendMaster-Agent/{AGENT_VERSION}'
        })
        self.agent_id: Optional[str] = None

    def register_agent(self, name: str, hwid_hash: str, capabilities: List[str]) -> Optional[Dict]:
        """Agent regisztráció"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/agent/register",
                json={
                    "name": name,
                    "hwid_hash": hwid_hash,
                    "version": AGENT_VERSION,
                    "capabilities": capabilities
                },
                timeout=REQUEST_TIMEOUT_SEC
            )
            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                self.agent_id = data.get('agent_id')
                return data
            return None
        except Exception as e:
            logger.error(f"Agent regisztráció hiba: {e}")
            return None

    def get_task(self, platforms: List[str]) -> Optional[Dict]:
        """Következő task lekérése"""
        if not self.agent_id:
            return None

        try:
            response = self.session.post(
                f"{self.server_url}/api/agent/get-task",
                json={
                    "agent_id": self.agent_id,
                    "platforms": platforms,
                    "version": AGENT_VERSION
                },
                timeout=REQUEST_TIMEOUT_SEC
            )
            response.raise_for_status()
            data = response.json()

            if data.get('success') and data.get('has_task'):
                return data.get('task')
            return None
        except Exception as e:
            logger.error(f"Task lekérés hiba: {e}")
            return None

    def report_status(self, task_id: str, status: str, error: str = None, result: str = None) -> bool:
        """Task státusz jelentés"""
        if not self.agent_id:
            return False

        try:
            response = self.session.post(
                f"{self.server_url}/api/agent/task-status",
                json={
                    "agent_id": self.agent_id,
                    "task_id": task_id,
                    "status": status,
                    "error": error,
                    "result": result
                },
                timeout=REQUEST_TIMEOUT_SEC
            )
            response.raise_for_status()
            return response.json().get('success', False)
        except Exception as e:
            logger.error(f"Státusz jelentés hiba: {e}")
            return False

    def heartbeat(self, platforms: List[str]) -> Dict:
        """Életjel küldése"""
        if not self.agent_id:
            return {}

        try:
            response = self.session.post(
                f"{self.server_url}/api/agent/heartbeat",
                json={
                    "agent_id": self.agent_id,
                    "platforms": platforms,
                    "version": AGENT_VERSION
                },
                timeout=REQUEST_TIMEOUT_SEC
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Heartbeat hiba: {e}")
            return {}

    def add_platform(self, platform_name: str, account_name: str) -> bool:
        """Platform fiók hozzáadása"""
        if not self.agent_id:
            return False

        try:
            response = self.session.post(
                f"{self.server_url}/api/agent/platform",
                json={
                    "agent_id": self.agent_id,
                    "platform": platform_name,
                    "account_name": account_name
                },
                timeout=REQUEST_TIMEOUT_SEC
            )
            response.raise_for_status()
            return response.json().get('success', False)
        except Exception as e:
            logger.error(f"Platform hozzáadás hiba: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════
# FŐ ALKALMAZÁS
# ═══════════════════════════════════════════════════════════════════════════

class TrendMasterAgent:
    """TrendMaster Desktop Agent - SaaS Edition"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"TrendMaster Agent 🛡️ v{AGENT_VERSION}")
        self.root.geometry("500x700")
        self.root.resizable(False, False)

        self.api_key: str = ""
        self.is_running: bool = False
        self.poll_job: Optional[str] = None
        self.secure_storage: Optional[SecureStorage] = None
        self.api: Optional[TrendMasterAPI] = None

        self.logged_in_platforms: Dict[Platform, bool] = {p: False for p in Platform}

        self._load_config()
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        logger.info(f"Agent v{AGENT_VERSION} (SaaS) elindítva")

    def _load_config(self):
        """Konfiguráció betöltése"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
            except:
                pass

    def _save_config(self):
        """Konfiguráció mentése"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'api_key': self.api_key}, f)
        except:
            pass

    def _build_ui(self):
        """UI felépítése"""
        # Header
        header = tk.Frame(self.root, bg="#1a252f", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🛡️ TrendMaster Agent",
            font=("Arial", 20, "bold"),
            bg="#1a252f",
            fg="#3498db"
        ).pack(pady=10)

        tk.Label(
            header,
            text=f"SaaS Edition v{AGENT_VERSION}",
            font=("Arial", 10),
            bg="#1a252f",
            fg="#7f8c8d"
        ).pack()

        # Server URL
        server_frame = tk.LabelFrame(self.root, text="🌐 Szerver", padx=15, pady=10)
        server_frame.pack(fill="x", padx=20, pady=10)

        self.server_label = tk.Label(
            server_frame,
            text=f"URL: {SERVER_URL}",
            font=("Arial", 9),
            fg="#7f8c8d"
        )
        self.server_label.pack(anchor="w")

        # API Key
        api_frame = tk.LabelFrame(self.root, text="🔑 API Hitelesítés", padx=15, pady=10)
        api_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(api_frame, text="API Kulcs:", font=("Arial", 9)).pack(anchor="w")
        self.api_entry = tk.Entry(api_frame, width=50, show="•")
        self.api_entry.pack(fill="x", pady=5)

        if self.api_key:
            self.api_entry.insert(0, self.api_key)

        key_frame = tk.Frame(api_frame)
        key_frame.pack(fill="x")

        self.show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            key_frame,
            text="Megjelenítés",
            variable=self.show_key_var,
            command=lambda: self.api_entry.config(show="" if self.show_key_var.get() else "•")
        ).pack(side="left")

        tk.Button(
            key_frame,
            text="🔓 Aktiválás",
            command=self._activate_key
        ).pack(side="right")

        # Platform Login
        login_frame = tk.LabelFrame(self.root, text="📱 Platform Fiókok", padx=15, pady=10)
        login_frame.pack(fill="x", padx=20, pady=10)

        self.login_buttons: Dict[Platform, tk.Button] = {}
        self.status_indicators: Dict[Platform, tk.Label] = {}

        for platform in [Platform.FACEBOOK, Platform.INSTAGRAM, Platform.TWITTER]:
            config = PLATFORM_CONFIGS[platform]
            row = tk.Frame(login_frame)
            row.pack(fill="x", pady=4)

            btn = tk.Button(
                row,
                text=f"{config.emoji} {config.name}",
                bg=config.button_color,
                fg="white",
                font=("Arial", 9, "bold"),
                width=18,
                command=lambda p=platform: self._perform_login(p),
                state="disabled"
            )
            btn.pack(side="left", padx=(0, 10))
            self.login_buttons[platform] = btn

            indicator = tk.Label(row, text="⚫ Várakozás", fg="gray", font=("Arial", 9))
            indicator.pack(side="left")
            self.status_indicators[platform] = indicator

        # Biztonsági státusz
        security_frame = tk.LabelFrame(self.root, text="🔒 Biztonság", padx=15, pady=10)
        security_frame.pack(fill="x", padx=20, pady=10)

        self.encryption_label = tk.Label(security_frame, text="⚫ Titkosítás: Inaktív", fg="gray")
        self.encryption_label.pack(anchor="w")

        self.stealth_label = tk.Label(security_frame, text="✅ Stealth mód: Aktív", fg="#27ae60")
        self.stealth_label.pack(anchor="w")

        self.jitter_label = tk.Label(security_frame, text=f"✅ Jitter: {POLL_MIN_SEC}-{POLL_MAX_SEC}s", fg="#27ae60")
        self.jitter_label.pack(anchor="w")

        self.agent_id_label = tk.Label(security_frame, text="⚫ Agent ID: -", fg="gray")
        self.agent_id_label.pack(anchor="w")

        # Agent státusz
        status_frame = tk.LabelFrame(self.root, text="⚙️ Agent Állapot", padx=15, pady=10)
        status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = tk.Label(status_frame, text="⏹️ Leállítva", fg="#e74c3c", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)

        self.task_label = tk.Label(status_frame, text="Utolsó task: -", fg="gray", font=("Arial", 9))
        self.task_label.pack()

        self.next_poll_label = tk.Label(status_frame, text="Következő: -", fg="gray", font=("Arial", 9))
        self.next_poll_label.pack()

        self.pending_label = tk.Label(status_frame, text="Várakozó: -", fg="gray", font=("Arial", 9))
        self.pending_label.pack()

        # Kontroll gombok
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20, pady=15)

        self.start_btn = tk.Button(
            btn_frame,
            text="▶️ INDÍTÁS",
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            height=2,
            command=self._toggle_agent,
            state="disabled"
        )
        self.start_btn.pack(fill="x")

        # Footer
        tk.Label(
            self.root,
            text="🛡️ SaaS Edition | Cookie-k titkosítva | Anti-detection aktív",
            fg="gray",
            font=("Arial", 8)
        ).pack(side="bottom", pady=5)

    def _activate_key(self):
        """API kulcs aktiválása"""
        key = self.api_entry.get().strip()

        if len(key) < 16:
            messagebox.showerror("Hiba", "Az API kulcsnak legalább 16 karakter hosszúnak kell lennie!")
            return

        self.api_key = key
        self.secure_storage = SecureStorage(key)
        self.api = TrendMasterAPI(key)

        # Agent regisztráció
        agent_name = f"Agent_{platform.node()[:8]}"
        hwid_hash = self.secure_storage.get_hwid_hash()

        result = self.api.register_agent(
            name=agent_name,
            hwid_hash=hwid_hash,
            capabilities=['facebook', 'instagram', 'twitter']
        )

        if result:
            self.agent_id_label.config(text=f"✅ Agent ID: {result['agent_id'][:16]}...", fg="#27ae60")

            # Gombok aktiválása
            for btn in self.login_buttons.values():
                btn.config(state="normal")
            self.start_btn.config(state="normal")

            # Meglévő cookie-k ellenőrzése
            for plat in Platform:
                cookies = self.secure_storage.load_cookies(plat.value)
                self.logged_in_platforms[plat] = cookies is not None

            self._update_indicators()
            self.encryption_label.config(text="✅ Titkosítás: AES-256 (Fernet)", fg="#27ae60")

            self._save_config()
            messagebox.showinfo("Siker", f"Agent regisztrálva!\nID: {result['agent_id']}")
            logger.info(f"Agent regisztrálva: {result['agent_id']}")
        else:
            messagebox.showerror("Hiba", "Agent regisztráció sikertelen!\nEllenőrizd az API kulcsot és a szerver URL-t.")

    def _update_indicators(self):
        """Státusz indikátorok frissítése"""
        for plat in Platform:
            if plat in self.status_indicators:
                if self.logged_in_platforms.get(plat):
                    self.status_indicators[plat].config(text="🟢 Aktív", fg="#27ae60")
                else:
                    self.status_indicators[plat].config(text="⚫ Nincs session", fg="gray")

    def _perform_login(self, plat: Platform):
        """Platform bejelentkezés"""
        if not self.secure_storage:
            messagebox.showerror("Hiba", "Először aktiváld az API kulcsot!")
            return

        config = PLATFORM_CONFIGS[plat]

        if not messagebox.askokcancel(
            "Bejelentkezés",
            f"Böngésző megnyitása: {config.name}\n\n"
            "1. Jelentkezz be\n"
            "2. Zárd be az ablakot\n\n"
            "⚠️ A cookie-k titkosítva lesznek tárolva."
        ):
            return

        thread = threading.Thread(target=self._login_worker, args=(plat,), daemon=True)
        thread.start()

    def _login_worker(self, plat: Platform):
        """Login worker szál"""
        config = PLATFORM_CONFIGS[plat]

        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=False)
                context = StealthBrowser.create_context(browser, headless=False)
                page = context.new_page()
                StealthBrowser.apply_stealth(page)

                page.goto(config.url)
                logger.info(f"Login ablak: {plat.value}")

                try:
                    page.wait_for_event("close", timeout=LOGIN_TIMEOUT_MS)
                except:
                    pass

                cookies = context.cookies()
                browser.close()

                if self.secure_storage.save_cookies(plat.value, cookies):
                    self.logged_in_platforms[plat] = True
                    self.root.after(0, self._update_indicators)

                    # Jelentés a szervernek
                    if self.api:
                        self.api.add_platform(plat.value, f"{plat.value}_user")

                    self.root.after(0, lambda: messagebox.showinfo(
                        "Siker", f"✅ {config.name} session mentve!"))

        except Exception as e:
            logger.error(f"Login hiba: {e}")
            self.root.after(0, lambda: messagebox.showerror("Hiba", str(e)))

    def _toggle_agent(self):
        """Agent indítás/leállítás"""
        if self.is_running:
            self._stop_agent()
        else:
            self._start_agent()

    def _start_agent(self):
        """Agent indítása"""
        if not self.api or not self.api.agent_id:
            messagebox.showerror("Hiba", "Aktiváld az API kulcsot!")
            return

        if not any(self.logged_in_platforms.values()):
            messagebox.showwarning("Figyelem", "Legalább egy platformra be kell jelentkezni!")
            return

        self.is_running = True
        self.start_btn.config(text="⏹️ LEÁLLÍTÁS", bg="#e74c3c")
        self.status_label.config(text="▶️ Fut", fg="#27ae60")
        self.api_entry.config(state="disabled")

        logger.info("Agent elindítva")
        self._poll_with_jitter()

    def _stop_agent(self):
        """Agent leállítása"""
        self.is_running = False

        if self.poll_job:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None

        self.start_btn.config(text="▶️ INDÍTÁS", bg="#27ae60")
        self.status_label.config(text="⏹️ Leállítva", fg="#e74c3c")
        self.next_poll_label.config(text="Következő: -")
        self.api_entry.config(state="normal")

        logger.info("Agent leállítva")

    def _poll_with_jitter(self):
        """Polling jitter-rel"""
        if not self.is_running:
            return

        jitter_sec = random.uniform(POLL_MIN_SEC, POLL_MAX_SEC)
        jitter_ms = int(jitter_sec * 1000)

        self.next_poll_label.config(text=f"Következő: {jitter_sec:.1f}s")

        thread = threading.Thread(target=self._fetch_task, daemon=True)
        thread.start()

        self.poll_job = self.root.after(jitter_ms, self._poll_with_jitter)

    def _fetch_task(self):
        """Task lekérése és végrehajtása"""
        if not self.api:
            return

        try:
            # Aktív platformok
            active_platforms = [p.value for p, ok in self.logged_in_platforms.items() if ok]

            # Heartbeat + pending tasks
            heartbeat = self.api.heartbeat(active_platforms)
            pending = heartbeat.get('pending_tasks', 0)
            self.root.after(0, lambda: self.pending_label.config(text=f"Várakozó: {pending}"))

            # Task lekérés
            raw_task = self.api.get_task(active_platforms)

            if raw_task:
                validated_task = validate_task(raw_task)

                if validated_task:
                    self.root.after(0, lambda: self.task_label.config(
                        text=f"Task: {validated_task.id[:12]}..."))
                    self._execute_task(validated_task)
                else:
                    logger.warning("Task elutasítva validáció után")
                    self.api.report_status(raw_task.get('id', 'unknown'), "failed", "Validation failed")

        except Exception as e:
            logger.error(f"Polling hiba: {e}")

    def _execute_task(self, task: Task):
        """Task végrehajtása"""
        plat = Platform(task.platform)
        cookies = self.secure_storage.load_cookies(plat.value)

        if not cookies:
            logger.error(f"Nincs cookie: {plat.value}")
            self.api.report_status(task.id, "failed", "No session")
            return

        # Státusz: in_progress
        self.api.report_status(task.id, "in_progress")

        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=True)
                context = StealthBrowser.create_context(browser, headless=True)
                context.add_cookies(cookies)

                page = context.new_page()
                StealthBrowser.apply_stealth(page)

                # Platform-specifikus végrehajtás
                if plat == Platform.FACEBOOK and task.task_type == "post":
                    self._facebook_post(page, task)
                elif plat == Platform.TWITTER and task.task_type == "post":
                    self._twitter_post(page, task)
                # További platformok...

                # Cookie frissítés
                updated_cookies = context.cookies()
                self.secure_storage.save_cookies(plat.value, updated_cookies)

                browser.close()

            self.api.report_status(task.id, "completed")
            logger.info(f"Task kész: {task.id}")

        except Exception as e:
            logger.error(f"Task végrehajtási hiba: {e}")
            self.api.report_status(task.id, "failed", str(e))

    def _facebook_post(self, page: Page, task: Task):
        """Facebook posztolás"""
        config = PLATFORM_CONFIGS[Platform.FACEBOOK]

        page.goto("https://www.facebook.com")
        StealthBrowser.human_delay(2000, 4000)

        post_box = find_element_robust(page, config.selectors["post_box"])
        if not post_box:
            raise Exception("Poszt doboz nem található")

        post_box.click()
        StealthBrowser.human_delay(1000, 2000)

        if task.content:
            StealthBrowser.human_type(page, '[role="textbox"]', task.content)

        StealthBrowser.human_delay(1000, 2000)

        post_btn = find_element_robust(page, config.selectors["post_button"])
        if post_btn:
            post_btn.click()
            StealthBrowser.human_delay(3000, 5000)

    def _twitter_post(self, page: Page, task: Task):
        """Twitter posztolás"""
        config = PLATFORM_CONFIGS[Platform.TWITTER]

        page.goto("https://twitter.com/compose/tweet")
        StealthBrowser.human_delay(2000, 4000)

        tweet_box = find_element_robust(page, config.selectors["tweet_box"])
        if not tweet_box:
            raise Exception("Tweet doboz nem található")

        if task.content:
            StealthBrowser.human_type(page, config.selectors["tweet_box"][0], task.content)

        StealthBrowser.human_delay(1000, 2000)

        tweet_btn = find_element_robust(page, config.selectors["tweet_button"])
        if tweet_btn:
            tweet_btn.click()
            StealthBrowser.human_delay(3000, 5000)

    def _on_closing(self):
        """Cleanup"""
        if self.is_running:
            if not messagebox.askokcancel("Kilépés", "Agent fut. Kilépsz?"):
                return

        self._stop_agent()
        logger.info("Agent leállítva")
        self.root.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# BELÉPÉSI PONT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    app = TrendMasterAgent(root)
    root.mainloop()


if __name__ == "__main__":
    main()
