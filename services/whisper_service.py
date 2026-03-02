"""
OpenAI Whisper service for voice message transcription.
Handles Telegram's .ogg voice files and converts them to text.
Supports auto language detection (Arabic / English / mixed).
"""
import os
import logging
import tempfile

from openai import OpenAI

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

# Whisper supports up to 25 MB; Telegram voice messages are typically well below that.
MAX_FILE_SIZE_MB = 24


def transcribe_voice(audio_bytes: bytes, file_extension: str = "ogg") -> str:
    """
    Transcribe a voice message using OpenAI Whisper.

    Args:
        audio_bytes:    Raw bytes of the audio file.
        file_extension: File extension hint for Whisper (ogg, mp3, wav, m4a…).

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If the audio file exceeds the size limit.
        RuntimeError: If transcription fails.
    """
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"Audio file is {size_mb:.1f} MB — exceeds the {MAX_FILE_SIZE_MB} MB limit."
        )

    # Write to a temp file so the OpenAI SDK can detect the format
    suffix = f".{file_extension.lstrip('.')}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                # language=None lets Whisper auto-detect (supports Arabic, English, etc.)
            )
        text = transcript.text.strip()
        logger.info("Transcribed voice message (%d chars)", len(text))
        return text
    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        raise RuntimeError(f"Voice transcription failed: {exc}") from exc
    finally:
        os.unlink(tmp_path)
