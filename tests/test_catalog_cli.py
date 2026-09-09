"""The CLI retains originals and queries without reopening the input PDF."""

import json
import sys
from types import SimpleNamespace

import pymupdf

from rag_bogado.indexing import __main__ as cli
from rag_bogado.indexing.service import query_active


def test_index_query_and_history_commands(tmp_path, monkeypatch, capsys):
    source = tmp_path / "original.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72, 100), "Test evidence")
        pdf.save(source)
    original_bytes = source.read_bytes()
    embedded = []

    class Model:
        def __init__(self, *args, **kwargs):
            self.model = SimpleNamespace(get_embedding_dimension=lambda: 2)

        def embed_passages(self, texts):
            embedded.extend(texts)
            return [[1.0, 0.0] for _ in texts]

        def embed_query(self, text):
            return [1.0, 0.0]

    monkeypatch.setattr(cli, "EmbeddingModel", Model)
    monkeypatch.setattr(
        cli,
        "query_active",
        lambda *a, **kw: query_active(*a, **kw, model_factory=Model),
    )
    base = ["indexing", "--catalog", str(tmp_path / "catalog" / "catalog.sqlite3")]
    index_args = [
        "index",
        str(source),
        "--document-id",
        "test",
        "--store-path",
        str(tmp_path / "vectors"),
    ]
    for _ in range(2):
        monkeypatch.setattr(sys, "argv", base + index_args)
        cli.main()
        capsys.readouterr()
    assert embedded == ["Test evidence"]

    def no_pdf(*args):
        raise AssertionError("Query must not read or chunk the PDF")

    monkeypatch.setattr(cli, "load_pdf", no_pdf)
    source.write_bytes(b"Input has changed since indexing")
    monkeypatch.setattr(
        sys, "argv", base + ["query", "--document-id", "test", "Question?"]
    )
    cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result["results"][0]["chunk"]["text"] == "Test evidence"
    from pathlib import Path

    assert Path(result["source_path"]).read_bytes() == original_bytes
    monkeypatch.setattr(sys, "argv", base + ["history", "--document-id", "test"])
    cli.main()
    history = json.loads(capsys.readouterr().out)
    assert len(history) == 2
    assert [row["active"] for row in history] == [0, 1]
