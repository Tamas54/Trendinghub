# TrendMaster

Facebook post generator powered by AI, with trending topics collection and automatic publishing.

## Features

- **Trend Collection**: Collects trending topics from Google News (HU, GB, US) and YouTube
- **Super Trends**: Detects topics trending across multiple sources
- **AI Post Generation**: Generates engaging Facebook posts using OpenAI GPT or Google Gemini
- **AI Image Generation**: Creates images with DALL-E 3 or Google Imagen
- **AI Video Generation**: Creates short videos with Google Veo 3
- **EXIF Spoofing**: Modifies image metadata to appear as mobile device photos
- **Scheduled Publishing**: Schedule posts for optimal engagement times
- **Optimal Posting Time**: Suggests best times to post based on engagement data

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: TailwindCSS, Vanilla JavaScript
- **AI**: OpenAI API, Google AI (Gemini, Imagen, Veo)
- **Database**: SQLite
- **Scheduler**: APScheduler

## Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/trendmaster.git
cd trendmaster
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create `.env` file
```env
# AI Providers
OPENAI_API_KEY=your_openai_key
GOOGLE_AI_API_KEY=your_google_ai_key
AI_PROVIDER=google  # or openai

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

6. Open http://localhost:5000 in your browser

## Deployment

This app is configured for Railway deployment. See `Procfile` and `railway.toml` for configuration.

## License

MIT
