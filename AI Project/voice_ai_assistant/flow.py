from typing import Any, Dict, List, Optional

from voice_ai_assistant.models import ConversationState, Intent, IntentDetection


CONFIDENCE_THRESHOLD = 0.65


REQUIRED_SLOTS: Dict[Intent, List[str]] = {
    Intent.movie_booking: ["city", "genre", "date_or_time"],
    Intent.hotel_booking: ["city", "check_in", "check_out", "guests"],
    Intent.food_order: ["city", "food_or_restaurant", "delivery_location"],
    Intent.cab_booking: ["pickup_location", "drop_location", "date_or_time"],
    Intent.cancel_booking: ["booking_type", "booking_id_or_name"],
    Intent.website_open: ["website_url"],
    Intent.faq: [],
    Intent.unknown: [],
}


SLOT_QUESTIONS: Dict[Intent, Dict[str, str]] = {
    Intent.movie_booking: {
        "city": "Sure, which city should I search in?",
        "genre": "Which genre do you prefer?",
        "date_or_time": "When would you like to watch it?",
    },
    Intent.hotel_booking: {
        "city": "Which city do you want to stay in?",
        "check_in": "What is your check-in date?",
        "check_out": "What is your check-out date?",
        "guests": "How many guests will be staying?",
    },
    Intent.food_order: {
        "city": "Which city are you ordering in?",
        "food_or_restaurant": "What food or restaurant would you like?",
        "delivery_location": "Where should it be delivered?",
    },
    Intent.cab_booking: {
        "pickup_location": "What is your pickup location?",
        "drop_location": "Where do you want to go?",
        "date_or_time": "When do you need the cab?",
    },
    Intent.cancel_booking: {
        "booking_type": "What type of booking do you want to cancel?",
        "booking_id_or_name": "Please share the booking ID or booking name.",
    },
    Intent.website_open: {
        "website_url": "Which website should I open?",
    },
}


ACTION_BY_INTENT: Dict[Intent, Dict[str, Any]] = {
    Intent.movie_booking: {"type": "open_url", "url": "https://in.bookmyshow.com"},
    Intent.hotel_booking: {"type": "open_url", "url": "https://www.booking.com"},
    Intent.food_order: {"type": "open_url", "url": "https://www.swiggy.com"},
    Intent.cab_booking: {"type": "open_url", "url": "https://www.uber.com/in/en/"},
}


class ConversationFlowEngine:
    """Turns intent detection results into an Alexa/Siri style conversation."""

    def apply_detection(
        self,
        state: ConversationState,
        detection: IntentDetection,
    ) -> Dict[str, Any]:
        state.detected_language = detection.detected_language or state.detected_language
        state.slots.update(self._clean_slots(detection.extracted_slots))

        if detection.confidence < CONFIDENCE_THRESHOLD:
            state.status = "fallback"
            state.active_intent = Intent.unknown
            state.pending_slot = None
            reply = self._low_confidence_reply(detection)
            return self._payload(state, detection, reply)

        if detection.intent != Intent.unknown:
            state.active_intent = detection.intent

        missing_slot = self._first_missing_slot(state)
        if missing_slot:
            state.status = "collecting"
            state.pending_slot = missing_slot
            reply = self._question_for(state.active_intent, missing_slot, detection)
            return self._payload(state, detection, reply, next_question=reply)

        state.pending_slot = None
        if state.active_intent in (Intent.faq, Intent.unknown):
            state.status = "completed"
            reply = detection.assistant_reply or "I can help with movies, hotels, food, cabs, cancellations, and FAQs."
            return self._payload(state, detection, reply)

        state.status = "ready"
        reply = self._ready_reply(state, detection)
        action = self._action_for_state(state)
        return self._payload(state, detection, reply, action=action)

    @staticmethod
    def _clean_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value
            for key, value in (slots or {}).items()
            if value not in (None, "", [], {})
        }

    def _first_missing_slot(self, state: ConversationState) -> Optional[str]:
        for slot in REQUIRED_SLOTS.get(state.active_intent, []):
            if not state.slots.get(slot):
                return slot
        return None

    @staticmethod
    def _question_for(intent: Intent, slot: str, detection: IntentDetection) -> str:
        return (
            detection.assistant_reply
            or SLOT_QUESTIONS.get(intent, {}).get(slot)
            or "Can you share a little more detail?"
        )

    @staticmethod
    def _low_confidence_reply(detection: IntentDetection) -> str:
        suggestions = [intent.value.replace("_", " ") for intent in detection.suggested_intents[:2]]
        if len(suggestions) >= 2:
            return f"I didn't fully understand. Did you mean {suggestions[0]} or {suggestions[1]}?"
        if suggestions:
            return f"I didn't fully understand. Did you mean {suggestions[0]}?"
        return "I didn't fully understand. Can you say that another way?"

    @staticmethod
    def _ready_reply(state: ConversationState, detection: IntentDetection) -> str:
        if state.active_intent == Intent.website_open:
            return detection.assistant_reply or "Opening the website now."
        readable_intent = state.active_intent.value.replace("_", " ")
        return (
            detection.assistant_reply
            or f"Great, I have the details for {readable_intent}. I can open the booking page now."
        )

    @staticmethod
    def _action_for_state(state: ConversationState) -> Optional[Dict[str, Any]]:
        if state.active_intent == Intent.website_open:
            url = str(state.slots.get("website_url") or "").strip()
            if not url:
                return None
            if not url.startswith(("http://", "https://")):
                if "." not in url:
                    url = f"{url}.com"
                url = f"https://{url}"
            return {"type": "open_url", "url": url}
        return ACTION_BY_INTENT.get(state.active_intent)

    @staticmethod
    def _payload(
        state: ConversationState,
        detection: IntentDetection,
        reply: str,
        next_question: Optional[str] = None,
        action: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "conversation_id": state.conversation_id,
            "intent": state.active_intent,
            "confidence": detection.confidence,
            "assistant_reply": reply,
            "status": state.status,
            "detected_language": state.detected_language,
            "slots": state.slots,
            "next_question": next_question,
            "action": action,
        }
