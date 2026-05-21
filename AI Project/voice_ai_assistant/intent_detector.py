import json
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv

from voice_ai_assistant.models import Intent, IntentDetection
from voice_ai_assistant.prompts import (
    INTENT_DETECTION_SYSTEM_PROMPT,
    build_intent_prompt,
)
from voice_ai_assistant.state import summarize_state


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

load_dotenv()

SLOT_KEYS = [
    "city",
    "genre",
    "date_or_time",
    "check_in",
    "check_out",
    "guests",
    "food_or_restaurant",
    "delivery_location",
    "pickup_location",
    "drop_location",
    "booking_type",
    "booking_id_or_name",
    "website_url",
]


INTENT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {"type": "string", "enum": [intent.value for intent in Intent]},
        "confidence": {"type": "number"},
        "detected_language": {"type": "string"},
        "user_goal": {"type": "string"},
        "extracted_slots": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                key: {"type": ["string", "number", "null"]} for key in SLOT_KEYS
            },
            "required": SLOT_KEYS,
        },
        "missing_slots": {"type": "array", "items": {"type": "string"}},
        "suggested_intents": {
            "type": "array",
            "items": {"type": "string", "enum": [intent.value for intent in Intent]},
        },
        "assistant_reply": {"type": "string"},
    },
    "required": [
        "intent",
        "confidence",
        "detected_language",
        "user_goal",
        "extracted_slots",
        "missing_slots",
        "suggested_intents",
        "assistant_reply",
    ],
}


class IntentDetector:
    """AI intent classifier using OpenAI Structured Outputs.

    This class intentionally does not contain keyword routing. All semantic
    classification is delegated to the model and validated against a schema.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", model)

    def detect(self, message: str, state) -> IntentDetection:
        if not self.api_key:
            return IntentDetection(
                intent=Intent.unknown,
                confidence=0.0,
                assistant_reply=(
                    "AI intent detection is not configured. Please set OPENAI_API_KEY."
                ),
            )

        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": INTENT_DETECTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_intent_prompt(message, summarize_state(state)),
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "intent_detection",
                    "strict": True,
                    "schema": INTENT_SCHEMA,
                }
            },
        }

        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        raw_text = self._extract_output_text(data)
        parsed = json.loads(raw_text)
        return IntentDetection(**parsed)

    @staticmethod
    def _extract_output_text(data: Dict[str, Any]) -> str:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "")
        if "output_text" in data:
            return data["output_text"]
        raise ValueError("OpenAI response did not include output text")
