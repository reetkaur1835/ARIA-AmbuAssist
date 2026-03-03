from langchain_openai import ChatOpenAI
import os


def get_llm(model: str = "openai/gpt-4o-mini", temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", "placeholder"),
        model=model,
        temperature=temperature,
        model_kwargs={
            "extra_headers": {
                "HTTP-Referer": "https://aria-ems.local",
                "X-Title": "ARIA EMS Assistant",
            }
        },
    )


# Lazy singletons — created on first access so missing API key only fails at runtime, not import
_routing_llm    = None
_extraction_llm = None
_voice_llm      = None


def _get_routing_llm() -> ChatOpenAI:
    global _routing_llm
    if _routing_llm is None:
        _routing_llm = get_llm("openai/gpt-4o-mini", temperature=0.1)
    return _routing_llm


def _get_extraction_llm() -> ChatOpenAI:
    global _extraction_llm
    if _extraction_llm is None:
        _extraction_llm = get_llm("openai/gpt-4o-mini", temperature=0.2)
    return _extraction_llm


def _get_voice_llm() -> ChatOpenAI:
    global _voice_llm
    if _voice_llm is None:
        _voice_llm = get_llm("google/gemini-2.0-flash-lite-001", temperature=0.7)
    return _voice_llm


# Module-level names for import compatibility — these are callables, not instances
ROUTING_LLM    = property(_get_routing_llm)
EXTRACTION_LLM = property(_get_extraction_llm)
VOICE_LLM      = property(_get_voice_llm)


# Preferred usage: call these functions directly
def get_routing_llm()    -> ChatOpenAI: return _get_routing_llm()
def get_extraction_llm() -> ChatOpenAI: return _get_extraction_llm()
def get_voice_llm()      -> ChatOpenAI: return _get_voice_llm()
