from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Intent(str, Enum):
    movie_booking = "movie_booking"
    hotel_booking = "hotel_booking"
    food_order = "food_order"
    cab_booking = "cab_booking"
    cancel_booking = "cancel_booking"
    website_open = "website_open"
    faq = "faq"
    unknown = "unknown"


class SlotSpec(BaseModel):
    name: str
    question: str


class IntentDetection(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)
    detected_language: str = Field(default="en")
    user_goal: str = Field(default="")
    extracted_slots: Dict[str, Any] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    suggested_intents: List[Intent] = Field(default_factory=list)
    assistant_reply: str = Field(default="")


class ConversationState(BaseModel):
    conversation_id: str
    active_intent: Intent = Intent.unknown
    detected_language: str = "en"
    slots: Dict[str, Any] = Field(default_factory=dict)
    pending_slot: Optional[str] = None
    status: Literal["new", "collecting", "ready", "completed", "fallback"] = "new"
    turns: List[Dict[str, str]] = Field(default_factory=list)


class VoiceMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class VoiceMessageResponse(BaseModel):
    conversation_id: str
    intent: Intent
    confidence: float
    assistant_reply: str
    status: str
    detected_language: str
    slots: Dict[str, Any]
    next_question: Optional[str] = None
    action: Optional[Dict[str, Any]] = None
