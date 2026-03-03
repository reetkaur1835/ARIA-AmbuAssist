from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging

logger = logging.getLogger(__name__)


async def call_llm_json(llm, system_prompt: str, user_input: str) -> dict:
    """
    Call an LLM and parse the response as JSON.
    Handles markdown code block wrappers gracefully.
    """
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input)
        ])
    except Exception as e:
        logger.error(f"[LLM] ainvoke failed: {type(e).__name__}: {e}")
        raise

    raw = response.content
    logger.debug(f"[LLM] raw response: {raw[:200]}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Strip markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            # drop first and last fence lines
            clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(f"[LLM] JSON parse failed. Raw: {raw[:300]}")
            raise
