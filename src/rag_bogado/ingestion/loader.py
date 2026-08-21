from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass
class Page:
    page_number: int
    text: str
    source: str


def extract_page_text(
    page: pymupdf.Page,
    top_margin: float = 65,
    bottom_margin: float = 30,
) -> str:
    clip = pymupdf.Rect(
        page.rect.x0,
        page.rect.y0 + top_margin,
        page.rect.x1,
        page.rect.y1 - bottom_margin,
    )
    return page.get_text(clip=clip)


def load_pdf(path: Path) -> list[Page]:
    document = pymupdf.open(path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = extract_page_text(page)

        pages.append(Page(page_number=page_number, text=text, source=path.name))

    return pages
