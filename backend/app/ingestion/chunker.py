import re
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class TextChunk:
    content: str
    chunk_index: int


def clean_text(text: str) -> str:
    """Normalize whitespace and remove junk characters."""
    text = re.sub(r"\s+", " ", text)           # Collapse whitespace
    text = re.sub(r"[^\x00-\x7F]+", " ", text) # Remove non-ASCII
    text = text.strip()
    return text


def split_into_chunks(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> list[TextChunk]:
    """
    Splits text into overlapping chunks by word count.
    Respects sentence and paragraph boundaries where possible.
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    text = clean_text(text)

    # Split into sentences to avoid mid-sentence cuts
    sentences = _split_sentences(text)

    chunks: list[TextChunk] = []
    current_words: list[str] = []
    chunk_index = 0

    for sentence in sentences:
        words = sentence.split()
        current_words.extend(words)

        if len(current_words) >= chunk_size:
            chunk_text = " ".join(current_words[:chunk_size])
            chunks.append(TextChunk(content=chunk_text, chunk_index=chunk_index))
            chunk_index += 1
            # Retain overlap from end of current chunk
            current_words = current_words[chunk_size - chunk_overlap:]

    # Add any remaining words as a final chunk
    if current_words:
        chunk_text = " ".join(current_words)
        if chunk_text.strip():
            chunks.append(TextChunk(content=chunk_text, chunk_index=chunk_index))

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitter that respects paragraph breaks."""
    # First split on paragraph breaks, then on sentence-ending punctuation
    paragraphs = re.split(r"\n{2,}", text)
    sentences = []
    for para in paragraphs:
        # Split on '. ', '! ', '? ' but keep the punctuation
        parts = re.split(r"(?<=[.!?])\s+", para)
        sentences.extend(parts)
    return [s.strip() for s in sentences if s.strip()]