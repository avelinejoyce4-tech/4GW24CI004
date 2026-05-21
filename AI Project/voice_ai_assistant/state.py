from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4

from voice_ai_assistant.models import ConversationState


class ConversationStateManager:
    """Small in-memory state store.

    For production with multiple workers, replace this with Redis or a database table.
    """

    def __init__(self, ttl_minutes: int = 60):
        self._states: Dict[str, ConversationState] = {}
        self._expires_at: Dict[str, datetime] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def get_or_create(self, conversation_id: Optional[str]) -> ConversationState:
        self._cleanup_expired()
        if conversation_id and conversation_id in self._states:
            self._touch(conversation_id)
            return self._states[conversation_id]

        new_id = conversation_id or str(uuid4())
        state = ConversationState(conversation_id=new_id)
        self._states[new_id] = state
        self._touch(new_id)
        return state

    def save(self, state: ConversationState) -> None:
        self._states[state.conversation_id] = state
        self._touch(state.conversation_id)

    def delete(self, conversation_id: str) -> None:
        self._states.pop(conversation_id, None)
        self._expires_at.pop(conversation_id, None)

    def _touch(self, conversation_id: str) -> None:
        self._expires_at[conversation_id] = datetime.now(timezone.utc) + self._ttl

    def _cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [cid for cid, ts in self._expires_at.items() if ts <= now]
        for cid in expired:
            self.delete(cid)


def summarize_state(state: ConversationState) -> str:
    recent_turns = state.turns[-6:]
    lines = [
        f"conversation_id: {state.conversation_id}",
        f"active_intent: {state.active_intent.value}",
        f"status: {state.status}",
        f"detected_language: {state.detected_language}",
        f"known_slots: {state.slots}",
        f"pending_slot: {state.pending_slot}",
        "recent_turns:",
    ]
    lines.extend(f"- {turn['role']}: {turn['content']}" for turn in recent_turns)
    return "\n".join(lines)

