# TrendMaster SaaS Integráció - Claude Code Prompt

## FELADAT

Integráld a `newscripts/` mappában lévő új fájlokat a meglévő TrendMaster projektbe. Ez egy hibrid SaaS architektúra: Railway szerver + Desktop Agent rendszer.

---

## ÚJ FÁJLOK (newscripts/ mappából)

| Fájl | Cél hely | Leírás |
|------|----------|--------|
| `database_saas.py` | projekt root | Multi-tenant DB (users, agents, tasks táblák) |
| `agent_api.py` | projekt root | REST API Blueprint az Agent-eknek |
| `seo_api.py` | projekt root | SEO/hashtag/emoji API Blueprint |
| `editor_v2.html` | `templates/editor.html` FELÜLÍRÁS | Frissített editor SEO score-ral |
| `dashboard_agent_section.html` | beillesztés `dashboard.html`-be | Agent kezelő UI szekció |
| `trendmaster_agent.py` | külön mappa vagy releases | Desktop Agent kliens |

---

## LÉPÉSEK

### 1. Fájlok másolása

```bash
cp newscripts/database_saas.py .
cp newscripts/agent_api.py .
cp newscripts/seo_api.py .
cp newscripts/editor_v2.html templates/editor.html
cp newscripts/trendmaster_agent.py agent/
```

### 2. app.py MÓDOSÍTÁS

Az `app.py` fájl elején az importok közé add hozzá:

```python
# === ÚJ IMPORTS - SaaS rendszer ===
from agent_api import agent_api
from seo_api import seo_api
```

A Flask app inicializálás után (kb. `app = Flask(__name__)` sor után) regisztráld a blueprint-eket:

```python
# === ÚJ BLUEPRINTS - SaaS rendszer ===
app.register_blueprint(agent_api)  # /api/agent/* végpontok
app.register_blueprint(seo_api)    # /api/optimize-seo, /api/generate-hashtags, stb.
```

### 3. dashboard.html MÓDOSÍTÁS

A `templates/dashboard.html` fájlban keresd meg a stats grid végét (kb. a `</div>` ami a 4 statisztika kártyát zárja, a "Utolsó frissítés" után).

Illeszd be IDE a `dashboard_agent_section.html` TELJES tartalmát (a `<section id="agentSection">` résztől a záró `</script>`-ig).

A beszúrás helye kb. így néz ki:
```html
            </div>  <!-- stats grid vége -->
        </div>

        <!-- === ITT ILLESZD BE A dashboard_agent_section.html TARTALMÁT === -->
        <section id="agentSection" class="mb-12">
        ...
        </section>
        <!-- === BESZÚRÁS VÉGE === -->

        <div id="loadingState" ...>
```

### 4. requirements.txt FRISSÍTÉS

Ellenőrizd hogy ezek benne vannak (ha nincs, add hozzá):

```
pydantic>=2.0.0
cryptography>=41.0.0
playwright>=1.40.0
playwright-stealth>=1.0.6
```

### 5. Adatbázis inicializálás

Az első indításkor a `database_saas.py` automatikusan létrehozza az új táblákat. Ha manuálisan akarod:

```python
from database_saas import SaaSDatabase
db = SaaSDatabase()
# Táblák létrejönnek automatikusan
```

---

## ELLENŐRZÉS

Sikeres integráció után ezek működnek:

1. **Editor oldal** (`/editor`):
   - SEO score panel látható (gépelés közben frissül)
   - "Mappa Spoofing" szekció a jobb oldalon
   - Forrás link a headerben (ha van source_url)

2. **Dashboard** (`/dashboard`):
   - "🤖 Agent Kezelés" szekció megjelenik
   - API kulcs beállítás modal működik

3. **API végpontok**:
   - `POST /api/agent/user/register` - user regisztráció
   - `POST /api/agent/register` - agent regisztráció
   - `POST /api/agent/get-task` - task lekérés
   - `POST /api/optimize-seo` - SEO optimalizálás
   - `POST /api/generate-hashtags` - hashtag generálás

---

## FONTOS MEGJEGYZÉSEK

- A `trendmaster_agent.py` a FELHASZNÁLÓ gépén fut, NEM a szerveren!
- Az Agent API-hoz API kulcs kell (`X-API-Key` header)
- A `database_saas.py` a meglévő `database.py` MELLÉ kerül, nem felülírja
- Az editor.html FELÜLÍRÓDIK az új verzióval

---

## GYORS TESZT

```bash
# Szerver indítása
python app.py

# Böngészőben:
# 1. /editor - SEO panel megjelenik?
# 2. /dashboard - Agent szekció megjelenik?
# 3. API teszt:
curl -X POST http://localhost:5000/api/agent/user/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","name":"Test"}'
```

Ha minden OK, deploy Railway-re! 🚀
