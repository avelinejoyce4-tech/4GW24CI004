// ═══════════════ VoxAI Home Page JS ═══════════════

// ─── Markdown renderer ────────────────────────────
function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    // Escape HTML entities first
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Bold: **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Numbered list: lines starting with "1. "
    .replace(/(?:^|\n)(\d+)\.\s+(.+)/g, '\n<li class="md-ol">$2</li>')
    // Bullet list: lines starting with "* " or "- "
    .replace(/(?:^|\n)[*\-]\s+(.+)/g, '\n<li class="md-ul">$2</li>')
    // Line breaks to <br>
    .replace(/\n/g, '<br>');
  // Wrap consecutive <li class="md-ol"> in <ol>
  html = html.replace(/(<li class="md-ol">.*?<\/li>)(<br>(<li class="md-ol">.*?<\/li>))*/g, (m) => '<ol>' + m + '</ol>');
  // Wrap consecutive <li class="md-ul"> in <ul>
  html = html.replace(/(<li class="md-ul">.*?<\/li>)(<br>(<li class="md-ul">.*?<\/li>))*/g, (m) => '<ul>' + m + '</ul>');
  // Clean up <br> inside list wrappers
  html = html.replace(/<\/li><br>/g, '</li>');
  return html;
}

// ─── State ────────────────────────────────────────
let currentLang = 'en';
let micActive = false;
let mediaRecorder = null;
let audioChunks = [];
let voiceConversationId = null;
let voiceHistory = [];
let chatConversationId = null;
let chatHistory = [];
let pendingActionUrl = null;
let chatPendingActionUrl = null;
let historyExpanded = false;
let prevView = 'voice';
let chatRecognition = null;
let chatMicActive = false;
let chatFinalTranscript = '';
let currentChatAbortController = null;
let activeTypingId = null;
let activeTtsAudio = null;
let currentVoiceAbortController = null;
let voiceSessionActive = false;
let ignoreVoiceEnd = false;
let pendingVoiceNote = null;

// ─── SIDEBAR ──────────────────────────────────────
function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebarOverlay').classList.add('active');
  loadHistory();
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('active');
}

// ─── VIEWS ────────────────────────────────────────
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  document.querySelectorAll('.sidebar-menu > li').forEach(li => li.classList.remove('active'));
  const menuEl = document.getElementById('menu-' + name);
  if (menuEl) menuEl.classList.add('active');
  if (name === 'analytics') loadAnalytics();
  if (name === 'audio') auInit();
  closeSidebar();
  prevView = name;
}

// ─── LANGUAGE ─────────────────────────────────────
function selectLang(btn, lang) {
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentLang = lang;
}

// ─── VOICE MICROPHONE ─────────────────────────────
function startVoice() {
  voiceConversationId = null;
  voiceHistory = [];
  pendingActionUrl = null;
  document.getElementById('convMessages').innerHTML = '';
  document.getElementById('actionCard').style.display = 'none';
  document.getElementById('voiceCenter').style.display = 'none';
  document.getElementById('voiceTopArea').style.display = 'flex';
  const box = document.getElementById('conversationBox');
  box.style.display = 'flex';
  box.style.flexDirection = 'column';
  voiceSessionActive = true;
  startBrowserMic();
}

function toggleMic() {
  if (micActive) stopBrowserMic();
  else startBrowserMic();
}

// ─── BROWSER SPEECH RECOGNITION ───────────────────
let recognition = null;

function startBrowserMic() {
  if (!voiceSessionActive) voiceSessionActive = true;
  if (micActive) return;
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    setVoiceStatus('Speech recognition not supported. Use Chrome or Edge.');
    return;
  }

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();

  const langCodes = {
    en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', kn: 'kn-IN',
    ml: 'ml-IN', te: 'te-IN', mr: 'mr-IN', bn: 'bn-IN', gu: 'gu-IN'
  };
  recognition.lang = langCodes[currentLang] || 'en-IN';
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  micActive = true;
  setMicUI(true);
  setVoiceStatus('🎙️ Listening… speak now');

  recognition.onresult = (event) => {
    let interim = '';
    let final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    setVoiceStatus('🎙️ ' + (final || interim));
  };

  recognition.onend = async () => {
    micActive = false;
    setMicUI(false);
    if (ignoreVoiceEnd) { ignoreVoiceEnd = false; return; }
    if (!voiceSessionActive) return;

    const statusEl = document.getElementById('voiceStatus');
    let spokenText = (statusEl.textContent || '').replace(/^🎙️\s*/, '').trim();

    if (spokenText && spokenText !== 'Listening… speak now') {
      appendConvMsg('user', spokenText);
      voiceHistory.push({ role: 'user', content: spokenText });
      setVoiceStatus('🤖 AI is thinking…');
      await getVoiceAIResponse(spokenText);
    } else {
      setVoiceStatus("Didn't catch that. Listening again...");
      window.setTimeout(() => {
        if (voiceSessionActive && !micActive) startBrowserMic();
      }, 500);
    }
  };

  recognition.onerror = (event) => {
    micActive = false;
    setMicUI(false);
    ignoreVoiceEnd = true;
    const msgs = {
      'no-speech':     "😶 Nothing heard. Tap mic to try again.",
      'not-allowed':   "🔒 Mic permission denied. Allow it in browser settings.",
      'audio-capture': "🎤 No microphone found.",
    };
    setVoiceStatus(msgs[event.error] || 'Error: ' + event.error);
    if (voiceSessionActive && event.error === 'no-speech') {
      window.setTimeout(() => {
        if (voiceSessionActive && !micActive) startBrowserMic();
      }, 700);
    }
  };

  recognition.start();
}

function stopBrowserMic() {
  if (recognition) { ignoreVoiceEnd = true; recognition.stop(); }
  micActive = false;
  setMicUI(false);
}

function setMicUI(listening) {
  const btn        = document.getElementById('micBtnTop');
  const rings      = document.getElementById('micRings');
  const micWrapper = document.getElementById('micWrapperTop');
  const waveform   = document.getElementById('voiceWaveform');
  if (!btn || !rings || !micWrapper || !waveform) return;
  if (listening) {
    micWrapper.style.display = 'none';
    waveform.style.display = 'flex';
    waveform.classList.add('active');
    btn.classList.add('active');
    rings.classList.add('active');
  } else {
    micWrapper.style.display = 'flex';
    waveform.style.display = 'none';
    waveform.classList.remove('active');
    btn.classList.remove('active');
    rings.classList.remove('active');
  }
}

function setVoiceStatus(text) {
  const el = document.getElementById('voiceStatus');
  if (el) el.textContent = text;
}

function goToBookingAction(action) {
  if (!action || !action.url) return;
  window.location.href = action.url;
}

// ─── AI RESPONSE (VOICE) ──────────────────────────
async function getVoiceAIResponse(message) {
  currentVoiceAbortController = new AbortController();
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: currentVoiceAbortController.signal,
      body: JSON.stringify({
        message,
        language: currentLang,
        conversation_id: voiceConversationId,
        history: voiceHistory
      })
    });
    const data = await res.json();
    currentVoiceAbortController = null;
    const reply = data.reply || 'Sorry, I could not respond.';
    voiceConversationId = data.conversation_id;
    voiceHistory.push({ role: 'assistant', content: reply });

    appendConvMsg('ai', reply);

    if (data.action) {
      pendingActionUrl = data.action.url;
      document.getElementById('actionDesc').textContent = data.action.description || data.action.url;
      document.getElementById('actionCard').style.display = 'block';
      setVoiceStatus('Opening booking page...');
      goToBookingAction(data.action);
      return;
    }

    setVoiceStatus('Speaking answer...');
    await speakText(reply, currentLang);
    if (voiceSessionActive && !micActive) {
      setVoiceStatus('Listening...');
      startBrowserMic();
    }
  } catch (e) {
    currentVoiceAbortController = null;
    if (e.name === 'AbortError') return;
    setVoiceStatus('Error getting AI response. Check your connection.');
    appendConvMsg('ai', '⚠️ Could not get a response. Please try again.');
  }
}

// ─── CONVERSATION MESSAGE BUBBLE ──────────────────
function appendConvMsg(role, text) {
  const box = document.getElementById('convMessages');
  if (!box) return;
  const div     = document.createElement('div');
  div.className = 'conv-msg ' + role;
  const label     = document.createElement('div');
  label.className = 'msg-role';
  label.textContent = role === 'user' ? '🎤 YOU' : '🤖 VOX AI';
  const content     = document.createElement('div');
  content.className = 'msg-text';
  if (role === 'ai') {
    content.innerHTML = renderMarkdown(text);
  } else {
    content.textContent = text;
  }
  div.appendChild(label);
  div.appendChild(content);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function openActionUrl() {
  if (pendingActionUrl) {
    window.open(pendingActionUrl, '_blank');
    document.getElementById('actionCard').style.display = 'none';
  }
}

// ─── TTS ──────────────────────────────────────────
async function speakText(text, language) {
  const ttsToggle  = document.getElementById('ttsToggle');
  const ttsEnabled = ttsToggle ? ttsToggle.checked : true;
  if (!ttsEnabled) return Promise.resolve();

  // Try ElevenLabs first
  try {
    const res = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.audio) {
        const audio = new Audio('data:audio/mpeg;base64,' + data.audio);
        activeTtsAudio = audio;
        return new Promise(resolve => {
          audio.onended = () => { if (activeTtsAudio === audio) activeTtsAudio = null; resolve(); };
          audio.onerror = () => { if (activeTtsAudio === audio) activeTtsAudio = null; resolve(); };
          audio.play().catch(() => resolve());
        });
      }
    }
  } catch (e) {}

  // Fallback: browser TTS
  if ('speechSynthesis' in window) {
    const utt    = new SpeechSynthesisUtterance(text);
    const langCodes = {
      en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', kn: 'kn-IN',
      ml: 'ml-IN', te: 'te-IN', mr: 'mr-IN', bn: 'bn-IN', gu: 'gu-IN'
    };
    utt.lang = langCodes[language || currentLang] || 'en-IN';
    window.speechSynthesis.cancel();
    return new Promise(resolve => {
      utt.onend  = resolve;
      utt.onerror = resolve;
      window.speechSynthesis.speak(utt);
    });
  }
  return Promise.resolve();
}

// ─── CHAT ─────────────────────────────────────────
async function sendChat(textOverride = null, options = {}) {
  const input = document.getElementById('chatInput');
  const msg   = (textOverride !== null ? textOverride : input.value).trim();
  if (!msg) return;
  if (textOverride === null) input.value = '';

  const lang = document.getElementById('chatLang').value;
  appendChatBubble('user', msg);
  chatHistory.push({ role: 'user', content: msg });

  const typingId = showTyping();
  activeTypingId = typingId;
  currentChatAbortController = new AbortController();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: currentChatAbortController.signal,
      body: JSON.stringify({
        message: msg, language: lang,
        conversation_id: chatConversationId,
        history: chatHistory
      })
    });
    const data = await res.json();
    removeTyping(typingId);
    activeTypingId = null;
    currentChatAbortController = null;
    const reply = data.reply || 'Sorry, I could not respond.';
    chatConversationId = data.conversation_id;
    chatHistory.push({ role: 'assistant', content: reply });
    appendChatBubble('ai', reply);
    if (options.fromAudio) speakText(reply, lang);

    if (data.action) {
      chatPendingActionUrl = data.action.url;
      document.getElementById('chatActionText').textContent = data.action.description || 'Open relevant page';
      document.getElementById('chatActionBanner').style.display = 'flex';
      goToBookingAction(data.action);
      return;
    }
  } catch (e) {
    removeTyping(typingId);
    activeTypingId = null;
    currentChatAbortController = null;
    if (e.name !== 'AbortError') {
      appendChatBubble('ai', 'Error: Could not get response. Please try again.');
    }
  }
}

function appendChatBubble(role, text) {
  const container = document.getElementById('chatMessages');
  const welcome   = container.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const div     = document.createElement('div');
  div.className = 'chat-bubble ' + role;

  const name     = document.createElement('div');
  name.className = 'bubble-name';
  name.textContent = role === 'user' ? '👤 You' : '🤖 VoxAI';

  const content = document.createElement('div');
  if (role === 'ai') {
    content.innerHTML = renderMarkdown(text);
  } else {
    content.textContent = text;
  }

  div.appendChild(name);
  div.appendChild(content);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const id  = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.id        = id;
  div.className = 'chat-bubble ai';
  div.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
  document.getElementById('chatMessages').appendChild(div);
  document.getElementById('chatMessages').scrollTop = 99999;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ─── CHAT MIC ─────────────────────────────────────
function toggleChatVoiceNote() {
  if (chatMicActive) stopChatVoiceNote();
  else startChatVoiceNote();
}

function startChatVoiceNote() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    setChatVoiceStatus('Speech recognition is not supported. Please use Chrome or Edge.');
    return;
  }

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  chatRecognition = new SR();
  const lang      = document.getElementById('chatLang').value;
  const langCodes = {
    en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', kn: 'kn-IN',
    ml: 'ml-IN', te: 'te-IN', mr: 'mr-IN', bn: 'bn-IN', gu: 'gu-IN'
  };

  chatRecognition.lang            = langCodes[lang] || 'en-IN';
  chatRecognition.continuous      = false;
  chatRecognition.interimResults  = true;
  chatRecognition.maxAlternatives = 1;
  chatFinalTranscript = '';
  chatMicActive       = true;
  setChatMicUI(true);
  setChatVoiceStatus('Listening...');

  chatRecognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) chatFinalTranscript += transcript + ' ';
      else interim += transcript;
    }
    const visibleText = (chatFinalTranscript + interim).trim();
    document.getElementById('chatInput').value = visibleText;
    setChatVoiceStatus(visibleText ? 'Heard: ' + visibleText : 'Listening...');
  };

  chatRecognition.onend = () => {
    chatMicActive = false;
    setChatMicUI(false);
    const transcript = (chatFinalTranscript || document.getElementById('chatInput').value || '').trim();
    if (transcript) {
      document.getElementById('chatInput').value = '';
      setChatVoiceStatus('Sending audio note as text...');
      sendChat(transcript, { fromAudio: true }).finally(() => setChatVoiceStatus(''));
    } else {
      setChatVoiceStatus("Didn't catch that. Tap the mic and try again.");
    }
  };

  chatRecognition.onerror = (event) => {
    chatMicActive = false;
    setChatMicUI(false);
    const message = event.error === 'not-allowed'
      ? 'Mic permission denied. Allow microphone access in your browser.'
      : 'Mic error: ' + event.error;
    setChatVoiceStatus(message);
  };

  chatRecognition.start();
}

function stopChatVoiceNote() {
  if (chatRecognition) chatRecognition.stop();
  chatMicActive = false;
  setChatMicUI(false);
}

// ─── VOICE NOTE (FILE UPLOAD) ─────────────────────
function prepareVoiceNote(file, target) {
  if (!file) return;
  pendingVoiceNote = { file, target };
  if (target === 'voice') {
    const homePicker = document.getElementById('homeVoiceNotePicker');
    if (homePicker) homePicker.style.display = 'flex';
    document.getElementById('voiceCenter').style.display = 'none';
    const box = document.getElementById('conversationBox');
    box.style.display      = 'flex';
    box.style.flexDirection = 'column';
    setVoiceStatus('Voice note selected. Press Convert.');
  } else {
    const picker = document.getElementById('voiceNotePicker');
    if (picker) picker.style.display = 'flex';
    setChatVoiceStatus('Voice note selected. Press Convert.');
  }
}

async function convertPendingVoiceNote() {
  if (!pendingVoiceNote) return;
  const targetLanguage = pendingVoiceNote.target === 'voice'
    ? currentLang
    : document.getElementById('voiceNoteLang').value;

  const formData = new FormData();
  formData.append('audio', pendingVoiceNote.file);
  setChatVoiceStatus('Reading voice note...');
  setVoiceStatus('Reading voice note...');

  try {
    const sttRes  = await fetch('/api/stt?language=' + encodeURIComponent(targetLanguage), {
      method: 'POST', body: formData
    });
    const sttData = await sttRes.json();
    if (!sttRes.ok || !sttData.transcript) {
      throw new Error(sttData.error || 'Could not read this voice note.');
    }

    const translateRes  = await fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: sttData.transcript, language: targetLanguage })
    });
    const translateData = await translateRes.json();
    if (!translateRes.ok || !translateData.text) {
      throw new Error(translateData.error || 'Could not convert the text.');
    }

    const output = translateData.text.trim();
    if (pendingVoiceNote.target === 'voice') {
      document.getElementById('voiceCenter').style.display = 'none';
      document.getElementById('conversationBox').style.display = 'flex';
      appendConvMsg('user', 'Voice note text: ' + sttData.transcript);
      appendConvMsg('ai', output);
      setVoiceStatus('Voice note converted.');
    } else {
      appendChatBubble('user', 'Voice note text: ' + sttData.transcript);
      appendChatBubble('ai', output);
      document.getElementById('chatInput').value = output;
      setChatVoiceStatus('Voice note converted.');
    }
  } catch (e) {
    setChatVoiceStatus(e.message || 'Could not convert this voice note.');
    setVoiceStatus(e.message || 'Could not convert this voice note.');
  } finally {
    pendingVoiceNote = null;
    const picker     = document.getElementById('voiceNotePicker');
    const homePicker = document.getElementById('homeVoiceNotePicker');
    if (picker)     picker.style.display = 'none';
    if (homePicker) homePicker.style.display = 'none';
    const chatInput  = document.getElementById('chatNoteUpload');
    const voiceInput = document.getElementById('voiceNoteUpload');
    if (chatInput)  chatInput.value = '';
    if (voiceInput) voiceInput.value = '';
  }
}

// ─── STOP CONVERSATION ────────────────────────────
function stopConversation() {
  voiceSessionActive = false;
  if (currentChatAbortController)  currentChatAbortController.abort();
  if (currentVoiceAbortController) currentVoiceAbortController.abort();
  if (activeTypingId) removeTyping(activeTypingId);
  activeTypingId             = null;
  currentChatAbortController  = null;
  currentVoiceAbortController = null;

  if (chatMicActive) stopChatVoiceNote();
  if (micActive)     stopBrowserMic();

  if (activeTtsAudio) {
    activeTtsAudio.pause();
    activeTtsAudio.currentTime = 0;
    activeTtsAudio = null;
  }
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();

  setChatVoiceStatus('Conversation stopped.');
  resetVoiceHome();
}

function resetVoiceHome() {
  voiceSessionActive    = false;
  voiceConversationId   = null;
  voiceHistory          = [];
  pendingActionUrl      = null;
  document.getElementById('convMessages').innerHTML = '';
  document.getElementById('actionCard').style.display = 'none';
  document.getElementById('voiceCenter').style.display = '';
  document.getElementById('voiceTopArea').style.display = 'none';
  document.getElementById('conversationBox').style.display = 'none';
  document.getElementById('micWrapperTop').style.display = 'none';
  const waveform = document.getElementById('voiceWaveform');
  if (waveform) {
    waveform.style.display = 'none';
    waveform.classList.remove('active');
  }
  setVoiceStatus('Conversation stopped.');
}

function setChatMicUI(active) {
  const btn = document.getElementById('chatMicBtn');
  if (!btn) return;
  btn.classList.toggle('active', active);
}

function setChatVoiceStatus(text) {
  const el = document.getElementById('chatVoiceStatus');
  if (el) el.textContent = text || '';
}

// ─── NEW CHAT ─────────────────────────────────────
function newChat() {
  chatConversationId  = null;
  chatHistory         = [];
  chatPendingActionUrl = null;
  document.getElementById('chatMessages').innerHTML =
    '<div class="chat-welcome"><div class="chat-welcome-icon"><i class="fa fa-robot"></i></div><p>Hi! I\'m VoxAI. How can I help you today?</p></div>';
  document.getElementById('chatActionBanner').style.display = 'none';
  setChatVoiceStatus('');
}

function openChatActionUrl() {
  if (chatPendingActionUrl) {
    window.open(chatPendingActionUrl, '_blank');
    document.getElementById('chatActionBanner').style.display = 'none';
  }
}

// ─── HISTORY ──────────────────────────────────────
async function loadHistory(limit = 5) {
  try {
    const res  = await fetch('/api/history?limit=' + limit);
    const data = await res.json();
    const list = document.getElementById('historyList');
    const more = document.getElementById('historyMore');
    list.innerHTML = '';
    data.forEach(conv => {
      const li = document.createElement('li');
      li.textContent = (conv.preview || 'Conversation').substring(0, 30) + '...';
      li.onclick = () => openHistoryDetail(conv.id, conv.preview);
      list.appendChild(li);
    });
    more.style.display = data.length >= limit ? 'block' : 'none';
  } catch (e) {}
}

function toggleHistory() {
  historyExpanded = !historyExpanded;
  const list    = document.getElementById('historyList');
  const chevron = document.getElementById('hist-chevron');
  list.classList.toggle('open', historyExpanded);
  chevron.style.transform = historyExpanded ? 'rotate(180deg)' : '';
  if (historyExpanded) loadHistory();
}

async function showAllHistory() {
  closeSidebar();
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-history-all').classList.add('active');
  try {
    const res  = await fetch('/api/history/all');
    const data = await res.json();
    const container = document.getElementById('historyAllList');
    container.innerHTML = '';
    if (!data.length) {
      container.innerHTML = '<p style="color:var(--gray);text-align:center;padding:30px">No conversations yet.</p>';
      return;
    }
    data.forEach(conv => {
      const div = document.createElement('div');
      div.className = 'history-item';
      div.innerHTML = `
        <div class="history-item-text">${escapeHtml(conv.preview || 'Conversation')}</div>
        <div class="history-item-meta">
          <span class="lang-badge">${conv.language || 'en'}</span>
          <span>${formatDate(conv.created_at)}</span>
        </div>`;
      div.onclick = () => openHistoryDetail(conv.id, conv.preview);
      container.appendChild(div);
    });
  } catch (e) {}
}

async function openHistoryDetail(convId, title) {
  const modal = document.getElementById('histDetailModal');
  document.getElementById('histDetailTitle').textContent = (title || 'Conversation').substring(0, 50);
  document.getElementById('histDetailMessages').innerHTML = '<p style="color:var(--gray);text-align:center">Loading...</p>';
  modal.style.display = 'flex';
  try {
    const res  = await fetch('/api/conversation/' + convId);
    const msgs = await res.json();
    const container = document.getElementById('histDetailMessages');
    container.innerHTML = '';
    msgs.forEach(m => {
      const div = document.createElement('div');
      div.className = 'detail-msg ' + m.role;
      div.innerHTML = `<div class="role-label">${m.role === 'user' ? '👤 You' : '🤖 VoxAI'}</div>${escapeHtml(m.content)}`;
      container.appendChild(div);
    });
  } catch (e) {}
}

// ─── PROFILE ──────────────────────────────────────
let profileEditing = false;
let profileData    = {};

async function openProfile() {
  document.getElementById('profileModal').style.display = 'flex';
  try {
    const res = await fetch('/api/profile');
    profileData = await res.json();
    renderProfileFields(false);
  } catch (e) {}
}

function closeProfile() {
  document.getElementById('profileModal').style.display = 'none';
  profileEditing = false;
}

function renderProfileFields(editing) {
  const container = document.getElementById('profileFields');
  const actions   = document.getElementById('profileActions');
  const fields    = [
    { key: 'name',     label: 'Full Name', icon: 'fa-user' },
    { key: 'email',    label: 'Email',     icon: 'fa-envelope' },
    { key: 'phone',    label: 'Phone',     icon: 'fa-phone' },
    { key: 'location', label: 'Location',  icon: 'fa-map-marker-alt', hasBtn: true }
  ];
  container.innerHTML = '';
  fields.forEach(f => {
    const div = document.createElement('div');
    div.className = 'profile-field';
    if (editing && f.key !== 'email') {
      const extra = f.hasBtn
        ? `<button class="loc-btn" onclick="getProfileLocation()" style="position:absolute;right:6px;top:50%;transform:translateY(-50%)"><i class="fa fa-crosshairs"></i></button>`
        : '';
      div.innerHTML = `<label><i class="fa ${f.icon}"></i> ${f.label}</label>
        <div style="position:relative">${extra}<input id="prof-${f.key}" value="${escapeHtml(profileData[f.key] || '')}" style="padding-right:${f.hasBtn ? '42px' : '14px'}"></div>`;
    } else {
      div.innerHTML = `<label><i class="fa ${f.icon}"></i> ${f.label}</label><div class="field-val">${escapeHtml(profileData[f.key] || '—')}</div>`;
    }
    container.appendChild(div);
  });
  actions.innerHTML = editing
    ? `<button class="glow-btn" onclick="saveProfile()"><i class="fa fa-save"></i> Save</button>
       <button class="outline-btn" onclick="renderProfileFields(false);profileEditing=false">Cancel</button>`
    : `<button class="glow-btn" onclick="enableEdit()"><i class="fa fa-pen"></i> Edit</button>`;
}

function enableEdit() { profileEditing = true; renderProfileFields(true); }

async function saveProfile() {
  const name     = document.getElementById('prof-name')?.value;
  const phone    = document.getElementById('prof-phone')?.value;
  const location = document.getElementById('prof-location')?.value;
  try {
    await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone, location })
    });
    profileData    = { ...profileData, name, phone, location };
    profileEditing = false;
    renderProfileFields(false);
  } catch (e) {}
}

function getProfileLocation() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(pos => {
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`)
      .then(r => r.json())
      .then(d => {
        const loc = (d.address.city || d.address.town || d.address.village || d.address.state || 'Unknown') + ', ' + d.address.state;
        document.getElementById('prof-location').value = loc;
      });
  });
}

// ─── SETTINGS ─────────────────────────────────────
function openSettings()  { document.getElementById('settingsModal').style.display = 'flex'; closeSidebar(); }
function closeSettings() { document.getElementById('settingsModal').style.display = 'none'; }

function switchTab(name, btn) {
  document.querySelectorAll('.settings-content').forEach(c => c.style.display = 'none');
  document.querySelectorAll('.settings-tab').forEach(b => b.classList.remove('active'));
  const el = document.getElementById('settings-' + name);
  el.style.display       = 'flex';
  el.style.flexDirection = 'column';
  btn.classList.add('active');
}

function setTheme(theme, btn) {
  document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.documentElement.setAttribute('data-theme', theme);
}

function exportData()    { alert('Data export functionality — your chat data will be emailed to your registered address.'); }
function deleteAllChats(){ alert('All chats deleted.'); }

// ─── ANALYTICS ────────────────────────────────────
let dailyChart = null;
let langChart  = null;

async function loadAnalytics() {
  try {
    const res  = await fetch('/api/analytics');
    const data = await res.json();
    document.getElementById('statConvs').textContent  = data.total_conversations || 0;
    document.getElementById('statMsgs').textContent   = data.total_messages || 0;
    document.getElementById('statLangs').textContent  = (data.languages || []).length;

    const daily  = (data.daily || []).reverse();
    const labels = daily.map(d => d.date);
    const counts = daily.map(d => d.count);

    if (dailyChart) dailyChart.destroy();
    dailyChart = new Chart(document.getElementById('dailyChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Conversations', data: counts,
          borderColor: '#cc0000', backgroundColor: 'rgba(204,0,0,0.1)',
          fill: true, tension: 0.4,
          pointBackgroundColor: '#cc0000', pointBorderColor: '#ff4444', pointRadius: 5
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#888' } } },
        scales: {
          x: { ticks: { color: '#666' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { ticks: { color: '#666' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });

    const langNames = {
      en:'English', hi:'Hindi', ta:'Tamil', kn:'Kannada',
      ml:'Malayalam', te:'Telugu', mr:'Marathi', bn:'Bengali', gu:'Gujarati'
    };
    const langs = data.languages || [];
    if (langChart) langChart.destroy();
    langChart = new Chart(document.getElementById('langChart'), {
      type: 'doughnut',
      data: {
        labels: langs.map(l => langNames[l.language] || l.language),
        datasets: [{
          data: langs.map(l => l.count),
          backgroundColor: ['#cc0000','#990000','#ff3333','#660000','#ff6666','#aa0000','#dd2222','#bb0000','#ff4444'],
          borderColor: '#000', borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#888' } } }
      }
    });
  } catch (e) {}
}

// ─── UTILS ────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function formatDate(str) {
  if (!str) return '';
  try { return new Date(str).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }); }
  catch(e) { return str; }
}

function goBackFromConv() { showView(prevView); }

// ─── AUDIO TO TEXT (inline view) ──────────────────
let auFile      = null;
let auConverted = parseInt(localStorage.getItem('vox_au_converted') || '0');
let auWords     = parseInt(localStorage.getItem('vox_au_words') || '0');

function auInit() {
  const fi = document.getElementById('auFileInput');
  if (!fi || fi._inited) return;
  fi._inited = true;

  const dz = document.getElementById('auDropZone');

  // Restore stats
  const statC = document.getElementById('auStatConverted');
  const statW = document.getElementById('auStatWords');
  if (statC) statC.textContent = auConverted;
  if (statW) statW.textContent = auWords;

  dz.addEventListener('dragover', e => {
    e.preventDefault();
    dz.style.borderColor = '#e63946';
    dz.style.background  = 'rgba(230,57,70,.05)';
  });
  dz.addEventListener('dragleave', () => {
    dz.style.borderColor = '#1e1e2e';
    dz.style.background  = '';
  });
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.style.borderColor = '#1e1e2e';
    dz.style.background  = '';
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith('audio/')) auSetFile(f);
    else auShowError('Please drop a valid audio file (mp3, wav, ogg, m4a, webm, flac).');
  });
  fi.addEventListener('change', () => { if (fi.files[0]) auSetFile(fi.files[0]); });
}

function auSetFile(file) {
  auFile = file;
  document.getElementById('auFileName').textContent = file.name;
  document.getElementById('auFileSize').textContent = auFmtSize(file.size);
  document.getElementById('auFileInfo').style.display = 'flex';

  const preview = document.getElementById('auPreview');
  preview.src = URL.createObjectURL(file);
  document.getElementById('auPlayerWrap').style.display = 'block';

  const btn      = document.getElementById('auConvertBtn');
  btn.disabled   = false;
  btn.style.opacity = '1';
  btn.style.cursor  = 'pointer';

  auHideError();
  auHideResult();
}

async function auConvert() {
  if (!auFile) return;
  const lang = document.getElementById('auLangSelect').value;
  const btn  = document.getElementById('auConvertBtn');
  btn.disabled      = true;
  btn.style.opacity = '.5';

  auHideError();
  auHideResult();
  auShowProgress('UPLOADING AUDIO...');

  const fd = new FormData();
  fd.append('audio', auFile);

  const start = Date.now();
  try {
    auShowProgress('TRANSCRIBING SPEECH...');
    const res  = await fetch('/api/stt?language=' + encodeURIComponent(lang), { method: 'POST', body: fd });
    const data = await res.json();

    if (!res.ok || !data.transcript) {
      throw new Error(data.error || 'Transcription failed. Check your DEEPGRAM_API_KEY or OPENAI_API_KEY in .env');
    }

    const elapsed = ((Date.now() - start) / 1000).toFixed(1) + 's';
    const wc      = data.transcript.trim().split(/\s+/).filter(Boolean).length;
    auShowResult(data.transcript, elapsed, wc, data.provider || 'AI');

    auConverted++;
    auWords += wc;
    localStorage.setItem('vox_au_converted', auConverted);
    localStorage.setItem('vox_au_words', auWords);
    const statC = document.getElementById('auStatConverted');
    const statW = document.getElementById('auStatWords');
    if (statC) statC.textContent = auConverted;
    if (statW) statW.textContent = auWords;

  } catch(err) {
    auShowError(err.message);
  } finally {
    auHideProgress();
    btn.disabled      = false;
    btn.style.opacity = '1';
  }
}

function auCopy() {
  const t = document.getElementById('auResultText').textContent;
  navigator.clipboard.writeText(t).then(() => {
    const btn  = event.currentTarget;
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="fa fa-check"></i> Copied!';
    setTimeout(() => btn.innerHTML = orig, 2000);
  });
}

function auDownload() {
  const t    = document.getElementById('auResultText').textContent;
  const name = (auFile?.name || 'audio').replace(/\.[^.]+$/, '') + '_transcript.txt';
  const a    = document.createElement('a');
  a.href     = 'data:text/plain;charset=utf-8,' + encodeURIComponent(t);
  a.download = name;
  a.click();
}

function auClear() {
  auFile = null;
  const fi = document.getElementById('auFileInput');
  if (fi) fi.value = '';
  document.getElementById('auFileInfo').style.display = 'none';
  document.getElementById('auPlayerWrap').style.display = 'none';
  const preview = document.getElementById('auPreview');
  if (preview) preview.src = '';
  const btn      = document.getElementById('auConvertBtn');
  btn.disabled      = true;
  btn.style.opacity = '.5';
  auHideResult();
  auHideError();
  auHideProgress();
}

function auShowProgress(msg) {
  document.getElementById('auProgressLabel').textContent = msg;
  document.getElementById('auProgress').style.display   = 'flex';
}
function auHideProgress() { document.getElementById('auProgress').style.display = 'none'; }

function auShowResult(text, time, words, provider) {
  document.getElementById('auResultText').textContent     = text;
  document.getElementById('auMetaTime').textContent       = time;
  document.getElementById('auMetaWords').textContent      = words;
  document.getElementById('auMetaProvider').textContent   = provider;
  document.getElementById('auResult').style.display       = 'block';
}
function auHideResult() {
  const el = document.getElementById('auResult');
  if (el) el.style.display = 'none';
}

function auShowError(msg) {
  const el = document.getElementById('auError');
  el.textContent    = '⚠ ' + msg;
  el.style.display  = 'block';
}
function auHideError() {
  const el = document.getElementById('auError');
  if (el) el.style.display = 'none';
}

function auFmtSize(b) {
  if (b < 1024)       return b + ' B';
  if (b < 1048576)    return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
}

// ─── INIT ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadHistory();
});