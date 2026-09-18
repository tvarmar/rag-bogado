"""Command-line interface for official source ingestion and synchronization."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.ingestion.boe import BoeClient
from rag_bogado.ingestion.sync import BoeSyncService
from rag_bogado.retrieval.embeddings import EmbeddingModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    meta_parser = commands.add_parser("metadata", help="Fetch BOE document metadata")
    meta_parser.add_argument("identifier", help="Official BOE document ID")

    sync_parser = commands.add_parser("sync", help="Synchronize official BOE documents")
    sync_parser.add_argument(
        "identifiers", nargs="+", help="One or more official BOE document IDs"
    )
    sync_parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/catalog.sqlite3")
    )
    sync_parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    sync_parser.add_argument("--store-path", type=Path, default=Path("data/qdrant"))
    sync_parser.add_argument("--model", default="intfloat/multilingual-e5-small")
    sync_parser.add_argument(
        "--revision", default="614241f622f53c4eeff9890bdc4f31cfecc418b3"
    )
    sync_parser.add_argument("--chunk-size", type=int, default=800)
    sync_parser.add_argument("--overlap", type=int, default=120)

    args = parser.parse_args()

    if args.command == "metadata":
        with BoeClient() as client:
            meta = client.get_metadata(args.identifier)
            print(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2))
    elif args.command == "sync":
        with DocumentCatalog(args.catalog) as catalog, BoeClient() as client:
            model = EmbeddingModel(
                args.model, revision=args.revision, local_files_only=True
            )
            service = BoeSyncService(
                catalog=catalog,
                boe_client=client,
                model=model,
                raw_dir=args.raw_dir,
                store_path=args.store_path,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
                dimension=model.model.get_embedding_dimension(),
                model_name=args.model,
                revision=args.revision,
            )
            results = service.sync_documents(args.identifiers)
            serialized = [
                {
                    "action": r.action,
                    "document_id": r.document_id,
                    "content_hash": r.content_hash,
                    "run_id": r.run_id,
                    "error": r.error,
                    "metadata": asdict(r.metadata) if r.metadata else None,
                }
                for r in results
            ]
            print(json.dumps(serialized, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
