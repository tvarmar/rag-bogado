"""Retrieve and answer each explicit question without mixing its evidence."""

import time
from collections.abc import Callable

from rag_bogado.generation.generator import OllamaGenerator
from rag_bogado.generation.questions import split_questions


def answer_questions(
    question: str,
    generator: OllamaGenerator,
    retrieve: Callable[[str], dict],
    **generation_options,
) -> dict:
    """Keep one result per detected question, including failures and abstentions.

    Citation IDs are namespaced by question. The final response is assembled
    deterministically so a second synthesis cannot silently drop an answer.
    """
    started = time.perf_counter()
    decomposition = split_questions(question, generator)
    answers = []
    identity = None
    for number, individual in enumerate(decomposition["questions"], start=1):
        question_id = f"Q{number}"
        try:
            retrieval_started = time.perf_counter()
            query = retrieve(individual)
            retrieval_seconds = time.perf_counter() - retrieval_started
            current = tuple(
                query[k]
                for k in ("document_id", "version_id", "content_hash", "index_id")
            )
            if identity is None:
                identity = current
            if current != identity:
                raise ValueError("Active document version changed between questions")
            if query["question"] != individual:
                raise ValueError("Retrieved evidence belongs to a different question")
            result = generator.generate(query, **generation_options)
            for source in result["sources"]:
                source["id"] = f"{question_id}-{source['id']}"
            for claim in result["claims"]:
                claim["citations"] = [f"{question_id}-{c}" for c in claim["citations"]]
            result["retrieval_seconds"] = retrieval_seconds
        except (ValueError, RuntimeError, OSError, KeyError) as error:
            result = {
                "question": individual,
                "status": "error",
                "error": str(error),
                "claims": [],
                "sources": [],
            }
        answers.append(dict(result, question_id=question_id))
    statuses = {a["status"] for a in answers}
    if statuses == {"answered"}:
        status = "answered"
    elif "answered" in statuses:
        status = "partial"
    elif "error" in statuses:
        status = "error"
    else:
        status = "insufficient_evidence"
    return {
        "question": question,
        "status": status,
        "decomposition": decomposition,
        "answers": answers,
        "wall_seconds": time.perf_counter() - started,
        "semantic_support_reviewed": False,
    }
