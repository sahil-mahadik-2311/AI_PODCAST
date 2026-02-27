# services/podcast/audio.py
import os
import base64
import io
from datetime import datetime
from typing import Optional, List

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from app.core.config import settings
from app.core.logger import logger

from .ffmpeg_check import PYDUB_AVAILABLE
from .script_splitting import split_script

try:
    from pydub import AudioSegment
except ImportError:
    # PYDUB_AVAILABLE is already handled by ffmpeg_check, but we need the import here for types if needed
    pass


async def combine_wav_chunks(chunks_bytes: List[bytes]) -> bytes:
    """
    Properly combine multiple WAV audio chunks using pydub.
    This ensures proper WAV header handling when combining chunks.
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
    Independent audio generation function.
    """
    if not HTTPX_AVAILABLE:
        logger.error("httpx is not installed. Cannot generate audio.")
        return None

    if not sarvam_api_key:
        logger.warning("Sarvam API key not provided. Cannot generate audio.")
        return None

    target_speaker = speaker or "anushka"
    logger.info(f"🎙️ Generating audio → speaker: {target_speaker} | format: {output_format}")

    try:
        # Split long script
        script_chunks = split_script(script, max_length=500)
        all_audio_chunks: List[bytes] = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, chunk in enumerate(script_chunks, 1):
                logger.debug(f"Processing chunk {i}/{len(script_chunks)}")

                payload = {
                    "inputs": [chunk],
                    "target_language_code": "hi-IN",
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
                    logger.error(f"Sarvam TTS failed: {resp.status_code} → {resp.text[:300]}")
                    return None

                data = resp.json()
                if "audios" not in data or not data["audios"]:
                    logger.error(f"No audio returned for chunk {i}")
                    return None

                chunk_bytes = base64.b64decode(data["audios"][0])
                all_audio_chunks.append(chunk_bytes)

        # Combine chunks
        if not all_audio_chunks:
            logger.error("No audio chunks received")
            return None

        if len(all_audio_chunks) == 1:
            audio_bytes = all_audio_chunks[0]
        else:
            logger.info(f"Combining {len(all_audio_chunks)} WAV chunks...")
            audio_bytes = await combine_wav_chunks(all_audio_chunks)

        if not audio_bytes:
            logger.error("Failed to combine audio chunks")
            return None

        # Optional MP3 conversion
        file_extension = "wav"
        if output_format.lower() == "mp3":
            logger.info("Converting to MP3...")
            audio_bytes = await convert_to_mp3(audio_bytes)
            file_extension = "mp3"

        # Save file
        filename = f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        filepath = os.path.join(audio_storage_path, filename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        size_mb = len(audio_bytes) / (1024 * 1024)
        logger.info(f"Audio saved → {filepath} ({size_mb:.2f} MB)")

        return f"/audio/{filename}"

    except Exception as e:
        logger.exception(f"Audio generation failed: {str(e)}")
        return None