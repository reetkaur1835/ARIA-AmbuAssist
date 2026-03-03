"""
main.py — ARIA FastAPI Application
All routes: auth, chat, WebSocket STT, status queries.
"""
import os
import sys
import json
import asyncio
from contextlib import asynccontextmanager
from datetime import date

# Ensure backend/ is on the path when running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.setup import init_db
from auth.session import (
    authenticate_paramedic, create_session,
    get_current_paramedic, end_session,
)
from agents.graph import aria_graph
from agents.state import AgentState
from services.tts import text_to_speech_base64
from tools.db_tools import get_paramedic_status, get_upcoming_shifts, get_submissions_for_medic


# ─────────────────────────────────────────────
# LIFESPAN (startup / shutdown)
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✅ ARIA backend started")
    yield
    print("ARIA backend shutting down")


app = FastAPI(title="ARIA EMS Assistant", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory per-session conversation + form state (resets on server restart — fine for hackathon)
# session_id -> AgentState dict
session_states: dict[str, dict] = {}


def get_or_init_state(session_id: str, paramedic: dict) -> dict:
    if session_id not in session_states:
        session_states[session_id] = {
            "messages": [],
            "session_id": session_id,
            "paramedic": paramedic,
            "intent": None,
            "intent_summary": None,
            "active_form": None,
            "form_data": {},
            "required_fields": [],
            "missing_fields": [],
            "confidence_scores": {},
            "confirmation_pending": False,
            "confirmed": False,
            "submitted": False,
            "response_text": "",
            "display_data": None,
            "error": None,
        }
    else:
        # Keep paramedic profile fresh
        session_states[session_id]["paramedic"] = paramedic
    return session_states[session_id]


# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    pin: str

class LogoutRequest(BaseModel):
    session_id: str

class MeRequest(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ResetRequest(BaseModel):
    session_id: str


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.post("/auth/login")
async def login(req: LoginRequest):
    paramedic = authenticate_paramedic(req.username, req.pin)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Invalid username or PIN")
    session_id = create_session(paramedic)
    return {
        "session_id": session_id,
        "paramedic": {
            "username":     paramedic["username"],
            "first_name":   paramedic["first_name"],
            "last_name":    paramedic["last_name"],
            "badge_number": paramedic["badge_number"],
            "station":      paramedic["station"],
            "role":         paramedic["role"],
            "email":        paramedic["email"],
        }
    }


@app.post("/auth/logout")
async def logout(req: LogoutRequest):
    end_session(req.session_id)
    session_states.pop(req.session_id, None)
    return {"ok": True}


@app.post("/auth/me")
async def me(req: MeRequest):
    paramedic = get_current_paramedic(req.session_id)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Session not found")
    return {"paramedic": paramedic}


# ─────────────────────────────────────────────
# CHAT ROUTE
# ─────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    paramedic = get_current_paramedic(req.session_id)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Session not found or expired")

    state = get_or_init_state(req.session_id, paramedic)

    # Append user message
    state["messages"].append({"role": "user", "content": req.message})
    # Reset per-turn flags — prevent stale flow-control state from leaking into next turn
    state["submitted"] = False
    state["confirmed"] = False
    state["error"] = None

    # Run the graph
    try:
        result = await aria_graph.ainvoke(state)
    except Exception as e:
        error_msg = f"Something went wrong on my end. Try again? ({str(e)[:80]})"
        return {
            "response": error_msg,
            "audio_base64": "",
            "intent": state.get("intent"),
            "active_form": state.get("active_form"),
            "form_data": state.get("form_data", {}),
            "required_fields": state.get("required_fields", []),
            "missing_fields": state.get("missing_fields", []),
            "confirmation_pending": state.get("confirmation_pending", False),
            "submitted": False,
            "display_data": None,
        }

    # Merge result back into session state
    # Always update every key that came back from the graph
    for key, value in result.items():
        state[key] = value
    # Keep messages as the full accumulated list (LangGraph returns the full list)
    if "messages" in result:
        state["messages"] = result["messages"]

    response_text = result.get("response_text", "")

    # Generate TTS audio in parallel with building the response dict
    async def _tts(text: str) -> str:
        try:
            return await text_to_speech_base64(text)
        except Exception:
            return ""

    audio_base64 = await _tts(response_text) if response_text else ""

    return {
        "response":            response_text,
        "audio_base64":        audio_base64,
        "intent":              result.get("intent"),
        "active_form":         result.get("active_form"),
        "form_data":           result.get("form_data", {}),
        "required_fields":     result.get("required_fields", []),
        "missing_fields":      result.get("missing_fields", []),
        "confirmation_pending": result.get("confirmation_pending", False),
        "submitted":           result.get("submitted", False),
        "display_data":        result.get("display_data"),
    }


# ─────────────────────────────────────────────
# RESET ROUTE
# ─────────────────────────────────────────────

@app.post("/api/reset")
async def reset_state(req: ResetRequest):
    paramedic = get_current_paramedic(req.session_id)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Session not found")
    session_states.pop(req.session_id, None)
    return {"ok": True, "message": "Conversation state cleared"}


# ─────────────────────────────────────────────
# DATA QUERY ROUTES
# ─────────────────────────────────────────────

@app.post("/api/paramedic/status")
async def get_status(req: MeRequest):
    paramedic = get_current_paramedic(req.session_id)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Session not found")
    items = get_paramedic_status(paramedic["username"])
    return {"status_items": items}


@app.post("/api/shifts/upcoming")
async def get_upcoming(req: MeRequest):
    paramedic = get_current_paramedic(req.session_id)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Session not found")
    shifts = await get_upcoming_shifts(paramedic["username"], days_ahead=7)
    return {"shifts": shifts}


@app.post("/api/submissions")
async def get_submissions(req: MeRequest):
    paramedic = get_current_paramedic(req.session_id)
    if not paramedic:
        raise HTTPException(status_code=401, detail="Session not found")
    submissions = get_submissions_for_medic(paramedic["username"])
    return {"submissions": submissions}


# ─────────────────────────────────────────────
# WEBSOCKET — Deepgram STT Relay
# ─────────────────────────────────────────────

@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    paramedic = get_current_paramedic(session_id)
    if not paramedic:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    deepgram_connection = None
    final_transcript_parts: list[str] = []

    async def on_transcript(transcript: str, is_final: bool):
        if is_final:
            final_transcript_parts.append(transcript)
        await websocket.send_json({
            "type": "transcript",
            "text": transcript,
            "is_final": is_final,
        })

    async def on_error(error: str):
        await websocket.send_json({"type": "error", "message": error})

    try:
        from services.stt import create_live_connection
        deepgram_connection = await create_live_connection(on_transcript, on_error)

        while True:
            data = await websocket.receive()
            if "bytes" in data:
                # Forward raw audio bytes to Deepgram
                await deepgram_connection.send(data["bytes"])
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "stop":
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if deepgram_connection:
            try:
                await deepgram_connection.finish()
            except Exception:
                pass

        # If we have a final transcript, send it back for the client to POST to /api/chat
        full_transcript = " ".join(final_transcript_parts).strip()
        if full_transcript:
            try:
                await websocket.send_json({
                    "type": "final_transcript",
                    "text": full_transcript,
                })
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ARIA EMS Assistant",
        "version": "1.0.0",
    }


# ─────────────────────────────────────────────
# RUN (dev only)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
