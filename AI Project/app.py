from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
import requests
import base64
import subprocess
import tempfile
import wave
import json
from dotenv import load_dotenv
import time
from deep_translator import GoogleTranslator
from groq import Groq

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'voxai-secret-key-2024')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


def env_value(name, default=''):
    value = os.environ.get(name)
    if value:
        return value.strip().strip('"').strip("'")
    try:
        lines = open('.env', encoding='utf-8').read().splitlines()
    except OSError:
        return default
    for index, line in enumerate(lines):
        if not line.startswith(f'{name}='):
            continue
        raw = line.split('=', 1)[1].strip()
        if raw.startswith('"') and not raw.endswith('"'):
            parts = [raw.lstrip('"')]
            for extra in lines[index + 1:]:
                stripped = extra.strip()
                if re.match(r'^[A-Z0-9_]+\s*=', stripped):
                    break
                if not stripped or stripped.startswith('#'):
                    continue
                if stripped.endswith('"'):
                    parts.append(stripped.rstrip('"'))
                    break
                parts.append(stripped)
            return ''.join(parts).strip()
        return raw.strip().strip('"').strip("'")
    return default

# ── API Keys ──────────────────────────────────────────────────────────────────
GROQ_API_KEY       = env_value('GROQ_API_KEY')
ASSEMBLYAI_API_KEY = env_value('ASSEMBLYAI_API_KEY')
OPENAI_API_KEY     = env_value('OPENAI_API_KEY')

# ── Groq AI config (same approach as Yogitha — direct HTTP, no extra SDK) ────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"   # same model Yogitha uses — more powerful
OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_STT_MODEL = os.environ.get('OPENAI_STT_MODEL', 'gpt-4o-mini-transcribe')
OPENAI_TTS_MODEL = os.environ.get('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
OPENAI_TTS_VOICE = os.environ.get('OPENAI_TTS_VOICE', 'coral')
OPENAI_TTS_FALLBACK_MODELS = [
    model for model in (OPENAI_TTS_MODEL, 'tts-1', 'tts-1-hd')
    if model
]

if GROQ_API_KEY:
    try:
        groq_client  = Groq(api_key=GROQ_API_KEY)
        AI_AVAILABLE = True
        print(f"Groq AI ready - model: {GROQ_MODEL}")
    except Exception as e:
        print(f"Groq config error: {e}")
else:
    print("GROQ_API_KEY not set in .env")


def ask_groq(system_prompt, user_message, max_tokens=1024):
    """
    Call Groq API directly via HTTP — same pattern Yogitha uses in her server.js.
    Returns the AI reply string, or raises an exception on failure.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
    data = resp.json()
    if not resp.ok:
        raise Exception(f"Groq API error {resp.status_code}: {data}")
    return data["choices"][0]["message"]["content"].strip()


def clean_ai_reply(text):
    """Return plain assistant text without markdown bullets or emphasis markers."""
    if not text:
        return text
    cleaned = str(text).replace('**', '').replace('__', '')
    cleaned = re.sub(r'(?m)^\s*[*-]\s+', '', cleaned)
    cleaned = re.sub(r'(?m)^\s*\*\s*', '', cleaned)
    cleaned = re.sub(r'(?<!\w)\*(?!\w)', '', cleaned)
    return cleaned.strip()


def normalize_url(raw_url):
    """Build a browser-safe URL from a spoken website target."""
    if not raw_url:
        return None
    value = raw_url.strip().lower()
    value = re.sub(r'^(website|site)\s+', '', value).strip()
    value = re.sub(r'\s+(website|site|page|link)$', '', value).strip()
    alias = WEBSITE_ALIASES.get(value)
    if alias:
        return alias
    value = value.replace(' dot ', '.').replace(' slash ', '/')
    value = re.sub(r'\s+', '', value)
    value = value.strip('.,!?')
    if not value:
        return None
    if value.startswith(('http://', 'https://')):
        return value
    if '.' not in value:
        value = f"{value}.com"
    return f"https://{value}"


def detect_website_open_request(message):
    """Detect natural website-opening requests without routing by app keywords."""
    text = (message or '').strip()
    if not text:
        return None
    normalized_text = re.sub(r'\s+', ' ', text.lower()).strip(' .?!')

    direct_url = re.search(
        r'(https?://[^\s]+|(?:www\.)?[a-z0-9-]+(?:\.[a-z]{2,})(?:/[^\s]*)?)',
        text,
        flags=re.IGNORECASE,
    )
    if direct_url:
        return normalize_url(direct_url.group(1))

    for name in sorted(WEBSITE_ALIASES, key=len, reverse=True):
        if re.search(rf'\b{re.escape(name)}\b', normalized_text) and re.search(
            r'\b(open|launch|visit|go to|take me to|show me|website|site|link)\b',
            normalized_text,
        ):
            return WEBSITE_ALIASES[name]

    command = re.search(
        r'\b(?:open|launch|visit|go to|take me to|show me)\s+([a-z0-9 .-]+?)(?:\s+(?:website|site|page|link))?\s*$',
        text,
        flags=re.IGNORECASE,
    )
    if command:
        return normalize_url(command.group(1))

    link_request = re.search(
        r'\b(?:website|site|page|link)\s+(?:for|of|to)?\s*([a-z0-9 .-]+)$|'
        r'\b([a-z0-9 .-]+?)\s+(?:website|site|page|link)\s*$',
        text,
        flags=re.IGNORECASE,
    )
    if link_request:
        target = (link_request.group(1) or link_request.group(2) or '').strip()
        if target:
            alias = WEBSITE_ALIASES.get(target.lower())
            if alias:
                return alias
            if ' ' in target and '.' not in target:
                return 'https://www.google.com/search?q=' + requests.utils.quote(f'{target} official website')
            return normalize_url(target)
    return None


def normalize_language(language):
    language = (language or 'en').strip().lower()
    return language if language in LANG_CODES else 'en'


def detect_language_from_text(text, fallback='en'):
    """Lightweight script-based language detection for voice text."""
    value = text or ''
    if re.search(r'[\u0B80-\u0BFF]', value):
        return 'ta'
    if re.search(r'[\u0C00-\u0C7F]', value):
        return 'te'
    if re.search(r'[\u0C80-\u0CFF]', value):
        return 'kn'
    if re.search(r'[\u0D00-\u0D7F]', value):
        return 'ml'
    if re.search(r'[\u0980-\u09FF]', value):
        return 'bn'
    if re.search(r'[\u0A80-\u0AFF]', value):
        return 'gu'
    if re.search(r'[\u0900-\u097F]', value):
        return 'mr' if fallback == 'mr' else 'hi'
    return normalize_language(fallback)


def is_stop_conversation_request(text):
    value = (text or '').strip().lower()
    if not value:
        return False
    stop_phrases = [
        'stop', 'stop conversation', 'stop the conversation', 'stop listening',
        'end conversation', 'end the conversation', 'cancel conversation',
        'बस करो', 'बंद करो', 'रुक जाओ', 'संवाद बंद करो',
        'நிறுத்து', 'உரையாடலை நிறுத்து',
        'ನಿಲ್ಲಿಸು', 'ಸಂಭಾಷಣೆ ನಿಲ್ಲಿಸು',
        'ఆపు', 'సంభాషణ ఆపు',
        'നിർത്തുക', 'സംഭാഷണം നിർത്തുക',
        'थांबा', 'संभाषण बंद करा',
    ]
    return any(phrase in value for phrase in stop_phrases)


# ── Database config ───────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     os.environ.get('MYSQL_HOST',     'localhost'),
    'user':     os.environ.get('MYSQL_USER',     'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DB',       'voxai'),
}

# ── Language maps ─────────────────────────────────────────────────────────────
LANG_CODES = {
    'en': 'en', 'hi': 'hi', 'ta': 'ta', 'kn': 'kn',
    'ml': 'ml', 'te': 'te', 'mr': 'mr', 'bn': 'bn', 'gu': 'gu',
}

LANGUAGE_NAMES = {
    'en': 'English', 'hi': 'Hindi',  'ta': 'Tamil',
    'kn': 'Kannada', 'ml': 'Malayalam', 'te': 'Telugu',
    'mr': 'Marathi', 'bn': 'Bengali',   'gu': 'Gujarati',
}

WEBSITE_ALIASES = {
    'google maps': 'https://maps.google.com',
    'google map': 'https://maps.google.com',
    'gmail': 'https://mail.google.com',
    'google mail': 'https://mail.google.com',
    'youtube': 'https://www.youtube.com',
    'facebook': 'https://www.facebook.com',
    'instagram': 'https://www.instagram.com',
    'twitter': 'https://www.twitter.com',
    'x': 'https://www.x.com',
    'whatsapp web': 'https://web.whatsapp.com',
    'linkedin': 'https://www.linkedin.com',
    'github': 'https://github.com',
    'stack overflow': 'https://stackoverflow.com',
    'amazon': 'https://www.amazon.in',
    'flipkart': 'https://www.flipkart.com',
    'myntra': 'https://www.myntra.com',
    'zomato': 'https://www.zomato.com',
    'swiggy': 'https://www.swiggy.com',
    'irctc': 'https://www.irctc.co.in',
    'bookmyshow': 'https://in.bookmyshow.com',
    'redbus': 'https://www.redbus.in',
    'ola': 'https://book.olacabs.com',
    'uber': 'https://www.uber.com/in/en/ride/',
}

# ── Booking services ──────────────────────────────────────────────────────────
BOOKING_SERVICES = {
    'movie': {
        'label': 'BookMyShow',
        'url': 'https://in.bookmyshow.com',
        'keywords': [
            'movie', 'movies', 'cinema', 'film', 'bookmyshow',
            'मूवी', 'फिल्म', 'सिनेमा', 'படம்', 'சினிமா',
            'ಸಿನಿಮಾ', 'ಚಲನಚಿತ್ರ', 'മൂവി', 'സിനിമ', 'సినిమా',
        ],
    },
    'train': {
        'label': 'IRCTC',
        'url': 'https://www.irctc.co.in/nget/train-search',
        'keywords': [
            'train', 'railway', 'rail', 'irctc',
            'ट्रेन', 'रेल', 'ரயில்', 'ரெயில்',
            'ರೈಲು', 'ಟ್ರೈನ್', 'ട്രെയിൻ', 'ರೈಲ್ವೆ', 'రైలు', 'ట్రైన్',
        ],
    },
    'flight': {
        'label': 'MakeMyTrip',
        'url': 'https://www.makemytrip.com/flights/',
        'keywords': [
            'flight', 'aeroplane', 'airplane', 'plane', 'air ticket',
            'makemytrip', 'make my trip',
            'फ्लाइट', 'विमान', 'விமானம்', 'ஃப்ளைட்',
            'ವಿಮಾನ', 'ಫ್ಲೈಟ್', 'വിമാനം', 'ఫ్లైట్', 'విమానం',
        ],
    },
    'bus': {
        'label': 'redBus',
        'url': 'https://www.redbus.in',
        'keywords': [
            'bus', 'redbus', 'bus ticket',
            'बस', 'பஸ்', 'ಬಸ್', 'ബസ്', 'బస్', 'బస్సు',
        ],
    },
    'cab': {
        'label': 'Uber',
        'url': 'https://www.uber.com/in/en/ride/',
        'keywords': [
            'cab', 'car', 'taxi', 'uber', 'ride',
            'कैब', 'कार', 'टैक्सी', 'கார்', 'கேப்', 'டாக்ஸி',
            'ಕ್ಯಾಬ್', 'ಕಾರ್', 'ಟ್ಯಾಕ್ಸಿ', 'കാർ', 'കാബ്', 'టాక్సీ', 'కారు', 'క్యాబ్',
        ],
    },
    'auto': {
        'label': 'Ola',
        'url': 'https://book.olacabs.com',
        'keywords': [
            'auto', 'rickshaw', 'ola',
            'ऑटो', 'ஆட்டோ', 'ಆಟೋ', 'ഓട്ടോ', 'ఆటో',
        ],
    },
}

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None


def query(sql, params=(), fetchone=False, fetchall=False, lastrowid=False):
    conn = get_db()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if fetchone:
            result = cur.fetchone()
        elif fetchall:
            result = cur.fetchall()
        elif lastrowid:
            conn.commit()
            result = cur.lastrowid
        else:
            conn.commit()
            result = True
        cur.close()
        conn.close()
        return result
    except Error as e:
        print(f"Query error: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None


def init_db():
    conn = get_db()
    if not conn:
        print("Cannot connect to database. Check DB_CONFIG in .env")
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                phone VARCHAR(20),
                password VARCHAR(255) NOT NULL,
                location VARCHAR(100),
                language VARCHAR(10) DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                preview VARCHAR(100),
                language VARCHAR(10) DEFAULT 'en',
                conversation_type VARCHAR(20) DEFAULT 'chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audio_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                filename VARCHAR(255),
                language VARCHAR(10) DEFAULT 'en',
                transcript TEXT NOT NULL,
                original_text TEXT,
                provider VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conversation_id INT NOT NULL,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='conversations'
              AND COLUMN_NAME='conversation_type'
        """, (DB_CONFIG['database'],))
        has_type = cur.fetchone()[0]
        if not has_type:
            cur.execute("""
                ALTER TABLE conversations
                ADD COLUMN conversation_type VARCHAR(20) DEFAULT 'chat' AFTER language
            """)
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'
              AND COLUMN_NAME='language'
        """, (DB_CONFIG['database'],))
        has_user_language = cur.fetchone()[0]
        if not has_user_language:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN language VARCHAR(10) DEFAULT 'en' AFTER location
            """)
        cur.execute("""
            UPDATE conversations
            SET conversation_type='chat'
            WHERE conversation_type IS NULL OR conversation_type=''
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database tables ready")
    except Error as e:
        print(f"DB init error: {e}")


# ── Translation helpers ───────────────────────────────────────────────────────
def translate_text_safe(text, target_language):
    target_code = LANG_CODES.get(target_language, 'en')
    if not text or target_code == 'en':
        return text
    try:
        return GoogleTranslator(source='auto', target=target_code).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text


OFFLINE_REPLIES = {
    'en': {
        'greeting': "Hi! I'm VoxAI. I can help with basic offline chat, website opening, and booking shortcuts.",
        'help': "I am running in offline mode. I can answer simple questions, open saved website shortcuts, and help you navigate the app.",
        'thanks': "You're welcome.",
        'fallback': "I am in offline mode right now, so I cannot use the cloud AI. I can still help with basic commands and website opening.",
    },
    'hi': {
        'greeting': 'नमस्ते! मैं VoxAI हूं। मैं ऑफलाइन बेसिक चैट और वेबसाइट खोलने में मदद कर सकता हूं।',
        'help': 'मैं अभी ऑफलाइन मोड में हूं। मैं साधारण सवालों, वेबसाइट खोलने और ऐप नेविगेशन में मदद कर सकता हूं।',
        'thanks': 'आपका स्वागत है।',
        'fallback': 'मैं अभी ऑफलाइन मोड में हूं, इसलिए क्लाउड AI का उपयोग नहीं कर सकता। फिर भी मैं बेसिक कमांड और वेबसाइट खोलने में मदद कर सकता हूं।',
    },
    'ta': {
        'greeting': 'வணக்கம்! நான் VoxAI. ஆஃப்லைனில் அடிப்படை உரையாடல் மற்றும் வலைத்தளங்களைத் திறக்க உதவுவேன்.',
        'help': 'நான் இப்போது ஆஃப்லைன் முறையில் இருக்கிறேன். எளிய கேள்விகள், வலைத்தள திறப்பு, மற்றும் பயன்பாட்டு வழிசெலுத்தலில் உதவுவேன்.',
        'thanks': 'நன்றி.',
        'fallback': 'நான் இப்போது ஆஃப்லைன் முறையில் இருக்கிறேன், அதனால் கிளவுட் AI பயன்படுத்த முடியாது. அடிப்படை கட்டளைகள் மற்றும் வலைத்தள திறப்பில் உதவ முடியும்.',
    },
    'kn': {
        'greeting': 'ನಮಸ್ಕಾರ! ನಾನು VoxAI. ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ಮೂಲ ಚಾಟ್ ಮತ್ತು ವೆಬ್‌ಸೈಟ್ ತೆರೆಯಲು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.',
        'help': 'ನಾನು ಈಗ ಆಫ್‌ಲೈನ್ ಮೋಡ್‌ನಲ್ಲಿ ಇದ್ದೇನೆ. ಸರಳ ಪ್ರಶ್ನೆಗಳು, ವೆಬ್‌ಸೈಟ್ ತೆರೆಯುವುದು ಮತ್ತು ಆಪ್ ನ್ಯಾವಿಗೇಷನ್‌ನಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಹುದು.',
        'thanks': 'ಧನ್ಯವಾದಗಳು.',
        'fallback': 'ನಾನು ಈಗ ಆಫ್‌ಲೈನ್ ಮೋಡ್‌ನಲ್ಲಿ ಇದ್ದೇನೆ, ಆದ್ದರಿಂದ ಕ್ಲೌಡ್ AI ಬಳಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ಆದರೂ ಮೂಲ ಕಮಾಂಡ್‌ಗಳು ಮತ್ತು ವೆಬ್‌ಸೈಟ್ ತೆರೆಯಲು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.',
    },
    'te': {
        'greeting': 'నమస్తే! నేను VoxAI. ఆఫ్‌లైన్‌లో ప్రాథమిక చాట్ మరియు వెబ్‌సైట్‌లు తెరవడంలో సహాయం చేస్తాను.',
        'help': 'నేను ఇప్పుడు ఆఫ్‌లైన్ మోడ్‌లో ఉన్నాను. సాధారణ ప్రశ్నలు, వెబ్‌సైట్ తెరవడం మరియు యాప్ నావిగేషన్‌లో సహాయం చేయగలను.',
        'thanks': 'ధన్యవాదాలు.',
        'fallback': 'నేను ఇప్పుడు ఆఫ్‌లైన్ మోడ్‌లో ఉన్నాను, కాబట్టి క్లౌడ్ AI ఉపయోగించలేను. అయినా ప్రాథమిక కమాండ్లు మరియు వెబ్‌సైట్ తెరవడంలో సహాయం చేస్తాను.',
    },
    'ml': {
        'greeting': 'നമസ്കാരം! ഞാൻ VoxAI. ഓഫ്ലൈനിൽ അടിസ്ഥാന ചാറ്റിലും വെബ്സൈറ്റ് തുറക്കുന്നതിലും സഹായിക്കും.',
        'help': 'ഞാൻ ഇപ്പോൾ ഓഫ്ലൈൻ മോഡിലാണ്. ലളിതമായ ചോദ്യങ്ങൾക്കും വെബ്സൈറ്റ് തുറക്കാനും ആപ്പ് നാവിഗേഷനും സഹായിക്കാം.',
        'thanks': 'നന്ദി.',
        'fallback': 'ഞാൻ ഇപ്പോൾ ഓഫ്ലൈൻ മോഡിലാണ്, അതിനാൽ ക്ലൗഡ് AI ഉപയോഗിക്കാൻ കഴിയില്ല. അടിസ്ഥാന കമാൻഡുകളും വെബ്സൈറ്റ് തുറക്കലും സഹായിക്കാം.',
    },
    'mr': {
        'greeting': 'नमस्कार! मी VoxAI आहे. ऑफलाइनमध्ये बेसिक चॅट आणि वेबसाइट उघडण्यात मदत करू शकतो.',
        'help': 'मी सध्या ऑफलाइन मोडमध्ये आहे. साधे प्रश्न, वेबसाइट उघडणे आणि अॅप नेव्हिगेशनमध्ये मदत करू शकतो.',
        'thanks': 'धन्यवाद.',
        'fallback': 'मी सध्या ऑफलाइन मोडमध्ये आहे, त्यामुळे क्लाउड AI वापरू शकत नाही. तरीही बेसिक कमांड आणि वेबसाइट उघडण्यात मदत करू शकतो.',
    },
}


def offline_reply(message, language):
    lang = language if language in OFFLINE_REPLIES else 'en'
    text = (message or '').strip().lower()
    replies = OFFLINE_REPLIES[lang]
    if any(word in text for word in ('hi', 'hello', 'hey', 'ನಮಸ್ಕಾರ', 'नमस्ते', 'வணக்கம்', 'నమస్తే', 'നമസ്കാരം')):
        return replies['greeting']
    if any(word in text for word in ('help', 'what can you do', 'ಸಹಾಯ', 'मदद', 'உதவி', 'సహాయం', 'സഹായം')):
        return replies['help']
    if any(word in text for word in ('thank', 'thanks', 'ಧನ್ಯವಾದ', 'शुक्रिया', 'நன்றி', 'ధన్యవాదాలు', 'നന്ദി')):
        return replies['thanks']
    return replies['fallback']


def offline_stt_windows(audio_data, filename):
    """Use Windows built-in offline speech recognition for WAV files."""
    ext = os.path.splitext(filename or '')[1].lower()
    if ext != '.wav':
        raise ValueError('Offline audio-to-text currently supports WAV files only. Please upload a WAV file.')

    script_path = os.path.join(app.root_path, 'scripts', 'offline_stt_windows.ps1')
    if not os.path.exists(script_path):
        raise RuntimeError('Offline speech script is missing.')

    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
        temp_audio.write(audio_data)
        temp_path = temp_audio.name

    try:
        result = subprocess.run(
            [
                'powershell',
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                script_path,
                '-Path',
                temp_path,
                '-Culture',
                'en-US',
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=140,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or 'Offline transcription failed').strip())
        transcript = (result.stdout or '').strip()
        if not transcript:
            raise RuntimeError('No speech detected in the WAV file.')
        return transcript
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def offline_stt_vosk(audio_data, filename):
    """Use a bundled Vosk model for offline English WAV transcription."""
    ext = os.path.splitext(filename or '')[1].lower()
    if ext != '.wav':
        raise ValueError('Vosk offline audio-to-text needs a WAV file.')

    model_path = os.path.join(app.root_path, 'models', 'vosk-model-small-en-us-0.15')
    if not os.path.isdir(model_path):
        raise RuntimeError('Vosk offline model is missing.')

    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
        temp_audio.write(audio_data)
        temp_path = temp_audio.name

    try:
        from vosk import KaldiRecognizer, Model, SetLogLevel
        SetLogLevel(-1)
        with wave.open(temp_path, 'rb') as wav_file:
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise RuntimeError('Offline WAV must be mono 16-bit PCM.')
            recognizer = KaldiRecognizer(Model(model_path), wav_file.getframerate())
            parts = []
            while True:
                data = wav_file.readframes(4000)
                if not data:
                    break
                if recognizer.AcceptWaveform(data):
                    text = json.loads(recognizer.Result()).get('text', '').strip()
                    if text:
                        parts.append(text)
            final_text = json.loads(recognizer.FinalResult()).get('text', '').strip()
            if final_text:
                parts.append(final_text)
        transcript = ' '.join(parts).strip()
        if not transcript:
            raise RuntimeError('No speech detected by Vosk.')
        return transcript
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def translate_audio_text(text, target_language):
    target_code = LANG_CODES.get(target_language, 'en')
    if not text:
        return text
    try:
        return GoogleTranslator(source='auto', target=target_code).translate(text)
    except Exception as e:
        print(f"Audio translation error: {e}")
        if target_code == 'en' and GROQ_API_KEY:
            try:
                return clean_ai_reply(ask_groq(
                    "Translate the user's text to English. Return only the translation.",
                    text,
                    max_tokens=300,
                ))
            except Exception as ge:
                print(f"Groq translation fallback error: {ge}")
        return text


def transcribe_audio_openai(audio_data, filename, mimetype, target_language):
    """Use OpenAI's newer transcription model for better STT accuracy when possible."""
    if not OPENAI_API_KEY:
        raise RuntimeError('OPENAI_API_KEY is not configured')
    data = {
        'model': OPENAI_STT_MODEL,
        'response_format': 'json',
        'prompt': (
            'Transcribe the speech exactly. Do not invent names, people, or places. '
            'If a word is unclear, use [inaudible].'
        ),
    }
    if target_language == 'en':
        data['language'] = 'en'
    resp = requests.post(
        OPENAI_STT_URL,
        headers={'Authorization': f'Bearer {OPENAI_API_KEY}'},
        files={'file': (filename, audio_data, mimetype or 'application/octet-stream')},
        data=data,
        timeout=60,
    )
    if resp.status_code != 200:
        try:
            detail = resp.json().get('error', {}).get('message', '')
        except Exception:
            detail = resp.text[:240]
        raise RuntimeError(f'OpenAI transcription failed: {detail or resp.status_code}')
    return (resp.json().get('text') or '').strip()


def transcribe_audio_groq(audio_data, filename, mimetype, target_language):
    """Use Groq Whisper transcription. Always transcribe first; translation happens after."""
    if not GROQ_API_KEY:
        raise RuntimeError('GROQ_API_KEY is not configured')
    data = {
        'model': 'whisper-large-v3',
        'response_format': 'json',
        'temperature': '0',
        'prompt': (
            'Exact transcription only. Do not invent names, people, or places. '
            'If unclear, write [inaudible].'
        ),
    }
    if target_language == 'en':
        data['language'] = 'en'
    resp = requests.post(
        'https://api.groq.com/openai/v1/audio/transcriptions',
        headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
        files={'file': (filename, audio_data, mimetype or 'audio/ogg')},
        data=data,
        timeout=60,
    )
    if resp.status_code != 200:
        try:
            detail = resp.json().get('error', {}).get('message', '')
        except Exception:
            detail = resp.text[:240]
        raise RuntimeError(f'Groq Whisper returned {resp.status_code}: {detail}')
    return (resp.json().get('text') or '').strip()


def english_for_intent(text):
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return f"{text} {translated}"
    except Exception:
        return text


# ── Booking detection ─────────────────────────────────────────────────────────
def detect_booking_service(message):
    text = english_for_intent(message or '').lower()
    booking_words = [
        'book', 'booking', 'ticket', 'tickets', 'reserve',
        'बुक', 'टिकट', 'புக்', 'டிக்கெட்',
        'ಬುಕ್', 'ಟಿಕೆಟ್', 'ബുക്ക്', 'ടിക്കറ്റ്', 'బుక్', 'టికెట్',
    ]
    if not any(word in text for word in booking_words):
        return None
    for service in ('train', 'flight', 'bus', 'cab', 'auto', 'movie'):
        if any(kw.lower() in text for kw in BOOKING_SERVICES[service]['keywords']):
            return service
    return None

def booking_response(service, language):
    info = BOOKING_SERVICES[service]
    reply = (
        f"Opening {info['label']} for {service} booking. "
        "Check the details once before payment."
    )
    return translate_text_safe(reply, language)


# ── Conversation helpers ──────────────────────────────────────────────────────
def get_or_create_conversation(conversation_id, user_id, preview, language, conversation_type='chat'):
    if conversation_id:
        existing = query(
            "SELECT id FROM conversations WHERE id=%s AND user_id=%s",
            (conversation_id, user_id),
            fetchone=True,
        )
        if existing:
            return existing['id']
    return query(
        "INSERT INTO conversations (user_id, preview, language, conversation_type) VALUES (%s,%s,%s,%s)",
        (user_id, (preview or 'Conversation')[:100], language, conversation_type),
        lastrowid=True,
    )


def save_message_pair(conversation_id, user_message, assistant_reply):
    if not conversation_id:
        return
    query(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s,%s,%s)",
        (conversation_id, 'user', user_message),
    )
    query(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s,%s,%s)",
        (conversation_id, 'assistant', assistant_reply),
    )


def is_action_only_history(message):
    value = (message or '').strip().lower()
    return bool(
        detect_website_open_request(value)
        or value.startswith(('open ', 'launch ', 'visit ', 'go to '))
    )


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('splash.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data     = request.get_json() or {}
        email    = (data.get('email') or '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'})

        user = query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid email or password'})
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data     = request.get_json() or {}
        name     = (data.get('name') or '').strip()
        email    = (data.get('email') or '').strip()
        phone    = (data.get('phone') or '').strip()
        password = data.get('password', '')
        location = (data.get('location') or '').strip()
        language = normalize_language(data.get('language', 'en'))

        if not name:
            return jsonify({'success': False, 'message': 'Name is required'})
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', email):
            return jsonify({'success': False, 'message': 'Enter a valid email'})
        if not password or len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'})

        existing = query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True)
        if existing:
            return jsonify({'success': False, 'message': 'Email already registered. Please login.'})

        hashed_password = generate_password_hash(password)
        user_id = query(
            "INSERT INTO users (name, email, phone, password, location, language) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, email, phone, hashed_password, location, language),
            lastrowid=True,
        )
        if not user_id:
            return jsonify({'success': False, 'message': 'Could not create account. Please try again.'})

        session['user_id']   = user_id
        session['user_name'] = name
        return jsonify({'success': True})
    return render_template('signup.html')


@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = query(
        "SELECT language FROM users WHERE id=%s",
        (session['user_id'],),
        fetchone=True,
    ) or {}
    return render_template(
        'home.html',
        user_name=session.get('user_name'),
        user_language=normalize_language(user.get('language', 'en')),
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data            = request.get_json() or {}
    message         = (data.get('message') or '').strip()
    requested_language = normalize_language(data.get('language', 'en'))
    language        = detect_language_from_text(message, requested_language)
    conversation_id = data.get('conversation_id')
    conversation_type = data.get('source', 'chat')
    if conversation_type not in ('chat', 'voice'):
        conversation_type = 'chat'

    if not message:
        return jsonify({'error': 'Empty message'}), 400

    msg_lower = message.lower()

    if is_stop_conversation_request(message):
        return jsonify({
            'reply': translate_text_safe('Conversation stopped.', language),
            'conversation_id': conversation_id,
            'stopped': True,
            'language': language,
        })

    # FIX: action is now a proper object {url, description}
    # so the JS can correctly access data.action.url
    def chat_json(reply, action=None):
        saved_id = get_or_create_conversation(
            conversation_id, session['user_id'], message, language, conversation_type
        )
        if not is_action_only_history(message):
            save_message_pair(saved_id, message, reply)
        payload = {'reply': reply, 'conversation_id': saved_id}
        if action:
            action.setdefault('type', 'open_url')
            payload['action'] = action
        return jsonify(payload)

    website_url = detect_website_open_request(message)
    if website_url:
        return chat_json(
            translate_text_safe("Opening the website now.", language),
            action={'type': 'open_url', 'url': website_url, 'description': 'Open website'},
        )

    # ── Booking intent ────────────────────────────────────────────────────────
    booking_service = detect_booking_service(message)
    if booking_service:
        info = BOOKING_SERVICES[booking_service]
        return chat_json(
            booking_response(booking_service, language),
            action={'type': 'open_url', 'url': info['url'], 'description': f"Open {info['label']}"},
        )

    # ── Simple URL shortcuts ──────────────────────────────────────────────────
    shortcuts = {
        'open google':    ('Opening Google!',    'https://www.google.com'),
        'open youtube':   ('Opening YouTube!',   'https://www.youtube.com'),
        'open facebook':  ('Opening Facebook!',  'https://www.facebook.com'),
        'open twitter':   ('Opening Twitter!',   'https://www.twitter.com'),
        'open instagram': ('Opening Instagram!', 'https://www.instagram.com'),
        'open gmail':     ('Opening Gmail!',     'https://mail.google.com'),
    }
    for trigger, (reply_text, url) in shortcuts.items():
        if trigger in msg_lower:
            return chat_json(
                reply_text,
                action={'type': 'open_url', 'url': url, 'description': reply_text},
            )

    # Generic booking without specific service
    if any(w in msg_lower for w in ('booking', 'book ticket', 'book a ticket',
                                    'book tickets', 'ticket booking')):
        return chat_json(
            translate_text_safe(
                "What would you like to book? I can help with movies, trains, "
                "flights, buses, cabs, or autos.",
                language,
            )
        )

    # ── Groq AI — same HTTP approach as Yogitha's project ─────────────────────
    if not GROQ_API_KEY:
        return chat_json(offline_reply(message, language))

    lang_name = LANGUAGE_NAMES.get(language, 'English')
    system_prompt = (
        f"You are VoxAI, a helpful and friendly AI assistant. "
        f"Always reply in {lang_name}. "
        "Be concise and clear. "
        "Return plain text only. Do not use markdown symbols, asterisks, bullets, or bold formatting."
    )

    try:
        reply = clean_ai_reply(ask_groq(system_prompt, message, max_tokens=1024))
        if language != 'en':
            reply = translate_text_safe(reply, language)
        return chat_json(reply)

    except Exception as e:
        error_str = str(e)
        print(f"Groq error: {error_str}")

        if '429' in error_str or 'quota' in error_str.lower() or 'rate' in error_str.lower():
            msg = "The AI is currently busy. Please wait a moment and try again."
        elif '401' in error_str or 'invalid' in error_str.lower() or 'api key' in error_str.lower():
            msg = "Invalid API key. Please check your GROQ_API_KEY in the .env file."
        else:
            return chat_json(offline_reply(message, language))

        return chat_json(translate_text_safe(msg, language))


# ── Translate endpoint (was MISSING — JS calls this for voice note translation) ─
@app.route('/api/translate', methods=['POST'])
def translate_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data     = request.get_json() or {}
    text     = (data.get('text') or '').strip()
    language = normalize_language(data.get('language', 'en'))
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    translated = translate_text_safe(text, language)
    return jsonify({'text': translated})


# ── TTS endpoint (was MISSING — JS tries this first, then falls back to browser) ─
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    language = normalize_language(data.get('language', 'en'))
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    if not OPENAI_API_KEY:
        return jsonify({'error': 'OPENAI_API_KEY is not configured'}), 404

    # This uses an AI-generated voice. Keep a user-facing disclosure in the app/docs.
    lang_name = LANGUAGE_NAMES.get(language, 'the input language')
    instructions = (
        f"Speak this {lang_name} text aloud in {lang_name}. "
        "Use a sweet, warm, friendly feminine style. "
        "Keep the tone cheerful, gentle, and clear."
    )
    try:
        last_error = ''
        response = None
        used_model = OPENAI_TTS_MODEL
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json',
        }
        for model in dict.fromkeys(OPENAI_TTS_FALLBACK_MODELS):
            voice = data.get('voice') or OPENAI_TTS_VOICE
            if model.startswith('tts-') and voice not in {'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'}:
                voice = 'nova'
            payload = {
                'model': model,
                'voice': voice,
                'input': text[:4000],
                'response_format': 'mp3',
            }
            if model == OPENAI_TTS_MODEL:
                payload['instructions'] = instructions
            response = requests.post(
                OPENAI_TTS_URL,
                headers=headers,
                json=payload,
                timeout=45,
            )
            if response.status_code == 200:
                used_model = model
                break
            try:
                last_error = response.json().get('error', {}).get('message', '')
            except Exception:
                last_error = response.text[:200]

        if not response or response.status_code != 200:
            return jsonify({'error': last_error or 'TTS generation failed'}), 502
        return jsonify({
            'audio': base64.b64encode(response.content).decode('ascii'),
            'format': 'mp3',
            'voice': voice,
            'language': language,
            'model': used_model,
        })
    except Exception as e:
        print(f"TTS error: {e}")
        return jsonify({'error': 'TTS generation failed'}), 502


@app.route('/api/google-tts', methods=['POST'])
def google_tts_proxy():
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    language = normalize_language(data.get('language', 'en'))
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        response = requests.get(
            'https://translate.google.com/translate_tts',
            params={
                'ie': 'UTF-8',
                'client': 'tw-ob',
                'tl': LANG_CODES.get(language, 'en'),
                'q': text[:190],
            },
            headers={
                'User-Agent': 'Mozilla/5.0',
            },
            timeout=20,
        )
        if response.status_code != 200 or not response.content:
            return jsonify({'error': 'Fallback TTS failed'}), 502
        return jsonify({
            'audio': base64.b64encode(response.content).decode('ascii'),
            'format': 'mp3',
            'voice': 'google-translate',
            'language': language,
        })
    except Exception as e:
        print(f"Google TTS error: {e}")
        return jsonify({'error': 'Fallback TTS failed'}), 502


# ── History ───────────────────────────────────────────────────────────────────
@app.route('/api/history')
def history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    rows = query(
        "SELECT c.id, c.preview, c.language, c.conversation_type, c.created_at, "
        "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS message_count "
        "FROM conversations c WHERE c.user_id=%s "
        "ORDER BY c.updated_at DESC",
        (session['user_id'],),
        fetchall=True,
    ) or []
    rows = [
        row for row in rows
        if int(row.get('message_count') or 0) > 0 and not is_action_only_history(row.get('preview'))
    ]
    for row in rows:
        created = row.get('created_at')
        row['created_at'] = created.strftime('%d %b %Y') if created else ''
    return jsonify(rows)


@app.route('/api/audio-history')
def audio_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    rows = query(
        "SELECT id, filename, language, transcript, original_text, provider, created_at "
        "FROM audio_history WHERE user_id=%s "
        "ORDER BY created_at DESC",
        (session['user_id'],),
        fetchall=True,
    ) or []
    for row in rows:
        created = row.get('created_at')
        row['created_at'] = created.strftime('%d %b %Y %H:%M') if created else ''
        preview = row.get('transcript') or row.get('filename') or 'Audio transcript'
        row['preview'] = preview[:100]
    return jsonify(rows)


@app.route('/api/conversation/<int:conversation_id>')
def conversation_detail(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    owner = query(
        "SELECT id FROM conversations WHERE id=%s AND user_id=%s",
        (conversation_id, session['user_id']),
        fetchone=True,
    )
    if not owner:
        return jsonify({'error': 'Conversation not found'}), 404
    rows = query(
        "SELECT role, content, created_at FROM messages "
        "WHERE conversation_id=%s ORDER BY created_at ASC, id ASC",
        (conversation_id,),
        fetchall=True,
    ) or []
    for row in rows:
        created = row.get('created_at')
        row['created_at'] = created.strftime('%d %b %Y %H:%M') if created else ''
    return jsonify(rows)


# ── Speech-to-Text ────────────────────────────────────────────────────────────
@app.route('/api/stt', methods=['POST'])
def speech_to_text():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    target_language = normalize_language(request.args.get('language', 'en'))

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        audio_data = audio_file.read()
        filename   = audio_file.filename or 'audio.ogg'

        # Prefer cloud STT for browser recordings such as OGG/Opus; offline STT is WAV-only.
        provider = ''
        original_text = ''
        prefer_offline = os.path.splitext(filename)[1].lower() == '.wav' and not OPENAI_API_KEY and not GROQ_API_KEY
        if not prefer_offline and OPENAI_API_KEY:
            try:
                original_text = transcribe_audio_openai(
                    audio_data,
                    filename,
                    audio_file.mimetype,
                    target_language,
                )
                provider = f'OpenAI {OPENAI_STT_MODEL}'
            except Exception as openai_error:
                print(f"OpenAI STT failed: {openai_error}")

        if not original_text and not prefer_offline and GROQ_API_KEY:
            try:
                original_text = transcribe_audio_groq(
                    audio_data,
                    filename,
                    audio_file.mimetype,
                    target_language,
                )
                provider = 'Groq Whisper transcription'
            except Exception as groq_error:
                print(f"Groq STT failed: {groq_error}")

        if not original_text:
            try:
                original_text = offline_stt_vosk(audio_data, filename)
                provider = 'Vosk Offline Speech Recognition'
            except Exception as vosk_error:
                print(f"Vosk STT failed, using Windows STT: {vosk_error}")
                original_text = offline_stt_windows(audio_data, filename)
                provider = 'Windows Offline Speech Recognition'

        if not original_text:
            raise RuntimeError('No speech detected. Try a clearer or longer audio clip.')

        final_text = original_text if target_language == 'en' else translate_audio_text(original_text, target_language)

        # ── Translate if a non-English target language is requested ──────────
        query(
            "INSERT INTO audio_history "
            "(user_id, filename, language, transcript, original_text, provider) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (
                session['user_id'],
                filename[:255],
                target_language,
                final_text,
                original_text,
                provider,
            ),
        )

        return jsonify({
            'success':         True,
            'transcript':      final_text,
            'original':        original_text,
            'target_language': target_language,
            'provider':        provider,
        })

    except Exception as e:
        print(f"STT Error: {e}")
        return jsonify({
            'error': (
                f'Offline audio-to-text failed: {e}. For offline mode, upload a clear English WAV file.'
            )
        }), 500


# ── Profile ───────────────────────────────────────────────────────────────────
@app.route('/api/profile', methods=['GET', 'PUT'])
def profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    if request.method == 'PUT':
        data     = request.get_json() or {}
        name     = (data.get('name') or '').strip()
        email    = (data.get('email') or '').strip()
        phone    = (data.get('phone') or '').strip()
        location = (data.get('location') or '').strip()
        language = normalize_language(data.get('language', 'en'))

        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', email):
            return jsonify({'success': False, 'message': 'Enter a valid email'}), 400
        if phone and not re.match(r'^\d{10}$', phone):
            return jsonify({'success': False, 'message': 'Phone number must be 10 digits'}), 400

        duplicate = query(
            "SELECT id FROM users WHERE email=%s AND id<>%s",
            (email, session['user_id']),
            fetchone=True,
        )
        if duplicate:
            return jsonify({'success': False, 'message': 'Email already exists'}), 400

        ok = query(
            "UPDATE users SET name=%s, email=%s, phone=%s, location=%s, language=%s WHERE id=%s",
            (name, email, phone, location, language, session['user_id']),
        )
        if not ok:
            return jsonify({'success': False, 'message': 'Could not update profile'}), 500

        session['user_name'] = name
        return jsonify({'success': True, 'name': name, 'email': email,
                        'phone': phone, 'location': location, 'language': language})

    user = query(
        "SELECT id, name, email, phone, location, language FROM users WHERE id=%s",
        (session['user_id'],),
        fetchone=True,
    )
    return jsonify(user or {})


# ── Entry point ───────────────────────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  VOXAI - POWERED BY GROQ AI (llama-3.3-70b-versatile)")
    print("  Open: http://localhost:5000")
    print("=" * 60)
    if GROQ_API_KEY:
        print("  AI is READY. Try asking anything!")
    else:
        print("  AI not ready - add GROQ_API_KEY to your .env file")
    print("  Audio-to-Text with multilingual translation")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
