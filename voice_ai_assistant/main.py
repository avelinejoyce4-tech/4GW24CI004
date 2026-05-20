from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from voice_ai_assistant.flow import ConversationFlowEngine
from voice_ai_assistant.intent_detector import IntentDetector
from voice_ai_assistant.models import VoiceMessageRequest, VoiceMessageResponse
from voice_ai_assistant.state import ConversationStateManager


app = FastAPI(title="VoxAI Conversational Voice Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_manager = ConversationStateManager(ttl_minutes=90)
intent_detector = IntentDetector()
flow_engine = ConversationFlowEngine()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/voice-assistant/message", response_model=VoiceMessageResponse)
def handle_voice_message(request: VoiceMessageRequest):
    """Main conversational endpoint called after speech-to-text.

    The frontend sends recognized text and a conversation_id. The backend:
    1. Loads conversation memory.
    2. Uses AI to classify intent and extract slots.
    3. Updates state.
    4. Returns the next assistant utterance and optional action.
    """

    state = state_manager.get_or_create(request.conversation_id)
    state.turns.append({"role": "user", "content": request.message})

    try:
        detection = intent_detector.detect(request.message, state)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Intent detection failed: {exc}") from exc

    payload = flow_engine.apply_detection(state, detection)
    state.turns.append({"role": "assistant", "content": payload["assistant_reply"]})
    state_manager.save(state)
    return VoiceMessageResponse(**payload)


@app.delete("/api/voice-assistant/conversations/{conversation_id}")
def clear_conversation(conversation_id: str):
    state_manager.delete(conversation_id)
    return {"success": True}

