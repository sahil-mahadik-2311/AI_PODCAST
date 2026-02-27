import re
from typing import List

from app.core.logger import logger


def split_script(script: str, max_length: int = 500) -> List[str]:
    """
    Split long script into chunks of max_length characters.
    Splits at sentence boundaries (. ! ?) to keep sentences intact.
    """
    if len(script) <= max_length:
        logger.info(f"Script length: {len(script)} chars (within limit)")
        return [script]

    logger.info(f"Script length: {len(script)} chars - splitting into chunks of max {max_length} chars")

    chunks = []
    current_chunk = ""

    # Split by sentence delimiters, keeping the delimiter
    sentences = re.split(r'(?<=[.!?])\s+', script)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_chunk and len(current_chunk) + len(sentence) + 1 > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    logger.info(f"✅ Split into {len(chunks)} chunks:")
    for idx, chunk in enumerate(chunks, 1):
        logger.info(f"   Chunk {idx}: {len(chunk)} characters")

    return chunks