"""The CLI retains originals and queries without reopening the input XML."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from rag_bogado.indexing import __main__ as cli
from rag_bogado.indexing.service import query_active


def test_index_query_and_history_commands(tmp_path, monkeypatch, capsys):
    source = tmp_path / "original.xml"
    source.write_text(
        "<documento><texto>"
        "<p class='articulo'>Artículo 1</p>"
        "<p class='parrafo'>Test evidence</p>"
        "</texto></documento>",
        encoding="utf-8",
    )
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
    assert embedded == ["Artículo 1. Test evidence"]

    def no_xml(*args):
        raise AssertionError("Query must not read or chunk the XML")

    monkeypatch.setattr(cli, "load_xml_chunks", no_xml)
    source.write_bytes(b"Input has changed since indexing")
    monkeypatch.setattr(
        sys, "argv", base + ["query", "--document-id", "test", "Question?"]
    )
    cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result["results"][0]["chunk"]["text"] == "Artículo 1. Test evidence"
    assert Path(result["source_path"]).read_bytes() == original_bytes
    monkeypatch.setattr(sys, "argv", base + ["history", "--document-id", "test"])
    cli.main()
    history = json.loads(capsys.readouterr().out)
    assert len(history) == 2
    assert [row["active"] for row in history] == [0, 1]


def test_index_xml_document(tmp_path, monkeypatch, capsys):
    source = tmp_path / "law.xml"
    source.write_text(
        "<documento><texto>"
        "<p class='articulo'>Artículo 4</p>"
        "<p class='parrafo'>Alfabetización en IA</p>"
        "<p class='parrafo'>Regla legal.</p>"
        "</texto></documento>",
        encoding="utf-8",
    )
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
    base = ["indexing", "--catalog", str(tmp_path / "catalog" / "catalog.sqlite3")]
    index_args = [
        "index",
        str(source),
        "--document-id",
        "law_xml",
        "--store-path",
        str(tmp_path / "vectors"),
    ]
    monkeypatch.setattr(sys, "argv", base + index_args)
    cli.main()
    capsys.readouterr()
    assert len(embedded) == 1
    assert "Artículo 4. Alfabetización en IA" in embedded[0]
    assert "Regla legal." in embedded[0]
