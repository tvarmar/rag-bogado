from rag_bogado import main
from rag_bogado.ingestion.normalizer import normalize_text


def test_main_prints_greeting(capsys):
    main()

    captured = capsys.readouterr()

    assert captured.out == "Hello from rag-bogado!\n"


def test_normalize_text_removes_line_breaks():
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
