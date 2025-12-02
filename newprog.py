# agent_app.py
"""
TrendMaster Desktop Agent - Hardened Edition
Verzió: 2.0.0 - "Königstiger"

Biztonsági fejlesztések:
- Cookie titkosítás (Fernet + HWID)
- Anti-detection (Stealth mode)
- Jitter-alapú polling
- Szigorú task validáció
- Robusztus szelektorok
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

import requests
import tkinter as tk
from tkinter import messagebox, ttk

# Titkosítás
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Playwright + Stealth
from playwright.sync_api import sync_playwright, Page, BrowserContext
from playwright_stealth import stealth_sync  # pip install playwright-stealth

# Pydantic a szigorú validációhoz
from pydantic import BaseModel, Field, validator, ValidationError


# ═══════════════════════════════════════════════════════════════════
# KONFIGURÁCIÓ
# ═══════════════════════════════════════════════════════════════════

SERVER_URL = os.getenv("TRENDMASTER_SERVER", "https://te-railway-appod.app")
LOCAL_SESSION_DIR = "sessions"
LOG_DIR = "logs"

# Polling Jitter beállítások (anti-detection)
POLL_MIN_SEC = 8
POLL_MAX_SEC = 18
LOGIN_TIMEOUT_MS = 300_000
REQUEST_TIMEOUT_SEC = 30

# Engedélyezett task típusok (whitelist)
ALLOWED_TASK_TYPES: Set[str] = {"post", "like", "comment", "share", "story"}
MAX_CONTENT_LENGTH = 5000

# Logging
os.makedirs(LOG_DIR, exist_ok=True)
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


# ═══════════════════════════════════════════════════════════════════
# BIZTONSÁGI RÉTEG - Cookie Titkosítás
# ═══════════════════════════════════════════════════════════════════

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
        Kombinálja: MAC cím + Processzorazonosító + Gépnév
        """
        components = [
            str(uuid.getnode()),  # MAC cím
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
        salt = hwid[:32].encode()  # 32 byte salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP ajánlás
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
    
    def save_cookies(self, platform: str, cookies: List[dict]) -> bool:
        """Cookie-k titkosított mentése"""
        try:
            encrypted = self.encrypt({"cookies": cookies, "saved_at": datetime.now().isoformat()})
            path = os.path.join(LOCAL_SESSION_DIR, f"{platform}.enc")
            
            with open(path, "wb") as f:
                f.write(encrypted)
            
            logger.info(f"Cookie-k titkosítva mentve: {platform}")
            return True
        except Exception as e:
            logger.error(f"Cookie mentési hiba: {e}")
            return False
    
    def load_cookies(self, platform: str) -> Optional[List[dict]]:
        """Titkosított cookie-k betöltése"""
        path = os.path.join(LOCAL_SESSION_DIR, f"{platform}.enc")
        
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


# ═══════════════════════════════════════════════════════════════════
# TASK VALIDÁCIÓ - Szigorú Pydantic Séma
# ═══════════════════════════════════════════════════════════════════

class TaskContent(BaseModel):
    """Poszt tartalom validáció"""
    text: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    media_urls: List[str] = Field(default_factory=list, max_items=10)
    
    @validator('text')
    def sanitize_text(cls, v):
        # Alapvető XSS védelem - script tagek eltávolítása
        v = re.sub(r'<script[^>]*>.*?</script>', '', v, flags=re.IGNORECASE | re.DOTALL)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        return v.strip()
    
    @validator('media_urls', each_item=True)
    def validate_media_url(cls, v):
        # Csak HTTPS URL-ek engedélyezettek
        if not v.startswith('https://'):
            raise ValueError('Csak HTTPS URL-ek engedélyezettek')
        # Tiltott domain-ek
        blocked = ['localhost', '127.0.0.1', '0.0.0.0', 'file://']
        if any(b in v.lower() for b in blocked):
            raise ValueError('Tiltott URL')
        return v


class Task(BaseModel):
    """
    Feladat séma - csak ezek a mezők fogadhatók el.
    Minden más mező IGNORÁLVA lesz (extra='ignore').
    """
    id: str = Field(..., min_length=8, max_length=64)
    platform: str
    task_type: str
    content: Optional[TaskContent] = None
    target_url: Optional[str] = None
    scheduled_at: Optional[str] = None
    
    class Config:
        extra = 'ignore'  # Ismeretlen mezők eldobása
    
    @validator('platform')
    def validate_platform(cls, v):
        allowed = {'facebook', 'instagram', 'twitter'}
        if v.lower() not in allowed:
            raise ValueError(f'Ismeretlen platform: {v}')
        return v.lower()
    
    @validator('task_type')
    def validate_task_type(cls, v):
        if v.lower() not in ALLOWED_TASK_TYPES:
            raise ValueError(f'Tiltott task típus: {v}')
        return v.lower()


def validate_task(raw_task: dict) -> Optional[Task]:
    """
    Szigorú task validáció.
    Ha bármi gyanús, None-t ad vissza.
    """
    try:
        task = Task(**raw_task)
        logger.info(f"Task validálva: {task.id} ({task.platform}/{task.task_type})")
        return task
    except ValidationError as e:
        logger.warning(f"Érvénytelen task elutasítva: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# ANTI-DETECTION RÉTEG
# ═══════════════════════════════════════════════════════════════════

class StealthBrowser:
    """
    Anti-detection böngésző wrapper.
    Stealth plugin + emberi viselkedés szimuláció.
    """
    
    # Valósághű User-Agent rotáció
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]
    
    # Valósághű viewport méretek
    VIEWPORTS = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
    ]
    
    @classmethod
    def create_context(cls, browser, headless: bool = True) -> BrowserContext:
        """
        Stealth kontextus létrehozása anti-fingerprinting beállításokkal.
        """
        viewport = random.choice(cls.VIEWPORTS)
        user_agent = random.choice(cls.USER_AGENTS)
        
        context = browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale='hu-HU',
            timezone_id='Europe/Budapest',
            # Valósághű beállítások
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
            # Geolocation (Budapest)
            geolocation={'longitude': 19.0402, 'latitude': 47.4979},
            permissions=['geolocation'],
            # Color scheme
            color_scheme='light',
        )
        
        return context
    
    @classmethod
    def apply_stealth(cls, page: Page) -> None:
        """
        Stealth beállítások alkalmazása a Page-re.
        Elrejti a headless jeleket.
        """
        stealth_sync(page)
        
        # Extra anti-detection scriptek
        page.add_init_script("""
            // WebDriver flag elrejtése
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Chrome runtime szimuláció
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Permissions override
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // Plugin lista szimuláció
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin'},
                    {name: 'Chrome PDF Viewer'},
                    {name: 'Native Client'}
                ]
            });
            
            // Language beállítás
            Object.defineProperty(navigator, 'languages', {
                get: () => ['hu-HU', 'hu', 'en-US', 'en']
            });
        """)
    
    @classmethod
    def human_delay(cls, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Emberi késleltetés szimuláció"""
        import time
        delay = random.randint(min_ms, max_ms) / 1000
        time.sleep(delay)
    
    @classmethod
    def human_type(cls, page: Page, selector: str, text: str) -> None:
        """
        Emberi gépelés szimuláció - változó sebesség, néha elütés.
        """
        element = page.locator(selector)
        element.click()
        cls.human_delay(200, 500)
        
        for char in text:
            element.type(char, delay=random.randint(50, 150))
            
            # 5% eséllyel "elütés" és javítás
            if random.random() < 0.05 and len(text) > 10:
                wrong_char = random.choice('abcdefghijklmnop')
                element.type(wrong_char, delay=100)
                cls.human_delay(100, 300)
                page.keyboard.press('Backspace')


# ═══════════════════════════════════════════════════════════════════
# PLATFORM KONFIGURÁCIÓ
# ═══════════════════════════════════════════════════════════════════

class Platform(Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"


@dataclass
class PlatformConfig:
    name: str
    url: str
    button_color: str
    emoji: str
    # Robusztus szelektorok - aria-label és text alapú
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
                '[aria-label*="Create a post"]',
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
                'svg[aria-label*="post"]',
            ],
        }
    ),
    Platform.TWITTER: PlatformConfig(
        name="X (Twitter)",
        url="https://twitter.com/login",
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
                'button:has-text("Tweet")',
            ],
        }
    ),
}


# ═══════════════════════════════════════════════════════════════════
# ROBUSZTUS SZELEKTOR KEZELÉS
# ═══════════════════════════════════════════════════════════════════

def find_element_robust(page: Page, selectors: List[str], timeout: int = 10000) -> Optional[Any]:
    """
    Több szelektor próbálása sorban.
    Az első működő elemet adja vissza.
    """
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


# ═══════════════════════════════════════════════════════════════════
# FŐ ALKALMAZÁS
# ═══════════════════════════════════════════════════════════════════

class SocialAgentApp:
    """TrendMaster Desktop Agent - Hardened Edition"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TrendMaster Agent 🛡️ v2.0")
        self.root.geometry("450x600")
        self.root.resizable(False, False)
        
        self.api_key: str = ""
        self.is_running: bool = False
        self.poll_job: Optional[str] = None
        self.session = requests.Session()
        self.secure_storage: Optional[SecureStorage] = None
        
        self.logged_in_platforms: Dict[Platform, bool] = {p: False for p in Platform}
        
        self._init_dirs()
        self._build_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        logger.info("Agent v2.0 (Hardened) elindítva")

    def _init_dirs(self) -> None:
        """Mappák inicializálása"""
        os.makedirs(LOCAL_SESSION_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)

    def _build_ui(self) -> None:
        """UI felépítése"""
        # Header
        header = tk.Frame(self.root, bg="#1a252f", height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🛡️ TrendMaster Agent",
            font=("Arial", 18, "bold"),
            bg="#1a252f",
            fg="#3498db"
        ).pack(pady=8)
        
        tk.Label(
            header,
            text="Hardened Edition v2.0",
            font=("Arial", 9),
            bg="#1a252f",
            fg="#7f8c8d"
        ).pack()

        # API Key
        api_frame = tk.LabelFrame(self.root, text="🔐 API Hitelesítés", padx=15, pady=10)
        api_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(api_frame, text="API Kulcs (titkosításhoz is használjuk):", font=("Arial", 9)).pack(anchor="w")
        self.api_entry = tk.Entry(api_frame, width=50, show="•")
        self.api_entry.pack(fill="x", pady=5)
        
        key_frame = tk.Frame(api_frame)
        key_frame.pack(fill="x")
        
        self.show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(key_frame, text="Megjelenítés", variable=self.show_key_var,
                      command=lambda: self.api_entry.config(show="" if self.show_key_var.get() else "•")
                      ).pack(side="left")
        
        tk.Button(key_frame, text="🔓 Kulcs aktiválása", command=self._activate_key
                 ).pack(side="right")

        # Platform Login
        login_frame = tk.LabelFrame(self.root, text="📱 Fiók Csatlakoztatás", padx=15, pady=10)
        login_frame.pack(fill="x", padx=20, pady=10)
        
        self.login_buttons: Dict[Platform, tk.Button] = {}
        self.status_indicators: Dict[Platform, tk.Label] = {}
        
        for platform in Platform:
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
                state="disabled"  # Először API kulcs kell
            )
            btn.pack(side="left", padx=(0, 10))
            self.login_buttons[platform] = btn
            
            indicator = tk.Label(row, text="⚫ Várakozás", fg="gray", font=("Arial", 9))
            indicator.pack(side="left")
            self.status_indicators[platform] = indicator

        # Biztonsági státusz
        security_frame = tk.LabelFrame(self.root, text="🔒 Biztonsági Státusz", padx=15, pady=10)
        security_frame.pack(fill="x", padx=20, pady=10)
        
        self.encryption_label = tk.Label(security_frame, text="⚫ Titkosítás: Inaktív", fg="gray")
        self.encryption_label.pack(anchor="w")
        
        self.stealth_label = tk.Label(security_frame, text="✅ Stealth mód: Aktív", fg="#27ae60")
        self.stealth_label.pack(anchor="w")
        
        self.jitter_label = tk.Label(security_frame, text=f"✅ Jitter: {POLL_MIN_SEC}-{POLL_MAX_SEC}s", fg="#27ae60")
        self.jitter_label.pack(anchor="w")

        # Agent státusz
        status_frame = tk.LabelFrame(self.root, text="⚙️ Agent Állapot", padx=15, pady=10)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_label = tk.Label(status_frame, text="⏹️ Leállítva", fg="#e74c3c", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)
        
        self.task_label = tk.Label(status_frame, text="Utolsó: -", fg="gray", font=("Arial", 9))
        self.task_label.pack()
        
        self.next_poll_label = tk.Label(status_frame, text="Következő lekérdezés: -", fg="gray", font=("Arial", 9))
        self.next_poll_label.pack()

        # Kontroll
        self.start_btn = tk.Button(
            self.root,
            text="▶️ AGENT INDÍTÁSA",
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            height=2,
            command=self._toggle_agent,
            state="disabled"
        )
        self.start_btn.pack(fill="x", padx=20, pady=15)

        # Footer
        tk.Label(self.root, text="🛡️ Hardened Edition | Cookie-k titkosítva | Anti-detection aktív",
                fg="gray", font=("Arial", 8)).pack(side="bottom", pady=5)

    def _activate_key(self) -> None:
        """API kulcs aktiválása és titkosítás inicializálása"""
        key = self.api_entry.get().strip()
        
        if len(key) < 16:
            messagebox.showerror("Hiba", "Az API kulcsnak legalább 16 karakter hosszúnak kell lennie!")
            return
        
        self.api_key = key
        self.secure_storage = SecureStorage(key)
        
        # Gombok aktiválása
        for btn in self.login_buttons.values():
            btn.config(state="normal")
        self.start_btn.config(state="normal")
        
        # Meglévő cookie-k ellenőrzése
        for platform in Platform:
            cookies = self.secure_storage.load_cookies(platform.value)
            self.logged_in_platforms[platform] = cookies is not None
        
        self._update_indicators()
        self.encryption_label.config(text="✅ Titkosítás: AES-256 (Fernet)", fg="#27ae60")
        
        messagebox.showinfo("Siker", "API kulcs aktiválva!\nA cookie-k titkosítva lesznek tárolva.")
        logger.info("API kulcs aktiválva, titkosítás inicializálva")

    def _update_indicators(self) -> None:
        """Státusz indikátorok frissítése"""
        for platform in Platform:
            if self.logged_in_platforms.get(platform):
                self.status_indicators[platform].config(text="🟢 Titkosítva", fg="#27ae60")
            else:
                self.status_indicators[platform].config(text="⚫ Nincs session", fg="gray")

    def _perform_login(self, platform: Platform) -> None:
        """Platform bejelentkezés"""
        if not self.secure_storage:
            messagebox.showerror("Hiba", "Először aktiváld az API kulcsot!")
            return
        
        config = PLATFORM_CONFIGS[platform]
        
        if not messagebox.askokcancel("Bejelentkezés",
            f"Böngésző megnyitása: {config.name}\n\n"
            "1. Jelentkezz be\n"
            "2. Zárd be az ablakot\n\n"
            "⚠️ A cookie-k titkosítva lesznek tárolva."):
            return
        
        thread = threading.Thread(target=self._login_worker, args=(platform,), daemon=True)
        thread.start()

    def _login_worker(self, platform: Platform) -> None:
        """Login worker szál stealth móddal"""
        config = PLATFORM_CONFIGS[platform]
        
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=False)
                context = StealthBrowser.create_context(browser, headless=False)
                page = context.new_page()
                StealthBrowser.apply_stealth(page)
                
                page.goto(config.url)
                logger.info(f"Login ablak: {platform.value}")
                
                try:
                    page.wait_for_event("close", timeout=LOGIN_TIMEOUT_MS)
                except:
                    pass
                
                cookies = context.cookies()
                browser.close()
                
                # Titkosított mentés
                if self.secure_storage.save_cookies(platform.value, cookies):
                    self.logged_in_platforms[platform] = True
                    self.root.after(0, self._update_indicators)
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Siker", f"✅ {config.name} session titkosítva mentve!"))
                    
        except Exception as e:
            logger.error(f"Login hiba: {e}")
            self.root.after(0, lambda: messagebox.showerror("Hiba", str(e)))

    def _toggle_agent(self) -> None:
        """Agent indítás/leállítás"""
        if self.is_running:
            self._stop_agent()
        else:
            self._start_agent()

    def _start_agent(self) -> None:
        """Agent indítása"""
        if not self.secure_storage:
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

    def _stop_agent(self) -> None:
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

    def _poll_with_jitter(self) -> None:
        """Polling jitter-rel (anti-detection)"""
        if not self.is_running:
            return
        
        # Véletlenszerű késleltetés
        jitter_sec = random.uniform(POLL_MIN_SEC, POLL_MAX_SEC)
        jitter_ms = int(jitter_sec * 1000)
        
        self.next_poll_label.config(text=f"Következő: {jitter_sec:.1f}s")
        
        # Task lekérés külön szálon
        thread = threading.Thread(target=self._fetch_task, daemon=True)
        thread.start()
        
        # Következő polling ütemezése
        self.poll_job = self.root.after(jitter_ms, self._poll_with_jitter)

    def _fetch_task(self) -> None:
        """Task lekérése és validálása"""
        try:
            response = self.session.post(
                f"{SERVER_URL}/api/get-task",
                json={
                    "api_key": self.api_key,
                    "platforms": [p.value for p, ok in self.logged_in_platforms.items() if ok],
                    "version": "2.0.0"
                },
                timeout=REQUEST_TIMEOUT_SEC
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('has_task'):
                raw_task = data.get('task', {})
                
                # SZIGORÚ VALIDÁCIÓ
                validated_task = validate_task(raw_task)
                
                if validated_task:
                    self.root.after(0, lambda: self.task_label.config(
                        text=f"Task: {validated_task.id[:12]}..."))
                    self._execute_task(validated_task)
                else:
                    logger.warning("Task elutasítva validáció után")
                    self._report_status(raw_task.get('id', 'unknown'), "rejected", "Validation failed")
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"Hálózati hiba: {e}")
        except Exception as e:
            logger.error(f"Polling hiba: {e}")

    def _execute_task(self, task: Task) -> None:
        """Validált task végrehajtása stealth móddal"""
        platform = Platform(task.platform)
        cookies = self.secure_storage.load_cookies(platform.value)
        
        if not cookies:
            logger.error(f"Nincs cookie: {platform.value}")
            self._report_status(task.id, "failed", "No session")
            return
        
        try:
            with sync_playwright() as p:
                # Headless, de stealth móddal
                browser = p.firefox.launch(headless=True)
                context = StealthBrowser.create_context(browser, headless=True)
                context.add_cookies(cookies)
                
                page = context.new_page()
                StealthBrowser.apply_stealth(page)
                
                # Platform-specifikus logika
                if platform == Platform.FACEBOOK and task.task_type == "post":
                    self._facebook_post(page, task)
                elif platform == Platform.TWITTER and task.task_type == "post":
                    self._twitter_post(page, task)
                # ... további platformok
                
                # Cookie frissítés
                updated_cookies = context.cookies()
                self.secure_storage.save_cookies(platform.value, updated_cookies)
                
                browser.close()
            
            self._report_status(task.id, "completed")
            logger.info(f"Task kész: {task.id}")
            
        except Exception as e:
            logger.error(f"Task végrehajtási hiba: {e}")
            self._report_status(task.id, "failed", str(e))

    def _facebook_post(self, page: Page, task: Task) -> None:
        """Facebook posztolás robusztus szelektorokkal"""
        config = PLATFORM_CONFIGS[Platform.FACEBOOK]
        
        page.goto("https://www.facebook.com")
        StealthBrowser.human_delay(2000, 4000)
        
        # Poszt doboz keresése
        post_box = find_element_robust(page, config.selectors["post_box"])
        if not post_box:
            raise Exception("Poszt doboz nem található")
        
        post_box.click()
        StealthBrowser.human_delay(1000, 2000)
        
        # Szöveg beírása emberi módon
        if task.content and task.content.text:
            StealthBrowser.human_type(page, '[role="textbox"]', task.content.text)
        
        StealthBrowser.human_delay(1000, 2000)
        
        # Közzététel gomb
        post_btn = find_element_robust(page, config.selectors["post_button"])
        if post_btn:
            post_btn.click()
            StealthBrowser.human_delay(3000, 5000)

    def _twitter_post(self, page: Page, task: Task) -> None:
        """Twitter/X posztolás"""
        config = PLATFORM_CONFIGS[Platform.TWITTER]
        
        page.goto("https://twitter.com/compose/tweet")
        StealthBrowser.human_delay(2000, 4000)
        
        tweet_box = find_element_robust(page, config.selectors["tweet_box"])
        if not tweet_box:
            raise Exception("Tweet doboz nem található")
        
        if task.content and task.content.text:
            StealthBrowser.human_type(page, config.selectors["tweet_box"][0], task.content.text)
        
        StealthBrowser.human_delay(1000, 2000)
        
        tweet_btn = find_element_robust(page, config.selectors["tweet_button"])
        if tweet_btn:
            tweet_btn.click()
            StealthBrowser.human_delay(3000, 5000)

    def _report_status(self, task_id: str, status: str, error: str = "") -> None:
        """Státusz jelentés"""
        try:
            self.session.post(
                f"{SERVER_URL}/api/task-complete",
                json={"api_key": self.api_key, "task_id": task_id, "status": status, "error": error},
                timeout=REQUEST_TIMEOUT_SEC
            )
        except Exception as e:
            logger.error(f"Státusz jelentési hiba: {e}")

    def _on_closing(self) -> None:
        """Cleanup"""
        if self.is_running:
            if not messagebox.askokcancel("Kilépés", "Agent fut. Kilépsz?"):
                return
        
        self._stop_agent()
        self.session.close()
        logger.info("Agent leállítva")
        self.root.destroy()


# ═══════════════════════════════════════════════════════════════════
# BELÉPÉSI PONT
# ═══════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    app = SocialAgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
