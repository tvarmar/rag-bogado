"""Extract structured legal units and chunks from regulatory XML documents."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.ingestion.normalizer import normalize_text


@dataclass
class LegalUnit:
    """A semantic legal unit such as an article, recital, or annex."""

    unit_id: str
    unit_type: str
    identifier: str
    title: str
    text: str
    source: str
    order: int


def _clean_xml_content(path: Path) -> str:
    """Read XML, stripping non-XML preamble banners if present."""
    content = path.read_text(encoding="utf-8")
    for marker in ("<documento", "<?xml", "<"):
        idx = content.find(marker)
        if idx != -1:
            return content[idx:]
    return content


def _split_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries without losing punctuation."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _chunk_unit_content(
    prefix: str, paragraphs: list[str], max_chars: int = 1200
) -> list[str]:
    """Group paragraphs under a prefix, splitting long paragraphs by sentences."""
    full_text = f"{prefix}\n" + "\n".join(paragraphs) if paragraphs else prefix
    if len(full_text) <= max_chars:
        return [full_text.strip()]

    chunks: list[str] = []
    current = prefix

    pieces: list[str] = []
    for p in paragraphs:
        if len(p) > max_chars:
            pieces.extend(_split_sentences(p))
        else:
            pieces.append(p)

    for piece in pieces:
        if len(current) + len(piece) + 1 <= max_chars:
            current += ("\n" if current == prefix else " ") + piece
        else:
            if current != prefix:
                chunks.append(current.strip())
            current = f"{prefix}\n{piece}"

    if current != prefix:
        chunks.append(current.strip())

    return chunks


def load_xml(path: Path) -> list[LegalUnit]:
    """Parse structured legal units (recitals, articles, annexes) from XML."""
    content = _clean_xml_content(path)
    root = ET.fromstring(content)
    texto = root.find("texto")
    if texto is None:
        texto = root

    units: list[LegalUnit] = []
    order = 0

    # 1. Parse recitals (considerandos) from tables
    for table in texto.findall(".//table"):
        for tr in table.findall(".//tr"):
            tds = tr.findall(".//td")
            if len(tds) == 2:
                num_text = "".join(tds[0].itertext()).strip()
                body_text = "".join(tds[1].itertext()).strip()
                if (
                    num_text.startswith("(")
                    and num_text.endswith(")")
                    and num_text[1:-1].isdigit()
                ):
                    num = int(num_text[1:-1])
                    clean_body = normalize_text(body_text)
                    if clean_body:
                        units.append(
                            LegalUnit(
                                unit_id=f"recital_{num}",
                                unit_type="recital",
                                identifier=f"Considerando {num_text}",
                                title="",
                                text=clean_body,
                                source=path.name,
                                order=order,
                            )
                        )
                        order += 1

    # 2. Parse articles and annexes from paragraphs
    curr_art: dict | None = None
    curr_annex: dict | None = None

    for p in texto.findall(".//p"):
        cls = p.attrib.get("class", "")
        txt = "".join(p.itertext()).strip()
        if not txt:
            continue

        if cls == "articulo" or re.match(r"^Artículo\s+\d+", txt, re.IGNORECASE):
            if curr_art:
                units.append(_build_article_unit(curr_art, path.name, order))
                order += 1
            curr_art = {"header": txt, "title": "", "paras": []}
            curr_annex = None
        elif cls in ("anexo_num", "anexo") or re.match(
            r"^ANEXO\s+[IVXLCDM]+", txt, re.IGNORECASE
        ):
            if curr_art:
                units.append(_build_article_unit(curr_art, path.name, order))
                order += 1
                curr_art = None
            if curr_annex:
                units.append(_build_annex_unit(curr_annex, path.name, order))
                order += 1
            curr_annex = {"header": txt, "title": "", "paras": []}
        elif cls == "anexo_tit" and curr_annex:
            curr_annex["title"] = txt
        elif curr_art is not None:
            if cls in ("capitulo_num", "capitulo_tit", "seccion"):
                pass
            elif not curr_art["title"] and not txt.startswith(
                ("1.", "2.", "A los efectos", "El presente")
            ):
                curr_art["title"] = txt
            else:
                curr_art["paras"].append(txt)
        elif curr_annex is not None:
            curr_annex["paras"].append(txt)

    if curr_art:
        units.append(_build_article_unit(curr_art, path.name, order))
        order += 1
    if curr_annex:
        units.append(_build_annex_unit(curr_annex, path.name, order))
        order += 1

    # Fallback for generic XML documents without specific legal classes
    if not units:
        all_text = normalize_text("".join(texto.itertext()))
        if all_text:
            units.append(
                LegalUnit(
                    unit_id="doc_1",
                    unit_type="document",
                    identifier=path.stem,
                    title="",
                    text=all_text,
                    source=path.name,
                    order=0,
                )
            )

    return units


def _build_article_unit(data: dict, source: str, order: int) -> LegalUnit:
    """Construct an article LegalUnit from accumulated paragraphs."""
    header = data["header"]
    match = re.search(r"\d+", header)
    num = match.group() if match else str(order)
    return LegalUnit(
        unit_id=f"art_{num}",
        unit_type="article",
        identifier=header,
        title=data.get("title", ""),
        text=normalize_text("\n".join(data.get("paras", []))),
        source=source,
        order=order,
    )


def _build_annex_unit(data: dict, source: str, order: int) -> LegalUnit:
    """Construct an annex LegalUnit from accumulated paragraphs."""
    header = data["header"]
    return LegalUnit(
        unit_id=f"annex_{order}",
        unit_type="annex",
        identifier=header,
        title=data.get("title", ""),
        text=normalize_text("\n".join(data.get("paras", []))),
        source=source,
        order=order,
    )


def chunk_legal_units(
    units: list[LegalUnit], max_chunk_size: int = 1200
) -> list[Chunk]:
    """Convert LegalUnits into search chunks respecting max_chunk_size."""
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be positive")

    chunks: list[Chunk] = []
    chunk_id = 0

    for unit in units:
        prefix = f"{unit.identifier}. {unit.title}".strip(". ")
        paragraphs = [p.strip() for p in unit.text.split("\n") if p.strip()]
        text_chunks = _chunk_unit_content(prefix, paragraphs, max_chars=max_chunk_size)

        for text in text_chunks:
            if text:
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        text=text,
                        source=unit.source,
                        page_number=0,
                        article=unit.identifier,
                        unit_type=unit.unit_type,
                    )
                )
                chunk_id += 1

    return chunks


def load_xml_chunks(path: Path, max_chunk_size: int = 1200) -> list[Chunk]:
    """Load and chunk an XML document into retrieval chunks."""
    units = load_xml(path)
    return chunk_legal_units(units, max_chunk_size=max_chunk_size)
