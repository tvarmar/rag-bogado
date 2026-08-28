from dataclasses import dataclass

from rag_bogado.ingestion.loader import Page


@dataclass
class Chunk:
    chunk_id: int
    text: str
    source: str
    page_number: int


def find_breakpoint(text: str, start: int, end: int) -> int:
    if end >= len(text):
        return len(text)

    for position in range(end, start, -1):
        if text[position - 1].isspace():
            return position

    return end


def find_startpoint(text: str, position: int, lower_bound: int) -> int:
    while position > lower_bound and not text[position - 1].isspace():
        position -= 1

    return position


def chunk_page(
    page: Page,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    chunk_id = 0

    while start < len(page.text):
        target_end = min(start + chunk_size, len(page.text))
        end = find_breakpoint(page.text, start, target_end)

        text = page.text[start:end].strip()

        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                text=text,
                source=page.source,
                page_number=page.page_number,
            )
        )

        chunk_id += 1

        if end >= len(page.text):
            break

        overlap_position = max(start + 1, end - overlap)

        next_start = find_startpoint(page.text, overlap_position, start)

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks
