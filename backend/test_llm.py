import asyncio, os, sys, logging
logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, '.')

# Load .env
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

print('API KEY prefix:', os.environ.get('OPENROUTER_API_KEY', 'MISSING')[:20])

from services.llm import get_voice_llm
from services.llm_utils import call_llm_json

async def test():
    try:
        result = await call_llm_json(
            get_voice_llm(),
            'You are ARIA. Respond ONLY with valid JSON: {"response": "your answer"}',
            'Hello, how can you help me?'
        )
        print('SUCCESS:', result)
    except Exception as e:
        print('FAILED:', type(e).__name__, str(e)[:500])

asyncio.run(test())
