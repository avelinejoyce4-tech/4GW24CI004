# 🎙️ VoxAI - Voice Intelligence for Everyone

A voice-first AI web app for low-digital-literacy users in India.

---

## 📁 Project Structure

```
voxai/
├── app.py              ← Main Flask server
├── schema.sql          ← MySQL database setup
├── requirements.txt    ← Python packages
├── .env.example        ← Copy to .env and fill keys
├── static/
│   ├── css/style.css   ← All styles
│   └── js/
│       ├── app.js      ← Global utilities
│       └── home.js     ← Main app logic
└── templates/
    ├── splash.html     ← Loading screen
    ├── login.html      ← Sign in page
    ├── signup.html     ← Create account page
    └── home.html       ← Main app (voice, chat, analytics)
```

---

## 🚀 Step-by-Step Setup Guide (For Beginners)

### STEP 1: Install Python
- Download from https://www.python.org/downloads/
- During install, CHECK ✅ "Add Python to PATH"

### STEP 2: Install MySQL
- Download MySQL Community Server: https://dev.mysql.com/downloads/mysql/
- Remember your root password!

### STEP 3: Setup the Database
Open MySQL command line or MySQL Workbench and run:
```sql
-- Copy and paste the entire contents of schema.sql
```

### STEP 4: Get API Keys

**OpenAI (for AI chat):**
- Go to https://platform.openai.com
- Sign up → API Keys → Create new key
- Copy the key (starts with sk-)

**Deepgram (for voice-to-text):**
- Go to https://console.deepgram.com
- Sign up → Create API Key
- Copy the key

**ElevenLabs (for text-to-voice):**
- Go to https://elevenlabs.io
- Sign up → Profile → API Key
- Copy the key

### STEP 5: Configure Environment
```bash
# In the voxai folder, copy the example file:
cp .env.example .env

# Open .env with Notepad and fill in all your keys
```

### STEP 6: Install Python Packages
Open Command Prompt (Windows) / Terminal (Mac/Linux) in the voxai folder:
```bash
pip install -r requirements.txt
```

### STEP 7: Run the App
```bash
python app.py
```

### STEP 8: Open in Browser
Go to: http://localhost:5000

---

## 🌟 Features

- 🎤 **Voice Interaction** — Speak in 9 Indian languages
- 🤖 **AI Chat** — ChatGPT-style conversation in your language
- 🚀 **Task Completion** — AI opens the right website for you
- 📊 **Analytics** — See your usage history and stats
- 👤 **Profile** — Store and edit your details
- 🌙 **Dark Theme** — Easy on the eyes
- 📱 **Mobile Ready** — Works on phone and desktop

## 🌐 Supported Languages
English, Hindi (हिंदी), Tamil (தமிழ்), Kannada (ಕನ್ನಡ),
Malayalam (മലയാളം), Telugu (తెలుగు), Marathi (मराठी),
Bengali (বাংলা), Gujarati (ગુજરાતી)

## 🎯 Supported Tasks
- 🚂 Train ticket booking (IRCTC)
- 🚌 Bus booking (RedBus)
- ✈️ Flight booking (MakeMyTrip)
- 🏛️ Government services
- 🪪 Aadhaar, PAN card services
- 🏦 SBI Online Banking
- 💡 Electricity bill payment
- 🛒 Grocery (BigBasket)
- 💊 Medicine (1mg)
- 💸 UPI / BHIM payments
- And many more!
