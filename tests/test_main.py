import pytest

from rag_bogado import main
from rag_bogado.ingestion.chunker import chunk_page
from rag_bogado.ingestion.loader import Page
from rag_bogado.ingestion.normalizer import normalize_text


def test_main_prints_greeting(capsys):
    main()

    captured = capsys.readouterr()

    assert captured.out == "Hello from rag-bogado!\n"


def test_normalize_text_preserves_line_breaks():
    text = "Artículo 3\nDefiniciones"

    result = normalize_text(text)

    assert result == "Artículo 3\nDefiniciones"


def test_normalize_text_collapses_horizontal_whitespace():
    text = "Artículo   3\nDefiniciones"

    result = normalize_text(text)

    assert result == "Artículo 3\nDefiniciones"


def test_normalize_text_removes_extra_blank_lines():
    text = "Artículo 3\n\n\n\nDefiniciones"

    result = normalize_text(text)

    assert result == "Artículo 3\n\nDefiniciones"


def test_chunk_page_returns_single_chunk_for_short_text():
    page = Page(page_number=1, text="Texto jurídico corto.", source="ai_act.pdf")

    chunks = chunk_page(page, chunk_size=100, overlap=20)

    assert len(chunks) == 1


def test_chunk_page_preserves_page_metadata():
    page = Page(page_number=42, text="Texto jurídico corto.", source="ai_act.pdf")

    chunks = chunk_page(page, chunk_size=100, overlap=20)

    assert chunks[0].page_number == 42
    assert chunks[0].source == "ai_act.pdf"
    assert chunks[0].chunk_id == 0


def test_chunk_page_rejects_overlap_equal_to_chunk_size():
    page = Page(
        page_number=1,
        text="Texto de prueba",
        source="test.pdf",
    )

    with pytest.raises(ValueError):
        chunk_page(page, chunk_size=10, overlap=10)


def test_chunk_page_rejects_negative_overlap():
    page = Page(
        page_number=1,
        text="Texto de prueba",
        source="test.pdf",
    )

    with pytest.raises(ValueError):
        chunk_page(page, chunk_size=10, overlap=-1)


def test_chunk_page_does_not_split_words():
    page = Page(
        page_number=1,
        text="uno dos tres cuatro cinco seis",
        source="test.pdf",
    )

    chunks = chunk_page(page, chunk_size=12, overlap=3)

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk.text[0] != " "
        assert chunk.text[-1] != " "


def test_chunk_page_rejects_non_positive_chunk_size():
    page = Page(
        page_number=1,
        text="Texto de prueba",
        source="test.pdf",
    )

    with pytest.raises(ValueError):
        chunk_page(page, chunk_size=0, overlap=0)


def test_chunk_page_does_not_skip_content():
    page = Page(
        page_number=1,
        text="uno dos tres cuatro cinco seis siete ocho nueve diez",
        source="test.pdf",
    )

    chunks = chunk_page(page, chunk_size=15, overlap=0)

    reconstructed_words = " ".join(chunk.text for chunk in chunks).split()
    original_words = page.text.split()

    assert reconstructed_words == original_words


def test_chunk_page_returns_no_chunks_for_empty_text():
    page = Page(
        page_number=1,
        text="",
        source="test.pdf",
    )

    chunks = chunk_page(page)

    assert chunks == []


def test_chunk_page_returns_no_chunks_for_whitespace():
    assert chunk_page(Page(1, " \n\t " * 100, "test.pdf")) == []


@pytest.mark.parametrize("overlap", [0, 3, 14])
def test_chunk_page_preserves_all_words_with_overlap(overlap):
    words = "uno dos tres cuatro cinco seis siete ocho nueve diez".split()
    chunks = chunk_page(Page(1, " ".join(words), "test.pdf"), 15, overlap)
    recovered = [word for chunk in chunks for word in chunk.text.split()]
    assert set(recovered) == set(words)
    assert all(chunk.text for chunk in chunks)
