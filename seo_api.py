"""
TrendMaster SEO API Endpoints
SEO optimalizálás, hashtag és emoji generálás

Ezeket a végpontokat add hozzá az app.py-hoz!
"""

from flask import Blueprint, request, jsonify
import re
import os

# AI imports - használd ami elérhető
try:
    from google_ai import GoogleAIGenerator
    google_ai = GoogleAIGenerator()
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False


seo_api = Blueprint('seo_api', __name__, url_prefix='/api')


# ═══════════════════════════════════════════════════════════════════════════
# SEO OPTIMALIZÁLÁS
# ═══════════════════════════════════════════════════════════════════════════

@seo_api.route('/optimize-seo', methods=['POST'])
def optimize_seo():
    """
    AI-alapú SEO optimalizálás Facebook posztokhoz.
    
    POST body:
    {
        "text": "Eredeti szöveg..."
    }
    
    Response:
    {
        "success": true,
        "optimized_text": "Optimalizált szöveg...",
        "seo_score": 85,
        "improvements": ["Hashtag-ek hozzáadva", "Emoji-k optimalizálva"]
    }
    """
    data = request.get_json()
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        if AI_AVAILABLE:
            # AI optimalizálás
            prompt = f"""Optimalizáld ezt a Facebook posztot SEO szempontból:

EREDETI SZÖVEG:
{text}

KÖVETELMÉNYEK:
1. Tedd vonzóbbá és figyelemfelkeltőbbé
2. Adj hozzá 2-4 releváns hashtag-et a végére
3. Használj 1-3 megfelelő emoji-t
4. Tartsd meg az eredeti üzenetet
5. Optimális hossz: 100-250 karakter
6. Használj call-to-action-t ha releváns

FONTOS: Csak a optimalizált szöveget add vissza, semmi mást!"""

            optimized = google_ai.generate_text(prompt)
            
            return jsonify({
                'success': True,
                'optimized_text': optimized.strip(),
                'original_length': len(text),
                'optimized_length': len(optimized)
            })
        else:
            # Fallback: egyszerű optimalizálás AI nélkül
            optimized = simple_seo_optimize(text)
            return jsonify({
                'success': True,
                'optimized_text': optimized,
                'note': 'Simple optimization (AI not available)'
            })
            
    except Exception as e:
        print(f"❌ SEO optimization error: {e}")
        return jsonify({'error': str(e)}), 500


def simple_seo_optimize(text):
    """Egyszerű SEO optimalizálás AI nélkül"""
    # Ha nincs emoji az elején, adj hozzá
    if not re.match(r'^[\U0001F300-\U0001F9FF]', text):
        emojis = ['🔥', '⭐', '💡', '✨', '🚀', '📢', '💪', '🎯']
        import random
        text = random.choice(emojis) + ' ' + text
    
    # Ha nincs hashtag, adj hozzá általánosat
    if '#' not in text:
        text = text.strip() + '\n\n#trending #viral #foryou'
    
    return text


# ═══════════════════════════════════════════════════════════════════════════
# HASHTAG GENERÁLÁS
# ═══════════════════════════════════════════════════════════════════════════

@seo_api.route('/generate-hashtags', methods=['POST'])
def generate_hashtags():
    """
    Releváns hashtag-ek generálása a szöveghez.
    
    POST body:
    {
        "text": "Poszt szövege..."
    }
    
    Response:
    {
        "success": true,
        "hashtags": ["#trend", "#viral", "#news"]
    }
    """
    data = request.get_json()
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        if AI_AVAILABLE:
            prompt = f"""Generálj 5-7 releváns magyar és angol hashtag-et ehhez a Facebook poszthoz:

POSZT:
{text}

SZABÁLYOK:
1. Mix magyar és angol hashtag-ek
2. Használj trending hashtag-eket is (#foryou, #viral, #trending)
3. Legyenek specifikusak a tartalomra
4. Ne használj túl hosszú hashtag-eket

Formátum: csak a hashtag-ek, szóközzel elválasztva, semmi más!"""

            result = google_ai.generate_text(prompt)
            hashtags = [tag.strip() for tag in result.split() if tag.startswith('#')]
            
            return jsonify({
                'success': True,
                'hashtags': hashtags[:7]
            })
        else:
            # Fallback hashtag-ek
            hashtags = extract_keywords_as_hashtags(text)
            return jsonify({
                'success': True,
                'hashtags': hashtags
            })
            
    except Exception as e:
        print(f"❌ Hashtag generation error: {e}")
        return jsonify({'error': str(e)}), 500


def extract_keywords_as_hashtags(text):
    """Kulcsszavak kinyerése és hashtag-gé alakítása"""
    # Nagybetűs szavak és főnevek keresése
    words = re.findall(r'\b[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű]+\b', text)
    unique_words = list(set(words))[:3]
    
    hashtags = [f'#{word.lower()}' for word in unique_words]
    hashtags.extend(['#trending', '#viral', '#foryou'])
    
    return hashtags


# ═══════════════════════════════════════════════════════════════════════════
# EMOJI HOZZÁADÁS
# ═══════════════════════════════════════════════════════════════════════════

@seo_api.route('/add-emojis', methods=['POST'])
def add_emojis():
    """
    Emoji-k intelligens hozzáadása a szöveghez.
    
    POST body:
    {
        "text": "Poszt szövege..."
    }
    
    Response:
    {
        "success": true,
        "text_with_emojis": "🔥 Poszt szövege... ✨"
    }
    """
    data = request.get_json()
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        if AI_AVAILABLE:
            prompt = f"""Add hozzá a megfelelő emoji-kat ehhez a Facebook poszthoz:

EREDETI SZÖVEG:
{text}

SZABÁLYOK:
1. Adj 1-2 emoji-t az elejére
2. Adj 1-2 emoji-t a végére vagy a mondatok közé
3. Ne vidd túlzásba (max 4 emoji összesen)
4. Az emoji-k legyenek relevánsak a tartalomhoz

FONTOS: Csak a szöveget add vissza az emoji-kkal, semmi mást!"""

            result = google_ai.generate_text(prompt)
            
            return jsonify({
                'success': True,
                'text_with_emojis': result.strip()
            })
        else:
            # Fallback emoji hozzáadás
            enhanced = add_simple_emojis(text)
            return jsonify({
                'success': True,
                'text_with_emojis': enhanced
            })
            
    except Exception as e:
        print(f"❌ Emoji addition error: {e}")
        return jsonify({'error': str(e)}), 500


def add_simple_emojis(text):
    """Egyszerű emoji hozzáadás kategória alapján"""
    import random
    
    # Kategória detektálás kulcsszavak alapján
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['hír', 'news', 'bejelent', 'közlemény']):
        start_emoji = random.choice(['📢', '📰', '🗞️', '⚡'])
        end_emoji = random.choice(['👀', '🔥', '💡'])
    elif any(word in text_lower for word in ['sport', 'meccs', 'győz', 'bajnok']):
        start_emoji = random.choice(['⚽', '🏆', '🎯', '💪'])
        end_emoji = random.choice(['🔥', '👏', '🙌'])
    elif any(word in text_lower for word in ['tech', 'ai', 'robot', 'digital']):
        start_emoji = random.choice(['🤖', '💻', '🚀', '⚡'])
        end_emoji = random.choice(['✨', '🔮', '💡'])
    else:
        start_emoji = random.choice(['🔥', '⭐', '✨', '💡'])
        end_emoji = random.choice(['👇', '💬', '🙌'])
    
    return f"{start_emoji} {text.strip()} {end_emoji}"


# ═══════════════════════════════════════════════════════════════════════════
# SEO SCORE SZÁMÍTÁS (részletes)
# ═══════════════════════════════════════════════════════════════════════════

@seo_api.route('/analyze-seo', methods=['POST'])
def analyze_seo():
    """
    Részletes SEO elemzés.
    
    POST body:
    {
        "text": "Poszt szövege..."
    }
    
    Response:
    {
        "success": true,
        "score": 75,
        "breakdown": {
            "hashtags": {"score": 15, "count": 3, "max": 20},
            "emojis": {"score": 10, "count": 2, "max": 15},
            "length": {"score": 20, "chars": 150, "max": 25},
            "readability": {"score": 15, "avg_words": 12, "max": 20},
            "keywords": {"score": 15, "found": ["AI", "tech"], "max": 20}
        },
        "suggestions": [
            "Adj hozzá még 1-2 hashtag-et",
            "A szöveg optimális hosszúságú"
        ]
    }
    """
    data = request.get_json()
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'Text is required'}), 400
    
    # Metrikák számítása
    hashtag_count = len(re.findall(r'#\w+', text))
    emoji_pattern = r'[\U0001F300-\U0001F9FF]|[\U00002600-\U000026FF]|[\U00002700-\U000027BF]'
    emoji_count = len(re.findall(emoji_pattern, text))
    char_count = len(text)
    word_count = len(text.split())
    sentence_count = len(re.split(r'[.!?]+', text))
    avg_words_per_sentence = word_count / max(sentence_count, 1)
    
    # Kulcsszavak (nagybetűs szavak)
    keywords = list(set(re.findall(r'\b[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű]+\b', text)))[:5]
    
    # Score számítás
    breakdown = {
        'hashtags': {
            'score': min(20, hashtag_count * 5) if hashtag_count <= 5 else max(0, 20 - (hashtag_count - 5) * 3),
            'count': hashtag_count,
            'max': 20
        },
        'emojis': {
            'score': min(15, emoji_count * 5) if emoji_count <= 4 else max(0, 15 - (emoji_count - 4) * 3),
            'count': emoji_count,
            'max': 15
        },
        'length': {
            'score': 25 if 80 <= char_count <= 280 else (15 if 50 <= char_count <= 400 else 5),
            'chars': char_count,
            'max': 25
        },
        'readability': {
            'score': 20 if 8 <= avg_words_per_sentence <= 18 else 10,
            'avg_words': round(avg_words_per_sentence, 1),
            'max': 20
        },
        'keywords': {
            'score': min(20, len(keywords) * 4),
            'found': keywords,
            'max': 20
        }
    }
    
    total_score = sum(item['score'] for item in breakdown.values())
    
    # Javaslatok
    suggestions = []
    if hashtag_count == 0:
        suggestions.append('Adj hozzá 2-4 releváns hashtag-et')
    elif hashtag_count > 5:
        suggestions.append('Csökkentsd a hashtag-ek számát (max 5)')
    
    if emoji_count == 0:
        suggestions.append('Használj 1-2 emoji-t a figyelemfelkeltéshez')
    elif emoji_count > 4:
        suggestions.append('Kevesebb emoji javasolt')
    
    if char_count < 50:
        suggestions.append('A szöveg túl rövid, bővítsd ki')
    elif char_count > 400:
        suggestions.append('A szöveg túl hosszú, rövidítsd')
    
    if len(keywords) < 2:
        suggestions.append('Használj több kulcsszót')
    
    if not suggestions:
        suggestions.append('Kiváló! A poszt SEO szempontból optimális.')
    
    return jsonify({
        'success': True,
        'score': total_score,
        'max_score': 100,
        'breakdown': breakdown,
        'suggestions': suggestions
    })


# ═══════════════════════════════════════════════════════════════════════════
# BATCH IMAGE SPOOF (ZIP)
# ═══════════════════════════════════════════════════════════════════════════

@seo_api.route('/batch-spoof', methods=['POST'])
def batch_spoof():
    """
    Több kép egyszerre spoofing-ja.
    
    Multipart form-data:
    - images[]: több képfájl
    - device: eszköz típus (random, iphone15, stb.)
    
    Response: ZIP fájl a spoofolt képekkel
    """
    if 'images[]' not in request.files:
        return jsonify({'error': 'No images provided'}), 400
    
    files = request.files.getlist('images[]')
    device = request.form.get('device', 'random')
    
    if not files:
        return jsonify({'error': 'No valid images'}), 400
    
    try:
        import zipfile
        import io
        import tempfile
        from media_spoofer import MediaSpoofer
        
        spoofer = MediaSpoofer()
        
        # ZIP készítése memóriában
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, file in enumerate(files):
                if not file.filename:
                    continue
                
                # Temp fájl a spoofinghoz
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    file.save(tmp.name)
                    
                    # Spoof alkalmazása
                    current_device = device if device != 'random' else 'random'
                    success = spoofer.spoof_image(tmp.name, device_key=current_device)
                    
                    if success:
                        # ZIP-be rakás
                        with open(tmp.name, 'rb') as spoofed:
                            zip_file.writestr(
                                f'spoofed_{i+1}_{file.filename}',
                                spoofed.read()
                            )
                    
                    # Temp törlése
                    os.unlink(tmp.name)
        
        zip_buffer.seek(0)
        
        from flask import send_file
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'spoofed_batch_{len(files)}.zip'
        )
        
    except Exception as e:
        print(f"❌ Batch spoof error: {e}")
        return jsonify({'error': str(e)}), 500
