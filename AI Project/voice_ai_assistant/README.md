# VoxAI Conversational Voice Assistant

Run:

```powershell
$env:OPENAI_API_KEY="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
python -m uvicorn voice_ai_assistant.main:app --reload --host 127.0.0.1 --port 8000
```

You can also place `OPENAI_API_KEY=your_key_here` in the project `.env` file.

Request:

```json
{
  "message": "I want to watch a movie tonight",
  "conversation_id": null
}
```

Example flow:

1. User: `I want to watch a movie`
   Response intent: `movie_booking`, asks: `Sure, which city should I search in?`
2. User: `Bangalore`
   Response keeps `movie_booking`, stores `city=Bangalore`, asks genre.
3. User: `Action`
   Response stores genre and asks date/time.
4. User: `Tonight`
   Response status becomes `ready` and returns a BookMyShow action.

Low confidence example:

User: `I need something for tonight`

Response:

```json
{
  "intent": "unknown",
  "confidence": 0.42,
  "assistant_reply": "I didn't fully understand. Did you mean movie booking or hotel booking?"
}
```
