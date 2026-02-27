# services/podcast/audio.py
import os
import base64
import io
from datetime import datetime
from typing import Optional, List, Dict

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from app.core.config import settings
from app.core.logger import logger

from .ffmpeg_check import PYDUB_AVAILABLE
from .script_splitting import split_podcast_scripts, get_script_chunk

try:
    from pydub import AudioSegment
except ImportError:
    # PYDUB_AVAILABLE is already handled by ffmpeg_check, but we need the import here for types if needed
    pass


async def combine_wav_chunks(chunks_bytes: List[bytes]) -> bytes:
    """
    Properly combine multiple WAV audio chunks using pydub.
    This ensures proper WAV header handling when combining chunks.
    
    Args:
        chunks_bytes: List of WAV audio bytes to combine
    
    Returns:
        Combined WAV audio bytes
    """
    if not PYDUB_AVAILABLE:
        logger.warning("pydub not available. Returning first chunk only.")
        return chunks_bytes[0] if chunks_bytes else b""

    try:
        combined_audio = AudioSegment.empty()

        for idx, chunk in enumerate(chunks_bytes, 1):
            try:
                audio_segment = AudioSegment.from_wav(io.BytesIO(chunk))
                combined_audio += audio_segment
                logger.debug(f"Combined chunk {idx} ({len(audio_segment)} ms audio)")
            except Exception as e:
                logger.error(f"Error processing chunk {idx}: {str(e)}")
                continue

        if not combined_audio:
            logger.error("No audio chunks could be combined")
            return chunks_bytes[0] if chunks_bytes else b""

        # Export combined audio back to WAV
        wav_buffer = io.BytesIO()
        combined_audio.export(wav_buffer, format="wav")
        return wav_buffer.getvalue()

    except Exception as e:
        logger.error(f"Failed to combine WAV chunks: {str(e)}")
        return chunks_bytes[0] if chunks_bytes else b""


async def convert_to_mp3(audio_bytes: bytes) -> bytes:
    """
    Convert audio bytes from WAV to MP3 format.
    
    Args:
        audio_bytes: WAV audio bytes
    
    Returns:
        MP3 audio bytes
    """
    if not PYDUB_AVAILABLE:
        logger.warning("pydub not available. Returning original WAV format.")
        return audio_bytes

    try:
        audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))

        mp3_buffer = io.BytesIO()
        audio.export(
            mp3_buffer,
            format="mp3",
            bitrate="192k",
            parameters=["-q:a", "2"]
        )

        return mp3_buffer.getvalue()

    except Exception as e:
        logger.error(f"MP3 conversion failed: {str(e)}")
        return audio_bytes


async def generate_audio_from_script(
    script: str,
    sarvam_api_key: str,
    tts_url: str,
    language: str = "hi",
    output_format: str = "mp3",
    speaker: Optional[str] = None,
    audio_storage_path: str = settings.AUDIO_STORAGE_PATH,
) -> Optional[str]:
    """
    Generate audio from a SINGLE script using Sarvam TTS.
    Splits script into chunks (max 500 chars) and processes each separately.
    Combines all audio chunks into one file.
    
    Args:
        script: Text script to convert to audio
        sarvam_api_key: Sarvam API authentication key
        tts_url: Sarvam TTS API endpoint URL
        language: Target language code ("hi" for Hindi, "en" for English)
        output_format: Output audio format ("mp3" or "wav")
        speaker: Speaker name (default: "anushka")
        audio_storage_path: Path to save audio files
    
    Returns:
        Path to generated audio file, or None if failed
    """
    if not HTTPX_AVAILABLE:
        logger.error("httpx is not installed. Cannot generate audio.")
        return None

    if not sarvam_api_key:
        logger.warning("Sarvam API key not provided. Cannot generate audio.")
        return None

    target_speaker = speaker or "anushka"
    logger.info(f"🎙️ Generating audio from script → language: {language} | speaker: {target_speaker} | format: {output_format}")

    try:
        # Split script into SEPARATE chunks (max 500 chars each)
        from .script_splitting import split_script
        script_chunks = split_script(script, max_length=500, language=language)
        
        logger.info(f"Script split into {len(script_chunks)} SEPARATE chunks for Sarvam TTS")
        all_audio_chunks: List[bytes] = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, chunk in enumerate(script_chunks, 1):
                logger.info(f"Processing chunk {i}/{len(script_chunks)} ({len(chunk)} chars)")

                # Map language code
                lang_code = "hi-IN" if language == "hi" else "en-IN"

                payload = {
                    "inputs": [chunk],
                    "target_language_code": lang_code,
                    "speaker": target_speaker,
                    "pitch": 1.0,
                    "pace": 1.0,
                    "loudness": 1.5
                }

                headers = {
                    "Authorization": f"Bearer {sarvam_api_key}",
                    "Content-Type": "application/json"
                }

                resp = await client.post(
                    tts_url,
                    json=payload,
                    headers=headers,
                    timeout=60.0
                )

                if resp.status_code != 200:
                    logger.error(f"Sarvam TTS failed for chunk {i}: {resp.status_code} → {resp.text[:300]}")
                    return None

                data = resp.json()
                if "audios" not in data or not data["audios"]:
                    logger.error(f"No audio returned for chunk {i}")
                    return None

                chunk_bytes = base64.b64decode(data["audios"][0])
                all_audio_chunks.append(chunk_bytes)
                logger.debug(f"✓ Chunk {i} audio received ({len(chunk_bytes)} bytes)")

        # Combine all audio chunks
        if not all_audio_chunks:
            logger.error("No audio chunks received")
            return None

        if len(all_audio_chunks) == 1:
            logger.info("Single audio chunk - no combining needed")
            audio_bytes = all_audio_chunks[0]
        else:
            logger.info(f"Combining {len(all_audio_chunks)} audio chunks into one file...")
            audio_bytes = await combine_wav_chunks(all_audio_chunks)

        if not audio_bytes:
            logger.error("Failed to combine audio chunks")
            return None

        # Optional MP3 conversion
        file_extension = "wav"
        if output_format.lower() == "mp3":
            logger.info("Converting WAV to MP3...")
            audio_bytes = await convert_to_mp3(audio_bytes)
            file_extension = "mp3"

        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"podcast_{language}_{timestamp}.{file_extension}"
        filepath = os.path.join(audio_storage_path, filename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        size_mb = len(audio_bytes) / (1024 * 1024)
        logger.info(f"✓ Audio saved → {filepath} ({size_mb:.2f} MB)")

        return f"/audio/{filename}"

    except Exception as e:
        logger.exception(f"Audio generation failed: {str(e)}")
        return None


async def generate_podcast_audio(
    eng_script: str,
    hin_script: str,
    sarvam_api_key: str,
    tts_url: str,
    output_format: str = "mp3",
    eng_speaker: Optional[str] = None,
    hin_speaker: Optional[str] = None,
    audio_storage_path: str = settings.AUDIO_STORAGE_PATH,
) -> Optional[Dict[str, str]]:
    """
    Generate AUDIO for TWO separate podcast scripts (English and Hindi).
    Each script is split into chunks and processed separately with Sarvam TTS.
    
    IMPORTANT: Does NOT merge scripts. Processes each script independently:
    - English script chunks → English audio file
    - Hindi script chunks → Hindi audio file
    
    Args:
        eng_script: English podcast script
        hin_script: Hindi podcast script
        sarvam_api_key: Sarvam API authentication key
        tts_url: Sarvam TTS API endpoint URL
        output_format: Output audio format ("mp3" or "wav")
        eng_speaker: English speaker name (e.g., "sachit")
        hin_speaker: Hindi speaker name (e.g., "anushka")
        audio_storage_path: Path to save audio files
    
    Returns:
        Dictionary with audio file paths:
        {
            "eng_pod_audio": "/audio/podcast_en_20260226_120000.mp3",
            "hin_pod_audio": "/audio/podcast_hi_20260226_120000.mp3",
            "success": True
        }
        Or None if generation fails
    
    Example:
        result = await generate_podcast_audio(
            eng_script=eng_script,
            hin_script=hin_script,
            sarvam_api_key="your_key",
            tts_url="https://api.sarvam.ai/text-to-speech",
            output_format="mp3"
        )
        
        if result:
            print(f"English audio: {result['eng_pod_audio']}")
            print(f"Hindi audio: {result['hin_pod_audio']}")
    """
    logger.info("=" * 70)
    logger.info("GENERATING PODCAST AUDIO - ENGLISH AND HINDI")
    logger.info("=" * 70)
    
    if not HTTPX_AVAILABLE:
        logger.error("httpx is not installed. Cannot generate audio.")
        return None

    if not sarvam_api_key:
        logger.warning("Sarvam API key not provided. Cannot generate audio.")
        return None

    eng_speaker = eng_speaker or "sachit"
    hin_speaker = hin_speaker or "anushka"

    try:
        # Generate English audio
        logger.info("\n[1/2] GENERATING ENGLISH PODCAST AUDIO (eng_pod)")
        logger.info("-" * 70)
        eng_audio_path = await generate_audio_from_script(
            script=eng_script,
            sarvam_api_key=sarvam_api_key,
            tts_url=tts_url,
            language="en",
            output_format=output_format,
            speaker=eng_speaker,
            audio_storage_path=audio_storage_path
        )

        if not eng_audio_path:
            logger.error("Failed to generate English audio")
            return None

        # Generate Hindi audio
        logger.info("\n[2/2] GENERATING HINDI PODCAST AUDIO (hin_pod)")
        logger.info("-" * 70)
        hin_audio_path = await generate_audio_from_script(
            script=hin_script,
            sarvam_api_key=sarvam_api_key,
            tts_url=tts_url,
            language="hi",
            output_format=output_format,
            speaker=hin_speaker,
            audio_storage_path=audio_storage_path
        )

        if not hin_audio_path:
            logger.error("Failed to generate Hindi audio")
            return None

        result = {
            "eng_pod_audio": eng_audio_path,
            "hin_pod_audio": hin_audio_path,
            "success": True,
            "format": output_format
        }

        logger.info("\n" + "=" * 70)
        logger.info("✓ PODCAST AUDIO GENERATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"English audio: {eng_audio_path}")
        logger.info(f"Hindi audio: {hin_audio_path}")
        logger.info("=" * 70 + "\n")

        return result

    except Exception as e:
        logger.exception(f"Podcast audio generation failed: {str(e)}")
        return None


async def generate_audio(
    script: str,
    sarvam_api_key: str,
    tts_url: str,
    language: str = "hi",
    output_format: str = "mp3",
    speaker: Optional[str] = None,
    audio_storage_path: str = settings.AUDIO_STORAGE_PATH,
) -> Optional[str]:
    """
    Legacy function for backward compatibility.
    Use generate_audio_from_script() for new code.
    
    This function processes a SINGLE script.
    For TWO scripts, use generate_podcast_audio() instead.
    """
    logger.warning("generate_audio() is deprecated. Use generate_audio_from_script() or generate_podcast_audio()")
    
    return await generate_audio_from_script(
        script=script,
        sarvam_api_key=sarvam_api_key,
        tts_url=tts_url,
        language=language,
        output_format=output_format,
        speaker=speaker,
        audio_storage_path=audio_storage_path
    )