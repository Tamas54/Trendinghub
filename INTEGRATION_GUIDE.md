# 🚀 TrendMaster SaaS Hibrid Architektúra

## Integrációs Útmutató

---

## 📁 Új Fájlok

| Fájl | Leírás | Hol fut |
|------|--------|---------|
| `database_saas.py` | SaaS adatbázis extension | Szerver (Railway) |
| `agent_api.py` | Flask Blueprint az Agent API-hoz | Szerver (Railway) |
| `trendmaster_agent.py` | Desktop Agent kliens | Kliens gép |

---

## 🔧 SZERVER OLDALI INTEGRÁCIÓ

### 1. Másold be a fájlokat

```bash
# Railway projektbe
cp database_saas.py /path/to/your/project/
cp agent_api.py /path/to/your/project/
```

### 2. Módosítsd az `app.py`-t

Az `app.py` elejére add hozzá:

```python
# === ÚJ IMPORT ===
from agent_api import agent_api
from database_saas import saas_db

# Flask app létrehozása után:
app = Flask(__name__)

# === ÚJ: Agent API Blueprint regisztrálása ===
app.register_blueprint(agent_api)
```

### 3. Frissítsd a `requirements.txt`-et

```txt
# Meglévők mellett:
pydantic>=2.0.0
cryptography>=41.0.0
playwright>=1.40.0
playwright-stealth>=1.0.6
```

### 4. Adatbázis migráció

Az első indításkor automatikusan létrejönnek az új táblák:
- `users` - SaaS felhasználók
- `agents` - Desktop Agent-ek
- `platform_accounts` - Social media fiókok
- `tasks` - Végrehajtandó feladatok
- `task_logs` - Audit napló

---

## 💻 KLIENS OLDALI SETUP

### 1. Agent telepítése (felhasználó gépén)

```bash
# Python környezet
python -m venv trendmaster_agent
source trendmaster_agent/bin/activate  # Linux/Mac
# vagy: trendmaster_agent\Scripts\activate  # Windows

# Függőségek
pip install requests cryptography playwright playwright-stealth pydantic

# Playwright böngésző
playwright install firefox

# Agent indítása
python trendmaster_agent.py
```

### 2. Környezeti változók (opcionális)

```bash
export TRENDMASTER_SERVER="https://your-app.up.railway.app"
```

---

## 🔄 API VÉGPONTOK

### Felhasználó regisztráció/login

```bash
# Regisztráció
POST /api/agent/user/register
{
    "email": "user@example.com",
    "password": "securepassword",
    "name": "John Doe"
}

# Login
POST /api/agent/user/login
{
    "email": "user@example.com",
    "password": "securepassword"
}
# Response: { "api_key": "tm_xxxx..." }
```

### Agent műveletek

```bash
# Agent regisztráció
POST /api/agent/register
Headers: X-API-Key: tm_xxxx
{
    "name": "My Desktop Agent",
    "hwid_hash": "sha256...",
    "capabilities": ["facebook", "instagram"]
}

# Task lekérés
POST /api/agent/get-task
{
    "agent_id": "agent_xxxx",
    "platforms": ["facebook", "instagram"]
}

# Státusz jelentés
POST /api/agent/task-status
{
    "agent_id": "agent_xxxx",
    "task_id": "task_xxxx",
    "status": "completed"
}

# Heartbeat
POST /api/agent/heartbeat
{
    "agent_id": "agent_xxxx",
    "platforms": ["facebook"]
}
```

### Task létrehozás (web dashboard-ból)

```bash
POST /api/agent/create-task
Headers: X-API-Key: tm_xxxx
{
    "platform": "facebook",
    "task_type": "post",
    "content": "Hello World! 🚀",
    "scheduled_at": "2025-01-01T12:00:00"
}
```

---

## 🔐 BIZTONSÁGI FUNKCIÓK

### Cookie titkosítás
- **Algoritmus**: AES-256 (Fernet)
- **Kulcs származtatás**: PBKDF2 (480,000 iteráció)
- **Salt**: Hardware ID (MAC + CPU + Hostname)
- **Tárolás**: `~/.trendmaster/sessions/*.enc`

### Anti-detection
- **Stealth plugin**: playwright-stealth
- **WebDriver elrejtés**: navigator.webdriver = undefined
- **User-Agent rotáció**: 4 valós böngésző fingerprint
- **Viewport randomizálás**: 4 népszerű felbontás
- **Emberi gépelés**: változó sebesség + elütések
- **Jitter polling**: 8-18 sec random késleltetés

### Task validáció
- **Pydantic séma**: szigorú típusellenőrzés
- **Whitelist**: csak engedélyezett task típusok
- **XSS védelem**: script tagek eltávolítása
- **URL validáció**: csak HTTPS, tiltott domének

---

## 📊 ADATFOLYAM

```
┌─────────────────────────────────────────────────────────────────┐
│                         WEB DASHBOARD                           │
│  (Felhasználó létrehoz egy posztot, kiválasztja az időpontot)   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAILWAY SZERVER                            │
│  POST /api/agent/create-task                                    │
│  → tasks tábla: status='pending', scheduled_at='...'           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DESKTOP AGENT                              │
│  GET /api/agent/get-task (polling 8-18s jitter-rel)            │
│  ← task: {id, platform, content, ...}                          │
│                                                                 │
│  1. Cookie visszafejtés (Fernet)                               │
│  2. Stealth browser indítás                                    │
│  3. Platform művelet végrehajtás                               │
│  4. Cookie frissítés + titkosítás                              │
│                                                                 │
│  POST /api/agent/task-status {status: 'completed'}             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAILWAY SZERVER                            │
│  tasks tábla: status='completed', completed_at='...'           │
│  task_logs: esemény naplózás                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 TESZTELÉS

### 1. Szerver API teszt

```bash
# User regisztráció
curl -X POST https://your-app.up.railway.app/api/agent/user/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testpassword123","name":"Test User"}'

# Agent regisztráció
curl -X POST https://your-app.up.railway.app/api/agent/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tm_xxxx" \
  -d '{"name":"Test Agent","capabilities":["facebook"]}'
```

### 2. Agent teszt

```bash
# Agent indítása
python trendmaster_agent.py

# GUI megjelenik:
# 1. API kulcs beírása
# 2. Facebook login
# 3. Agent indítása
```

---

## 📋 TODO / Következő lépések

- [ ] Web dashboard frissítése (task létrehozás UI)
- [ ] Agent letöltési oldal (landing page)
- [ ] Instagram és Twitter executor finomítás
- [ ] Média feltöltés támogatás
- [ ] Agent auto-update mechanizmus
- [ ] Billing integráció (Stripe)
- [ ] Rate limiting per user/plan

---

## 🆘 Hibaelhárítás

### Agent nem tud csatlakozni
1. Ellenőrizd a `TRENDMASTER_SERVER` URL-t
2. Ellenőrizd az API kulcsot
3. Nézd meg a Railway logokat

### Cookie titkosítás hiba
1. Töröld a `~/.trendmaster/sessions/*.enc` fájlokat
2. Jelentkezz be újra a platformokon

### Playwright hiba
```bash
playwright install --with-deps firefox
```

### Task nem hajtódik végre
1. Agent fut? (Zöld státusz)
2. Van aktív platform? (🟢 Aktív)
3. Task platform = Agent platform?

---

## 📞 Támogatás

Ha kérdésed van, nyiss issue-t a GitHub repo-ban vagy írj az admin@trendhub.hu címre.
