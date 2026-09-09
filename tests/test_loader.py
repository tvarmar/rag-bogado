import pymupdf

from rag_bogado.ingestion.loader import load_pdf


def test_load_pdf_preserves_pages_and_excludes_margins(tmp_path):
    path = tmp_path / "example.pdf"
    with pymupdf.open() as document:
        for number in (1, 2):
            page = document.new_page()
            page.insert_text((72, 30), "HEADER")
            page.insert_text((72, 100), f"Body {number}")
            page.insert_text((72, 830), "FOOTER")
        document.save(path)

    pages = load_pdf(path)

    assert [page.page_number for page in pages] == [1, 2]
    assert [page.text.strip() for page in pages] == ["Body 1", "Body 2"]
    assert all(page.source == path.name for page in pages)
