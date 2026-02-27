# services/podcast/service.py
from datetime import datetime
from typing import Dict, Optional

from app.core.config import settings
from app.core.logger import logger

from .translation import translate_text
from .file_utils import save_script
from .audio import generate_audio


class PodcastService:
    def __init__(self):
        self.tts_url = "https://api.sarvam.ai/text-to-speech"
        self.sarvam_api_key = getattr(settings, 'SARVAM_API_KEY', None)

    async def generate_full_podcast(
        self,
        script: str,
        topic: str = "podcast",
        language: str = "hi",
        output_format: str = "mp3",
        translate_to_hindi: bool = True,
        speaker: Optional[str] = None,
    ) -> Dict:
        logger.info(f"Starting podcast generation: {topic}")

        # 1. Translate (optional)
        if translate_to_hindi:
            translated = await translate_text(
                script,
                source_lang="en-IN",
                target_lang="hi-IN"
            )
            if translated and translated != script:
                final_script = translated
                logger.info(f"Using translated script ({len(final_script)} chars)")
            else:
                logger.warning("Translation did not change text")

        # 2. Save script
        script_path = await save_script(final_script, topic)

        # 3. Generate audio → now in separate file
        audio_path = await generate_audio(
            script=final_script,
            sarvam_api_key=self.sarvam_api_key,
            tts_url=self.tts_url,
            language=language,
            output_format=output_format,
            speaker=speaker,
        )

        success = bool(script_path and audio_path)

        return {
            "script_path": script_path,
            "audio_path": audio_path,
            "success": success,
            "format": output_format,
            "language": language,
            "translated": translate_to_hindi and (final_script != script),
            "script_length": len(final_script),
            "timestamp": datetime.now().isoformat()
        }


podcast_service = PodcastService()