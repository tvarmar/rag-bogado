from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Page:
    page_number: int
    text: str
    source: str


def load_pdf(path: Path) -> list[Page]:
    reader = PdfReader(path)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()

        pages.append(Page(page_number=page_number, text=text, source=path.name))

    return pages
