from typing import Optional

try:
    from sarvamai import SarvamAI
    SARVAM_AVAILABLE = True
except ImportError:
    SARVAM_AVAILABLE = False

from app.core.config import settings
from app.core.logger import logger


async def translate_text(
    text: str,
    source_lang: str = "en-IN",
    target_lang: str = "hi-IN"
) -> Optional[str]:
    """
    Translates text using Sarvam AI Translate API.
    Returns original text if translation fails or library is missing.
    """
    if not SARVAM_AVAILABLE:
        logger.warning("sarvamai library not installed. Skipping translation.")
        return text

    sarvam_api_key = getattr(settings, 'SARVAM_API_KEY', None)
    if not sarvam_api_key:
        logger.warning("Sarvam API key not configured. Skipping translation.")
        return text

    logger.info(f"🌐 Translating script from {source_lang} to {target_lang}...")

    try:
        client = SarvamAI(api_subscription_key=sarvam_api_key)

        response = client.text.translate(
            input=text,
            source_language_code=source_lang,
            target_language_code=target_lang,
            mode="formal",
            model="mayura:v1",
            numerals_format="native"
        )

        if response and hasattr(response, 'translated_text'):
            translated = response.translated_text
        elif isinstance(response, dict) and 'translated_text' in response:
            translated = response['translated_text']
        else:
            logger.warning(f"Unexpected translation response format: {response}")
            return text

        logger.info(f"✓ Translation successful ({len(translated)} characters)")
        logger.info(f"Translated text preview: {translated[:200]}...")
        return translated

    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        logger.warning("Proceeding with original English text")
        return text