# 🔄 TrendMaster Frissítési Útmutató

## Lili kérései implementálva! ✅

---

## 📦 Új/Frissített Fájlok

| Fájl | Leírás | Mit csinál |
|------|--------|-----------|
| `editor_v2.html` | Frissített editor | SEO score, mappa feltöltés, forrás link |
| `seo_api.py` | SEO API végpontok | AI optimalizálás, hashtag, emoji generálás |
| `dashboard_agent_section.html` | Dashboard kiegészítés | Agent kezelés UI |

---

## 🎯 Implementált Funkciók

### 1️⃣ Mappa Feltöltés Spoofingra 📁

**Hogyan működik:**
- Drag & drop VAGY kattintás a "Mappa Spoofing" szekcióra
- Automatikusan felismeri a képeket a mappában
- Előnézet grid mutatja az összes képet
- "Mind Spoofing" gomb egyszerre dolgozza fel
- ZIP letöltés az összes spoofolt képhez

**UI helye:** Editor oldal, jobb oldali panel

```html
<!-- Már benne van az editor_v2.html-ben -->
<div id="batchDropzone">...</div>
<div id="batchPreview">...</div>
<button onclick="processBatchSpoof()">🚀 Mind Spoofing</button>
<button onclick="downloadBatchZip()">📥 ZIP Letöltés</button>
```

---

### 2️⃣ SEO Optimalizálás + Score 📊

**Funkciók:**
- **Valós idejű SEO score** (0-100) - gauge megjelenítéssel
- **Automatikus elemzés** gépelés közben
- **AI optimalizálás** gomb - teljes szöveg SEO újraírása
- **Hashtag generálás** - releváns hashtag-ek hozzáadása
- **Emoji hozzáadás** - kategória-alapú emoji-k
- **Javaslatok panel** - konkrét tippek a javításhoz

**Metrikák:**
- Hashtag-ek száma (optimális: 2-5)
- Emoji-k száma (optimális: 1-4)
- Karakter szám (optimális: 80-280)
- Olvashatóság (szó/mondat)
- Kulcsszavak

**API végpontok (seo_api.py):**
```
POST /api/optimize-seo      → AI-alapú SEO optimalizálás
POST /api/generate-hashtags → Hashtag generálás
POST /api/add-emojis        → Emoji hozzáadás
POST /api/analyze-seo       → Részletes SEO elemzés
POST /api/batch-spoof       → Batch kép spoofing (ZIP)
```

---

### 3️⃣ Forrás Link az Editorban 🔗

**Megjelenés:** Header közepén, a cím alatt

**Működés:**
- Ha a felhasználó trendből/hírből nyit posztot, a forrás link automatikusan megjelenik
- Kék pill-szerű gomb "📰 Eredeti cikk megnyitása" szöveggel
- Kattintásra új ablakban nyílik meg
- Ha nincs forrás, rejtve marad

**Kód:**
```html
<div id="sourceLinkContainer" class="mt-1 hidden">
    <a href="#" id="sourceLink" target="_blank" 
       class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/20...">
        <svg>...</svg>
        <span id="sourceLinkText">Eredeti cikk megnyitása</span>
    </a>
</div>
```

**JavaScript:**
```javascript
function setSourceLink(url, title = null) {
    currentSourceUrl = url;
    const container = document.getElementById('sourceLinkContainer');
    const link = document.getElementById('sourceLink');
    
    if (url) {
        link.href = url;
        container.classList.remove('hidden');
    } else {
        container.classList.add('hidden');
    }
}
```

---

## 🔧 Integrációs Lépések

### 1. Editor frissítése

```bash
# Cseréld le a régi editor.html-t
cp editor_v2.html templates/editor.html
```

### 2. SEO API hozzáadása az app.py-hoz

```python
# app.py elején:
from seo_api import seo_api

# Flask app után:
app.register_blueprint(seo_api)
```

### 3. Dashboard frissítése

A `dashboard.html`-ben a stats grid után (kb. 177. sor) illeszd be a `dashboard_agent_section.html` tartalmát.

Vagy egyszerűbben:
```html
<!-- dashboard.html-ben a </main> előtt -->
{% include 'dashboard_agent_section.html' %}
```

### 4. Szükséges imports ellenőrzése

```python
# requirements.txt kiegészítés (ha még nincs):
jszip  # Frontend-en CDN-ről töltjük
```

---

## 📸 UI Preview

### SEO Panel
```
┌─────────────────────────────────────┐
│ 📊 SEO Elemzés        [🔄 Újra...]  │
├─────────────────────────────────────┤
│   ┌────────┐                        │
│   │   78   │  Kulcsszavak: AI, Tech │
│   │  /100  │  Hashtag-ek: 3         │
│   └────────┘  Emoji-k: 2            │
│              Olvashatóság: 12 szó   │
├─────────────────────────────────────┤
│ 💡 Javaslatok:                      │
│ • Adj hozzá még 1 hashtag-et        │
└─────────────────────────────────────┘
```

### Mappa Spoofing
```
┌─────────────────────────────────────┐
│ 📁 Mappa Spoofing           8 kép  │
├─────────────────────────────────────┤
│ ┌───┬───┬───┬───┐                  │
│ │ ✓ │ ✓ │ ✓ │ ⏳│  (thumbnail grid) │
│ ├───┼───┼───┼───┤                  │
│ │ ⏳│ ⏳│ ⏳│ ⏳│                  │
│ └───┴───┴───┴───┘                  │
├─────────────────────────────────────┤
│ Device: [🎲 Random        ▼]       │
│ [🚀 Mind Spoofing] [📥 ZIP Letöltés]│
│ ████████░░░░░░░░░░░  4 / 8         │
└─────────────────────────────────────┘
```

### Forrás Link (Header)
```
┌─────────────────────────────────────────────────────────┐
│ ← DASHBOARD    Editor Studio [PRO]         🪟 Új Fül   │
│               📰 Eredeti cikk megnyitása →             │
└─────────────────────────────────────────────────────────┘
```

---

## 🎁 Extra: Agent Kezelés a Dashboard-on

Az új Agent szekció tartalma:
- Online agent-ek száma (real-time)
- Várakozó task-ok
- Sikeres műveletek száma
- Sikerességi ráta (%)
- Agent lista (név, verzió, státusz)
- Task lista (filterezhető)
- Gyors műveletek (Poszt, Like, Komment, Újrapróbálás)
- API kulcs kezelés modal

---

## ✅ Ellenőrzőlista

- [ ] `editor_v2.html` → `templates/editor.html`
- [ ] `seo_api.py` → projekt root
- [ ] `app.py`-ban: `from seo_api import seo_api` + `app.register_blueprint(seo_api)`
- [ ] `dashboard.html`-be: Agent szekció beillesztése
- [ ] Tesztelés: SEO score működik?
- [ ] Tesztelés: Mappa feltöltés működik?
- [ ] Tesztelés: Forrás link megjelenik?
- [ ] Tesztelés: Agent kezelés működik?

---

## 🐛 Troubleshooting

**SEO nem működik:**
- Ellenőrizd, hogy a `seo_api.py` importálva van
- Ha nincs Google AI, fallback működik

**Mappa feltöltés nem működik:**
- Chrome/Edge kell (Firefox korlátozottan támogatja)
- `webkitdirectory` attribútum kell

**Forrás link nem jelenik meg:**
- A `selectTrend()` funkció hívja a `setSourceLink()`-et
- Ellenőrizd, hogy a trend-nek van-e `source_url` mezője

---

Kész! 🎉 Ha bármi kérdés, szólj!
