# ✅ TrendMaster TODO - 2025-11-26 (Kedd)

## 🚨 **SÜRGŐS KÉRDÉSEK (Döntés szükséges!)**

### ❓ **1. Agent Architektúra - Melyik utat választjuk?**

**A. Gyors MVP (1 hét):**
- [ ] Desktop Agent működésre bírás
- [ ] Manual notification ha offline
- [ ] Egyszerű, gyors, de korlátozott

**B. Hibrid Megoldás (2-3 hét):** ⭐ **AJÁNLOTT**
- [ ] Desktop Agent (primary)
- [ ] Cloud Agent Railway-en (fallback)
- [ ] Cookie sync Desktop ↔ Cloud
- [ ] Intelligens task routing
- [ ] Működik mindig (telefon/desktop)

**C. Enterprise (3-6 hónap):**
- [ ] Hibrid rendszer
- [ ] Mobile App (Flutter)
- [ ] Official API-k (Facebook Graph, Instagram)
- [ ] Residential proxy rendszer
- [ ] Komplett, de időigényes

**DÖNTÉS: ______** (A / B / C)

---

### ❓ **2. OAuth - Szükséges-e Google/Facebook OAuth login?**

**Jelenlegi helyzet:**
- ✅ Email/password regisztráció működik
- ✅ API key alapú auth működik
- ❌ OAuth nincs implementálva

**Opciók:**

**A. NEM kell OAuth (gyorsabb MVP):**
- [ ] Megtartjuk az email/password login-t
- [ ] Desktop Agent manual Facebook login (cookie-alapú)
- [ ] Egyszerűbb, gyorsabb piacra jutás

**B. KELL OAuth (professzionálisabb):**
- [ ] Google OAuth implementálás
- [ ] Facebook OAuth implementálás
- [ ] "Login with Google/Facebook" gombok
- [ ] Felhasználóbarátabb

**DÖNTÉS: ______** (KELL / NEM KELL)

---

### ❓ **3. Desktop Agent Tesztelés - Mikor kezdjük?**

**Függőségek:**
```bash
pip install requests cryptography playwright playwright-stealth pydantic
playwright install firefox
```

**Tesztelési lépések:**
- [ ] Függőségek telepítése
- [ ] Agent indítása (`python agent/trendmaster_agent.py`)
- [ ] User regisztráció/login tesztelése
- [ ] Facebook manual login
- [ ] Task végrehajtás tesztelése
- [ ] Cookie titkosítás ellenőrzése

**DÖNTÉS: Mikor? ______** (Ma / Holnap / Később)

---

### ❓ **4. Cloud Agent - Railway-en futtatjuk?**

**Ha IGEN:**
- [ ] `cloud_agent.py` létrehozása
- [ ] Headless Playwright konfiguráció
- [ ] Cookie sync endpoint-ok
- [ ] Residential proxy integráció (opcionális, $30-100/hó)
- [ ] Railway deployment

**Ha NEM:**
- [ ] Csak Desktop Agent
- [ ] Manual notification ha offline

**DÖNTÉS: ______** (IGEN / NEM / KÉSŐBB)

---

### ❓ **5. Publikálási Workflow - Facebook Graph API vagy Cookie-alapú?**

**A. Cookie-alapú (Desktop Agent):**
- ✅ Ingyenes
- ✅ Rugalmas (nincs API limitáció)
- ⚠️ Facebook detektálhatja
- ⚠️ Cookie lejárat

**B. Facebook Graph API (Official):**
- ✅ Hivatalos, stabil
- ✅ Kevesebb detektálás
- ❌ Csak Page-ekre működik (NEM personal profile!)
- ❌ Drága (Business account)
- ❌ Rate limits

**DÖNTÉS: ______** (Cookie / API / Mindkettő)

---

## 📋 **TECHNIKAI FELADATOK**

### 🔧 **Backend**

#### Agent API
- [ ] Tesztelni `/api/agent/user/register` végpontot
- [ ] Tesztelni `/api/agent/user/login` végpontot
- [ ] Tesztelni `/api/agent/register` (Desktop Agent regisztráció)
- [ ] Tesztelni `/api/agent/get-task` (Task polling)
- [ ] Cookie sync endpoint-ok implementálása (ha Cloud Agent)

#### Database
- [ ] Ellenőrizni hogy a `users` tábla megfelelően működik
- [ ] Tesztelni API key generálást
- [ ] Password hash biztonság ellenőrzése (bcrypt)

#### OAuth (ha kell)
- [ ] Google OAuth 2.0 setup (Credentials, Consent Screen)
- [ ] Flask-OAuthlib vagy Authlib telepítése
- [ ] `/auth/google` route létrehozása
- [ ] `/auth/google/callback` route létrehozása
- [ ] Session management

---

### 🎨 **Frontend**

#### Login/Register Oldal
- [ ] `templates/login.html` létrehozása
- [ ] Email/password form
- [ ] Google OAuth gomb (ha kell)
- [ ] Facebook OAuth gomb (ha kell)
- [ ] Regisztrációs link
- [ ] Elfelejtett jelszó link

#### Dashboard
- [ ] Agent státusz widget (online/offline)
- [ ] Task queue megjelenítés
- [ ] Notification rendszer (Agent offline figyelmeztetés)

#### Editor
- [ ] SEO Panel tesztelése éles környezetben
- [ ] Forrás Link tesztelése különböző forrásokkal
- [ ] Batch Upload tesztelése nagy mappákkal (50+ kép)

---

### 🖥️ **Desktop Agent**

#### Tesztelés
- [ ] Függőségek telepítése
- [ ] GUI megjelenítés tesztelése (Tkinter)
- [ ] API key input tesztelése
- [ ] Facebook login flow tesztelése
- [ ] Cookie titkosítás/desziffrálás tesztelése
- [ ] Task polling tesztelése
- [ ] Stealth mode ellenőrzése (Facebook detektálás)

#### Bug Fixek
- [ ] Playwright verzió kompatibilitás
- [ ] Cookie path ellenőrzése (~/.trendmaster/sessions/)
- [ ] HWID generálás tesztelése (MAC, CPU, Hostname)
- [ ] Error handling javítása

---

### ☁️ **Cloud Agent** (ha építjük)

#### Implementáció
- [ ] `cloud_agent.py` létrehozása
- [ ] Headless Playwright setup
- [ ] Cookie betöltés adatbázisból
- [ ] Task polling loop
- [ ] Anti-detection (User-Agent rotation, viewport randomization)
- [ ] Proxy integráció (opcionális)

#### Deployment
- [ ] Railway config (`railway.toml` vagy `Procfile`)
- [ ] Environment variables setup
- [ ] Memória/CPU limitek beállítása
- [ ] Health check endpoint (`/health`)
- [ ] Logging & monitoring

---

## 🧪 **TESZTELÉS & QA**

### End-to-End Flow
- [ ] User regisztráció → API kulcs generálás
- [ ] Desktop Agent indítás → API kulcs bevitel
- [ ] Facebook login → Cookie mentés
- [ ] Dashboard-on poszt generálás → Task létrehozás
- [ ] Desktop Agent task polling → Task végrehajtás
- [ ] Poszt megjelenik Facebook-on

### Edge Cases
- [ ] Mi történik ha Desktop Agent offline?
- [ ] Mi történik ha cookie lejár?
- [ ] Mi történik ha Facebook blokkolja az Agent-et?
- [ ] Mi történik ha több Agent fut egyszerre?
- [ ] Mi történik ha Task timeout-ol?

---

## 📚 **DOKUMENTÁCIÓ**

- [ ] `README.md` frissítése (architektúra diagram)
- [ ] Desktop Agent használati útmutató
- [ ] Cloud Agent deployment guide (ha kell)
- [ ] API dokumentáció (OpenAPI/Swagger)
- [ ] Video tutorial felvétele (5 perces bemutató)

---

## 🎯 **PRIORITÁSI SORREND**

### 🔴 **HIGH (Ma/Holnap):**
1. **Döntések meghozatala** (Agent architektúra, OAuth)
2. Desktop Agent tesztelés
3. Login/Register oldal UI

### 🟡 **MEDIUM (Ezen a héten):**
4. Cloud Agent implementálás (ha építjük)
5. Cookie sync mechanizmus
6. OAuth implementálás (ha kell)

### 🟢 **LOW (Később):**
7. Mobile App (Flutter)
8. Residential proxy
9. Official API integráció

---

## 💡 **ÖTLETEK / LATER**

- [ ] Browser extension (Chrome/Firefox) - Alternative to Desktop Agent?
- [ ] Scheduling rendszer (időzített posztok)
- [ ] A/B testing posztokhoz
- [ ] Analytics dashboard (engagement metrics)
- [ ] Multi-language support
- [ ] White-label verzió (más brandek számára)

---

## ❓ **KÉRDÉSEK HOLNAPRA**

1. ✅ **Melyik Agent architektúrát választjuk?** (MVP / Hibrid / Enterprise)
2. ✅ **Kell-e OAuth vagy elég email/password?**
3. ✅ **Mikor teszteljük a Desktop Agent-et?**
4. ✅ **Építünk-e Cloud Agent-et Railway-en?**
5. ✅ **Cookie-alapú vagy Facebook Graph API?**
6. **Van-e még más kérdés/igény?**

---

**Készült:** 2025-11-25 01:30
**Következő update:** 2025-11-26 este
**Felelős:** Tamas + Claude
