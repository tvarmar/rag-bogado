"""Metrics for retrieval results with known evidence references."""

from typing import NotRequired, TypedDict

from rag_bogado.retrieval.retriever import SearchResult


class EvidenceReference(TypedDict):
    page: int
    reference: str
    anchor: str
    rationale: NotRequired[str]


def evidence_rank(
    results: list[SearchResult], source: str, evidence: list[EvidenceReference]
) -> int | None:
    """Return the first result matching any accepted evidence alternative."""
    for rank, result in enumerate(results, start=1):
        chunk = result.chunk
        if chunk.source == source and any(
            chunk.page_number == alternative["page"]
            and " ".join(alternative["anchor"].split()).casefold()
            in " ".join(chunk.text.split()).casefold()
            for alternative in evidence
        ):
            return rank
    return None


def summarize(ranks: list[int | None]) -> dict[str, float]:
    if not ranks:
        raise ValueError("At least one answerable question is required")
    metrics = {
        f"hit@{k}": sum(rank is not None and rank <= k for rank in ranks) / len(ranks)
        for k in (1, 5, 10)
    }
    metrics["mrr@10"] = sum(1 / rank for rank in ranks if rank) / len(ranks)
    return metrics
