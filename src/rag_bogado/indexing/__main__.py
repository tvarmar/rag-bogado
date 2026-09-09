"""Index a local PDF, query its active version, or inspect indexing history."""

import argparse
import hashlib
import json
from pathlib import Path

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.configuration import index_configuration
from rag_bogado.indexing.service import publish_index, query_active
from rag_bogado.ingestion.chunker import chunk_page
from rag_bogado.ingestion.loader import Page, load_pdf
from rag_bogado.ingestion.normalizer import normalize_text
from rag_bogado.retrieval.embeddings import EmbeddingModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/catalog.sqlite3")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Build and activate a document version")
    index.add_argument("pdf", type=Path)
    index.add_argument("--document-id", required=True)
    index.add_argument("--title")
    index.add_argument("--store-path", type=Path, default=Path("data/qdrant"))
    index.add_argument("--model", default="intfloat/multilingual-e5-small")
    index.add_argument("--revision", default="614241f622f53c4eeff9890bdc4f31cfecc418b3")
    index.add_argument("--chunk-size", type=int, default=800)
    index.add_argument("--overlap", type=int, default=120)
    query = commands.add_parser(
        "query", help="Retrieve active evidence without reading a PDF"
    )
    query.add_argument("--document-id", required=True)
    query.add_argument("question")
    query.add_argument("--top-k", type=int, default=5)
    history = commands.add_parser("history", help="Show versions and indexing attempts")
    history.add_argument("--document-id", required=True)
    commands.add_parser("failures", help="Show failed indexing attempts")
    args = parser.parse_args()
    try:
        with DocumentCatalog(args.catalog) as catalog:
            if args.command == "query":
                result = query_active(
                    catalog, args.document_id, args.question, top_k=args.top_k
                )
            elif args.command == "history":
                result = catalog.history(args.document_id)
            elif args.command == "failures":
                result = catalog.failed_runs()
            else:
                original = args.pdf.read_bytes()
                digest = hashlib.sha256(original).hexdigest()
                # Retain each original independently of future changes to the input PDF.
                snapshot = args.catalog.parent / "originals" / digest / args.pdf.name
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                if snapshot.exists():
                    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest:
                        raise ValueError(
                            "Stored original does not match its content hash"
                        )
                else:
                    with snapshot.open("xb") as destination:
                        destination.write(original)
                chunks = [
                    chunk
                    for page in load_pdf(snapshot)
                    for chunk in chunk_page(
                        Page(page.page_number, normalize_text(page.text), page.source),
                        args.chunk_size,
                        args.overlap,
                    )
                ]
                if not chunks:
                    raise ValueError("PDF contains no indexable text")
                model = EmbeddingModel(
                    args.model, revision=args.revision, local_files_only=True
                )
                configuration = index_configuration(
                    digest,
                    args.model,
                    args.revision,
                    model.model.get_embedding_dimension(),
                    args.chunk_size,
                    args.overlap,
                )
                result = publish_index(
                    catalog,
                    document_id=args.document_id,
                    title=args.title or args.pdf.stem,
                    source_path=snapshot,
                    chunks=chunks,
                    configuration=configuration,
                    store_path=args.store_path,
                    model=model,
                )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
