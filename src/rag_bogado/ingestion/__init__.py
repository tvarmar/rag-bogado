"""Ingestion pipeline modules for XML parsing and legal text normalization."""

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.ingestion.normalizer import normalize_text
from rag_bogado.ingestion.xml_loader import (
    LegalUnit,
    chunk_legal_units,
    load_xml,
    load_xml_chunks,
)

__all__ = [
    "Chunk",
    "LegalUnit",
    "chunk_legal_units",
    "load_xml",
    "load_xml_chunks",
    "normalize_text",
]
