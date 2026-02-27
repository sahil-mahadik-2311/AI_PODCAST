from typing import Dict, Any, Optional

from app.core.logger import logger

from .agent_init import initialize_agent, ADK_AVAILABLE
from .prompt_builder import build_podcast_prompt
from .runner_execution import run_agent_and_get_script
from .script_cleaner import clean_generated_script
from .error_handling import error_response


class UnifiedAgentService:
    def __init__(self):
        self.agent = None
        self.session_service = None
        self.app_name = "podcast_agent"

        if ADK_AVAILABLE:
            self.agent, self.session_service, success = initialize_agent()
            if not success:
                logger.error("UnifiedAgentService failed to initialize properly")

    async def process_podcast_request(
        self,
        target_date: Optional[str] = None,
        attribution: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: generate financial podcast script using Google ADK agent.
        """
        target_date = target_date or "yesterday"
        attribution = attribution or "Financial Research Team"

        if not self.agent or not self.session_service:
            return error_response("Agent or session service not initialized")

        try:
            logger.info(f"Starting podcast script generation for date: {target_date}")

            prompt = build_podcast_prompt(target_date, attribution)

            raw_response = await run_agent_and_get_script(
                agent=self.agent,
                session_service=self.session_service,
                prompt=prompt,
                app_name=self.app_name
            )

            if not raw_response:
                return error_response("No valid response received from agent")

            cleaned_script = clean_generated_script(raw_response)

            if len(cleaned_script) < 300:
                logger.warning(f"Generated script too short: {len(cleaned_script)} chars")
                return error_response(f"Script too short ({len(cleaned_script)} chars)")

            logger.info(f"✓ Final podcast script ready — {len(cleaned_script)} characters")

            return {
                "podcast_script": cleaned_script,
                "success": True,
                "attribution": attribution,
                "date": target_date,
                "script_length": len(cleaned_script)
            }

        except Exception as e:
            logger.error(f"Critical error in podcast generation: {str(e)}", exc_info=True)
            return error_response(str(e))


# Global instance
unified_agent_service = UnifiedAgentService()