from rag_bogado import main
from rag_bogado.ingestion.normalizer import normalize_whitespace


def test_main_prints_greeting(capsys):
    main()

    captured = capsys.readouterr()

    assert captured.out == "Hello from rag-bogado!\n"


def test_normalize_whitespace_removes_line_breaks():
    text = "Reglamento\nEuropeo\n   de IA"

    result = normalize_whitespace(text)

    assert result == "Reglamento Europeo de IA"


def test_normalize_whitespace_handles_legal_reference():
    text = "n.º\n300/2008"

    result = normalize_whitespace(text)

    assert result == "n.º 300/2008"
