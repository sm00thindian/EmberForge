"""
EmberForge Companion - Phase 0: Digital Brain
FastAPI backend with Ember agent (text chat + voice upload ready)

Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import os
from datetime import datetime

app = FastAPI(
    title="EmberForge Companion - Phase 0",
    description="The digital brain for EmberForge. Text + voice-ready endpoints.",
    version="0.1.0"
)

# ==================== CONFIGURATION ====================
# IMPORTANT: Add your xAI / Grok API key here or via environment variable
GROK_API_KEY = os.getenv("GROK_API_KEY", "YOUR_XAI_API_KEY_HERE")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# Load the core Ember system prompt
with open("../prompts/ember_agent_prompt.md", "r") as f:
    EMBER_SYSTEM_PROMPT = f.read()

class ChatRequest(BaseModel):
    message: str
    mode: str = "warm"          # "warm" | "grumpy_artist" | "creative"
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    mode: str

@app.get("/")
async def root():
    return {
        "message": "EmberForge Phase 0 - Digital Brain is running",
        "status": "healthy",
        "endpoints": {
            "/chat": "Text conversation with Ember",
            "/voice": "Upload audio file for voice interaction (future)",
            "/health": "Health check"
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ember(request: ChatRequest):
    """
    Main conversation endpoint with Ember.
    The system prompt gives Ember its personality, creative depth, and maker wisdom.
    """
    if not GROK_API_KEY or GROK_API_KEY == "YOUR_XAI_API_KEY_HERE":
        raise HTTPException(
            status_code=500,
            detail="GROK_API_KEY not set. Please set the environment variable or update main.py"
        )

    # Build the messages for Grok
    messages = [
        {"role": "system", "content": EMBER_SYSTEM_PROMPT},
        {"role": "user", "content": request.message}
    ]

    # Optional: Adjust prompt slightly based on mode
    if request.mode == "grumpy_artist":
        messages[0]["content"] += "\n\nThe user has requested 'grumpy artist' mode. Be more direct, no-nonsense, and focused on craft. Less fluff, more honest feedback."
    elif request.mode == "creative":
        messages[0]["content"] += "\n\nFocus heavily on creative and musical collaboration. Offer raw, honest feedback on lyrics and ideas."

    payload = {
        "model": "grok-3-latest",   # or whichever Grok model you have access to
        "messages": messages,
        "temperature": request.temperature,
        "max_tokens": 1200
    }

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(GROK_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        ember_reply = data["choices"][0]["message"]["content"].strip()

        return ChatResponse(
            response=ember_reply,
            timestamp=datetime.now().isoformat(),
            mode=request.mode
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Grok API: {str(e)}")

@app.post("/voice")
async def voice_chat(audio: UploadFile = File(...)):
    """
    Placeholder for future voice interaction.
    Currently accepts audio file upload and returns metadata.
    In Milestone 2 we will add local Whisper transcription here.
    """
    return JSONResponse({
        "status": "received",
        "filename": audio.filename,
        "content_type": audio.content_type,
        "message": "Voice endpoint ready. Transcription + Ember response will be added in the next iteration."
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
