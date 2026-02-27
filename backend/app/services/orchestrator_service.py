import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logger import logger
from app.services.unified_agent.service import unified_agent_service
from app.services.podcast.service import podcast_service

class OrchestratorService:
    async def generate_podcast(self, name: str, voice_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Main orchestration pipeline (Unified with Gemini Google Search and Hinglish).
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            # 1. Unified Research, Analysis, and Script Generation
            logger.info(f"Starting unified processing for {name} with date: {yesterday}")
            result = await unified_agent_service.process_podcast_request(
                target_date=yesterday,
                attribution=name
            )
            
            if not result.get("success"):
                logger.error(f"Unified agent failed: {result.get('error')}")
                return self._error_response(result.get("error", "Agent failed"), yesterday, name)

            # Save raw data for audit
            self._save_raw_data(result, yesterday)

            script = result.get("podcast_script", "")
            
            # 2. Complete Pipeline: Translate, Save Script, and Generate Audio
            logger.info("🚀 Starting full podcast pipeline (Translate -> Save -> Audio)...")
            podcast_result = await podcast_service.generate_full_podcast(
                script=script,
                topic=name or "podcast",
                speaker=voice_agent,
                translate_to_hindi=True
            )
            
            if not podcast_result.get("success"):
                logger.error("Podcast generation pipeline failed")
                return self._error_response("Audio generation failed", yesterday, name)
           
            return {
                "date": yesterday,
                "podcast_script": script,
                "audio_url": podcast_result.get("audio_path"),
                "attribution": result.get("attribution", name),
                "status": "success",
                "error": None
            }

        except Exception as e:
            logger.error(f"Orchestrator pipeline failed: {str(e)}")
            return self._error_response(str(e), yesterday, name)

    def _save_raw_data(self, data: Any, date_str: str):
        try:
            filename = f"raw_{date_str}_{datetime.now().strftime('%H%M%S')}.json"
            filepath = os.path.join(settings.RAW_DATA_STORAGE_PATH, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save raw data: {str(e)}")

    def _error_response(self, error_msg: str, date: str, topic: Optional[str]) -> Dict[str, Any]:
        return {
            "date": date,
            "podcast_script": "Error occurred during generation.",
            "audio_url": None,
            "status": "error",
            "error": error_msg
        }

orchestrator_service = OrchestratorService()