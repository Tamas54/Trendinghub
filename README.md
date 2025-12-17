# TrendMaster AI

Facebook post generator powered by AI, with trending topics collection, RAG-based style learning, and automatic publishing.

## Features

### Trend Collection
- **Google News RSS**: Trending topics from HU, GB, US regions
- **YouTube Trending**: Real-time trending videos
- **Super Trends**: Detects topics trending across multiple sources

### AI Content Generation
- **GPT-5 Mini**: Latest OpenAI model for post generation (500-800 char posts)
- **Google Gemini 3 Pro**: Alternative text generation
- **Nano Banana (Gemini 3 Pro Image)**: AI image generation with 2-step workflow
- **Veo 3.1**: AI video generation

### RAG Style Learning
- **ChromaDB** vector database (local, CPU-only)
- **Multilingual embeddings**: `paraphrase-multilingual-MiniLM-L12-v2` (Hungarian support)
- Upload influencer style samples
- Automatic chunking (500 char/chunk)
- Style context injection into post generation
- Active style indicator on dashboard

### Document to Post
- Upload documents (.docx, .pdf, .md, .txt)
- Automatic text extraction
- SEO score calculation (textstat)
- AI post generation from document content

### Media & Publishing
- **EXIF Spoofing**: Makes images appear as mobile device photos
- **Batch EXIF Processing**: Drag & drop folder upload with ZIP download
- **Scheduled Publishing**: Schedule posts for optimal times
- **Optimal Posting Time**: Suggests best times based on engagement data

### SaaS Features
- Multi-tenant user management
- Desktop Agent API for automated posting
- SEO optimization API
- PWA support (installable web app)

## Tech Stack

- **Backend**: Flask (Python 3.10+)
- **Frontend**: TailwindCSS, Vanilla JavaScript
- **AI**: OpenAI GPT-5, Google AI (Gemini 3, Nano Banana, Veo 3.1)
- **Vector DB**: ChromaDB with sentence-transformers
- **Database**: SQLite
- **Scheduler**: APScheduler

## Setup

1. Clone the repository
```bash
git clone https://github.com/Tamas54/Trendinghub.git
cd Trendinghub
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create `.env` file (see `.env.example`)
```env
# AI Providers
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_ai_key
AI_PROVIDER=google  # or openai

# Models
GEMINI_TEXT_MODEL=gemini-3-pro-preview
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
GEMINI_VIDEO_MODEL=veo-3.1-generate-preview

# YouTube API
YOUTUBE_API_KEY=your_youtube_api_key

# Flask
SECRET_KEY=your_secret_key
FLASK_DEBUG=True
PORT=5000
```

5. Run the application
```bash
python app.py
```

6. Open http://localhost:5000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trends` | GET | Get all trends |
| `/api/generate` | POST | Generate post from trend |
| `/api/generate-image` | POST | Generate image |
| `/api/rag/upload` | POST | Upload style samples |
| `/api/rag/status` | GET | Get RAG store status |
| `/api/doc/extract` | POST | Extract text from document |
| `/api/optimize-seo` | POST | SEO optimization |

## Performance (CPU)

| Operation | Time |
|-----------|------|
| RAG embedding | ~0.5s/chunk |
| RAG query | ~20ms |
| Model load | 3-5s (once) |
| Post generation | 2-5s (API) |
| Image generation | 5-15s (API) |

## Deployment

Configured for Railway deployment:
- `Procfile`: `web: python app.py`
- `railway.json`: Build & deploy config

## Project Structure

```
├── app.py              # Main Flask application
├── generator.py        # Post generation with GPT-5/Gemini
├── google_ai.py        # Google AI integration (Nano Banana)
├── rag_store.py        # ChromaDB RAG store
├── database.py         # SQLite database
├── database_saas.py    # SaaS multi-tenant tables
├── media_spoofer.py    # EXIF spoofing
├── templates/          # HTML templates
├── static/             # Static files (CSS, JS, manifest)
├── chroma_db/          # Vector database (gitignored)
└── agent/              # Desktop agent
```

## License

MIT
