from __future__ import annotations

import re


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BOUNDARY = re.compile(r"(?<=[,;:])\s+")
_WHITESPACE = re.compile(r"\s+")


def _split_words(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for word in text.split():
        additional = len(word) if not current else len(word) + 1
        if current and current_length + additional > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length += additional

    if current:
        chunks.append(" ".join(current))
    return chunks


def _split_oversized(text: str, max_chars: int) -> list[str]:
    clauses = [part.strip() for part in _CLAUSE_BOUNDARY.split(text) if part.strip()]
    if len(clauses) == 1:
        return _split_words(text, max_chars)

    chunks: list[str] = []
    current = ""
    for clause in clauses:
        candidate = clause if not current else f"{current} {clause}"
        if current and len(candidate) > max_chars:
            chunks.extend(_split_words(current, max_chars))
            current = clause
        else:
            current = candidate

    if current:
        chunks.extend(_split_words(current, max_chars))
    return chunks


def split_text(text: str, max_chars: int) -> list[str]:
    """Split text on natural boundaries while preserving all input words."""

    normalized = _WHITESPACE.sub(" ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip()]
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_oversized(sentence, max_chars))
            continue

        candidate = sentence if not current else f"{current} {sentence}"
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        chunks.append(current)

    return [chunk for chunk in chunks if chunk]
