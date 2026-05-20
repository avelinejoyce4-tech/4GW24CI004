let voiceConversationId = null;

async function sendVoiceTextToAssistant(spokenText) {
  const response = await fetch("http://127.0.0.1:8000/api/voice-assistant/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: spokenText,
      conversation_id: voiceConversationId
    })
  });

  if (!response.ok) {
    throw new Error("Voice assistant request failed");
  }

  const data = await response.json();
  voiceConversationId = data.conversation_id;

  renderAssistantMessage(data.assistant_reply);
  speakText(data.assistant_reply, data.detected_language);

  if (data.action?.type === "open_url" && data.status === "ready") {
    window.open(data.action.url, "_blank", "noopener");
  }

  return data;
}

function renderAssistantMessage(text) {
  const box = document.getElementById("voiceLiveBox");
  if (!box) return;
  box.textContent = `${box.textContent || ""}\n\nVoxAI:\n${text}`.trim();
  box.classList.add("show");
  box.scrollTop = box.scrollHeight;
}

