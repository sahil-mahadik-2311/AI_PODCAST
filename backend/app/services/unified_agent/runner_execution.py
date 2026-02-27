import hashlib
from typing import Optional

try:
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from google.adk.runners import Runner
    ADK_RUNNER_AVAILABLE = True
except ImportError:
    ADK_RUNNER_AVAILABLE = False

from app.core.logger import logger


async def run_agent_and_get_script(
    agent,
    session_service,
    prompt: str,
    app_name: str = "podcast_agent"
) -> Optional[str]:
    """
    Execute the agent using Runner and collect the final text response.
    """
    if not GENAI_AVAILABLE or not ADK_RUNNER_AVAILABLE:
        logger.error("Google GenAI or ADK Runner not installed. Cannot execute agent.")
        return None

    try:
        user_id = f"user_{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
        session_id = f"session_{hashlib.md5(prompt.encode()).hexdigest()[:10]}"

        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )

        user_content = types.Content(
            role='user',
            parts=[types.Part(text=prompt)]
        )

        final_response = None
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break

        if not final_response:
            logger.error("Agent returned no final response text")
            return None

        logger.info(f"Agent response received — length: {len(final_response)} chars")
        return final_response.strip()

    except Exception as e:
        logger.error(f"Runner execution failed: {str(e)}", exc_info=True)
        return None