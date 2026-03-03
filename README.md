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

## Project Structure

```
ARIA-AmbuAssist/
├── backend/
│   ├── main.py              # FastAPI app + all routes
│   ├── agents/              # LangGraph agent nodes
│   │   ├── delegator.py     # Intent classifier / router
│   │   ├── schedule_agent.py
│   │   ├── checklist_agent.py
│   │   ├── occurrence_agent.py
│   │   ├── teddy_bear_agent.py
│   │   ├── general_agent.py
│   │   └── graph.py         # LangGraph StateGraph definition
│   ├── services/            # LLM, TTS, STT clients
│   ├── forms/               # Email rendering + sending
│   ├── tools/               # DB tools, weather tool
│   ├── auth/                # Session management
│   └── database/            # Schema + seed data
├── .env.example
└── README.md
```

---

*Built for EMS teams. Designed to stay out of the way.*
