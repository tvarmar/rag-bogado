"""Index an official XML document, query active versions, or inspect history."""

import argparse
import hashlib
import json
from pathlib import Path

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.configuration import index_configuration
from rag_bogado.indexing.service import publish_index, query_active
from rag_bogado.ingestion.xml_loader import load_xml_chunks
from rag_bogado.retrieval.embeddings import EmbeddingModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/catalog.sqlite3")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Build and activate a document version")
    index.add_argument("document", type=Path, help="XML document to index")
    index.add_argument("--document-id", required=True)
    index.add_argument("--title")
    index.add_argument("--store-path", type=Path, default=Path("data/qdrant"))
    index.add_argument("--model", default="intfloat/multilingual-e5-small")
    index.add_argument("--revision", default="614241f622f53c4eeff9890bdc4f31cfecc418b3")
    index.add_argument("--chunk-size", type=int, default=1200)
    index.add_argument("--overlap", type=int, default=120)
    query = commands.add_parser(
        "query", help="Retrieve active evidence without reading a document"
    )
    query.add_argument("--document-id", required=True)
    query.add_argument("question")
    query.add_argument("--top-k", type=int, default=5)
    history = commands.add_parser("history", help="Show versions and indexing attempts")
    history.add_argument("--document-id", required=True)
    commands.add_parser("failures", help="Show failed indexing attempts")
    sync_status = commands.add_parser(
        "sync-status", help="Show source sync metadata for a document"
    )
    sync_status.add_argument("--document-id", required=True)
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
            elif args.command == "sync-status":
                result = catalog.get_sync_metadata(args.document_id)
                if result is None:
                    result = {"status": "not_found", "document_id": args.document_id}
            else:
                original = args.document.read_bytes()
                digest = hashlib.sha256(original).hexdigest()
                snapshot = (
                    args.catalog.parent / "originals" / digest / args.document.name
                )
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                if snapshot.exists():
                    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest:
                        raise ValueError(
                            "Stored original does not match its content hash"
                        )
                else:
                    with snapshot.open("xb") as destination:
                        destination.write(original)
                chunks = load_xml_chunks(snapshot, max_chunk_size=args.chunk_size)
                if not chunks:
                    raise ValueError("Document contains no indexable text")
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
                    title=args.title or args.document.stem,
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
