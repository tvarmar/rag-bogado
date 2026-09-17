"""Passage data structure for persistence, retrieval, and generation."""

from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: int
    text: str
    source: str
    page_number: int = 0
    article: str | None = None
    unit_type: str | None = None
