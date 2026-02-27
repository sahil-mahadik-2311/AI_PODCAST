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
) -> Optional[dict]:
    """
    Execute the agent using Runner and collect the final text response.
    Splits the response into two separate files: eng_pod (English) and hin_pod (Hindi).
    Returns a dictionary with both scripts.
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
        
        # Split the response into English and Hindi scripts
        scripts = split_podcast_scripts(final_response.strip())
        
        if not scripts:
            logger.error("Failed to split response into English and Hindi scripts")
            return None
        
        logger.info(f"Successfully split into eng_pod ({len(scripts['eng_pod'])} chars) and hin_pod ({len(scripts['hin_pod'])} chars)")
        return scripts

    except Exception as e:
        logger.error(f"Runner execution failed: {str(e)}", exc_info=True)
        return None


def split_podcast_scripts(full_response: str) -> Optional[dict]:
    """
    Split the agent response into two separate podcast scripts: English and Hindi.
    
    Expected format:
    =====ENGLISH PODCAST SCRIPT=====
    [English content]
    
    =====HINDI PODCAST SCRIPT=====
    [Hindi content]
    
    Returns:
        dict with 'eng_pod' and 'hin_pod' keys, or None if split fails
    """
    try:
        # Define markers for English and Hindi sections
        eng_marker_start = "=====ENGLISH PODCAST SCRIPT====="
        hin_marker_start = "=====HINDI PODCAST SCRIPT====="
        
        # Find the positions of markers
        eng_start_idx = full_response.find(eng_marker_start)
        hin_start_idx = full_response.find(hin_marker_start)
        
        if eng_start_idx == -1 or hin_start_idx == -1:
            logger.error("Could not find both English and Hindi script markers in response")
            return None
        
        # Extract English script (from marker to before Hindi marker)
        eng_script = full_response[
            eng_start_idx + len(eng_marker_start):hin_start_idx
        ].strip()
        
        # Extract Hindi script (from marker to end)
        hin_script = full_response[
            hin_start_idx + len(hin_marker_start):
        ].strip()
        
        # Remove "IMPORTANT:" note if present at the end of English script
        if "IMPORTANT:" in eng_script:
            eng_script = eng_script[:eng_script.find("IMPORTANT:")].strip()
        
        # Validate both scripts have content
        if not eng_script or not hin_script:
            logger.error("One or both scripts are empty after splitting")
            return None
        
        logger.info("Successfully split podcast scripts into eng_pod and hin_pod")
        
        return {
            "eng_pod": eng_script,
            "hin_pod": hin_script
        }
    
    except Exception as e:
        logger.error(f"Failed to split podcast scripts: {str(e)}", exc_info=True)
        return None