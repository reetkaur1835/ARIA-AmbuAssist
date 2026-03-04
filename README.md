# 🚑 ARIA — AmbuAssist

**Ambulance Response Intelligence Assistant**

ARIA is a voice-first AI assistant built for paramedics and EMS personnel. It handles administrative tasks hands-free — so crews can stay focused on patient care.

---

## Features

| Capability | Description |
|---|---|
| 🗓 **Schedule Lookup** | Check your shift, your partner, or your station's schedule |
| 📋 **Compliance Status** | View outstanding certifications, ACR completions, and checklist items |
| ✅ **Checklist Updates** | Mark items as resolved by voice |
| 📝 **Occurrence Reports** | File EMS occurrence reports via conversation — auto-emailed on completion |
| 🧸 **Teddy Bear Program** | Request comfort bears for patients — form generated and sent automatically |
| 🔄 **Shift Change Requests** | Submit shift swap or day-off requests by voice |
| 🌤 **Weather** | Get a weather briefing relevant to EMS operations |

---

## Architecture

```
Voice Input (Deepgram STT)
        ↓
  FastAPI Backend
        ↓
  LangGraph Agent Graph
  ├── Delegator (gpt-4o-mini) — classifies intent
  ├── Schedule Agent
  ├── Checklist Agent
  ├── Occurrence Report Agent
  ├── Teddy Bear Agent
  ├── Shift Change Agent
  └── General / Weather Agent
        ↓
  Voice Response (ElevenLabs TTS)
```

---

## Tech Stack

- **Backend** — Python, FastAPI, LangGraph
- **LLMs** — OpenRouter (`gpt-4o-mini` for routing/extraction, `gemini-2.0-flash-lite` for responses)
- **STT** — Deepgram (WebSocket live transcription)
- **TTS** — ElevenLabs (`eleven_flash_v2_5`)
- **Email** — SendGrid
- **Database** — SQLite

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/ARIA-AmbuAssist.git
cd ARIA-AmbuAssist
```

### 2. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example backend/.env
# Fill in your API keys in backend/.env
```

### 4. Set up the database
```bash
cd backend
python database/setup.py
python database/seed_db.py
```

### 5. Run the backend
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 6. Run the frontend (Vite)
```bash
cd frontend
npm install
npm run dev -- --host
```

The Vite dev server listens on `http://localhost:5173/` and will also expose your LAN IP when launched with `--host`, which is handy for testing on tablets in the bay. The React client assumes the FastAPI backend is on `http://localhost:8000`; update `frontend/src/api/client.js` if you proxy requests elsewhere.

---

## Environment Variables

See `.env.example` for all required keys:

| Variable | Service |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter (LLM access) |
| `DEEPGRAM_API_KEY` | Deepgram (STT) |
| `ELEVENLABS_API_KEY` | ElevenLabs (TTS) |
| `SENDGRID_API_KEY` | SendGrid (email) |
| `OPENWEATHER_API_KEY` | OpenWeatherMap |

---

## Streaming Latency Model

`POST /api/chat` replies as a **Server-Sent Events (SSE)** stream. Every turn emits:

1. **Speculative chunk** — instant filler phrase generated locally (e.g., “Hang tight while I peek at scheduling…”). Its TTS audio is synthesized immediately and flushed so the UI can play it under 500 ms.
2. **Final chunk** — streamed after LangGraph produces the answer. Contains the full response, structured data (`display_data`, `form_data`, etc.), and the final TTS audio.

Client integration tips:
- Use `fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({...}) })` and parse `data: { ... }` events from the response stream.
- Handle `type: "speculative"`, `type: "final"`, and `type: "error"` events separately.
- Audio arrives Base64-encoded per chunk; render or play it as each event lands—no extra polling endpoints needed.

This architecture keeps perceived latency low while the heavier LLM turn finishes in the background.

---

## Project Structure

```
ARIA-AmbuAssist/
├── backend/
│   ├── main.py              # FastAPI app + SSE /api/chat endpoint
│   ├── agents/              # LangGraph nodes + routing logic
│   ├── services/            # LLM, TTS, STT clients
│   ├── forms/               # Email rendering + sending logic
│   ├── tools/               # DB helpers + weather tool
│   ├── auth/                # Session management helpers
│   └── database/            # Schema + migrations + seed data
├── frontend/
│   ├── src/
│   │   ├── main.jsx         # Vite entry; mounts providers + <App />
│   │   ├── App.jsx          # Layout shell (panels + providers)
│   │   ├── api/
│   │   │   └── client.js    # `chatStream()` SSE fetch helper
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx    # Streams SSE, renders/speculative audio
│   │   │   ├── LeftPanel.jsx    # User/session metadata
│   │   │   ├── RightPanel.jsx   # Forms + structured data display
│   │   │   ├── ModeToggle.jsx   # Theme switcher
│   │   │   └── ui/              # Reusable primitives (Button, Card, etc.)
│   │   ├── store/
│   │   │   └── useStore.js  # Zustand store tracking chat + audio queue
│   │   ├── utils/
│   │   │   └── audio.js     # Web Audio helpers (decode, queue playback)
│   │   └── lib/
│   │       └── utils.js     # Tailwind/class helpers
│   ├── public/
│   │   └── pcm-processor.js # AudioWorklet for PCM streaming
│   ├── App.css / index.css  # Global styles + layout tokens
│   ├── package.json         # Frontend deps + scripts
│   ├── vite.config.js       # Dev server + proxy tuning
│   └── README.md            # Frontend-specific notes
├── .env.example
└── README.md
```

---

*Built for EMS teams. Designed to stay out of the way.*
