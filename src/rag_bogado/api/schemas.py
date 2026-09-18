"""Pydantic request and response models for the RAG-Bogado REST API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    """Query request payload for retrieval and synthesis."""

    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(
        ...,
        min_length=1,
        description="Natural language question about indexed regulatory documents.",
        examples=["¿Quién debe procurar la alfabetización en IA?"],
    )
    document_id: str = Field(
        default="eu_ai_act",
        min_length=1,
        description="Identifier of the target document in the active catalog.",
        examples=["eu_ai_act"],
    )
    answer_mode: Literal["synthesis", "evidence"] = Field(
        default="synthesis",
        description=(
            "'synthesis' generates an LLM summary with citations; "
            "'evidence' returns exact source passages."
        ),
    )
    search_count: int = Field(
        default=2,
        ge=1,
        le=2,
        description=(
            "Number of searches: 1 (original only) or 2 "
            "(original plus rewrite with RRF)."
        ),
    )
    max_passages: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of candidate passages to supply as evidence.",
    )
    relative_margin: float | None = Field(
        default=0.025,
        ge=0.0,
        le=0.5,
        description=(
            "Relative score margin to discard distant passages when top score >= 0.85."
        ),
    )
    context_tokens: int = Field(
        default=8192,
        ge=512,
        le=32768,
        description="Context budget in UTF-8 tokens.",
    )
    output_tokens: int = Field(
        default=768,
        ge=64,
        le=4096,
        description="Maximum generation output token budget.",
    )


class SourceModel(BaseModel):
    """A retrieved and selected source passage with traceability metadata."""

    id: str = Field(..., description="Unique citation identifier (e.g. Q1-S1).")
    document: str = Field(..., description="Source document filename or identifier.")
    page: int = Field(..., description="Page number (0 for structured XML).")
    chunk_id: int = Field(..., description="Chunk identifier within the document.")
    version_id: int = Field(..., description="Catalog version identifier.")
    text: str = Field(..., description="Exact textual content of the retrieved chunk.")
    article: str | None = Field(
        default=None, description="Legal article designation (e.g. 'Artículo 4')."
    )
    unit_type: str | None = Field(
        default=None, description="Legal unit type: 'article', 'recital', or 'annex'."
    )


class ClaimModel(BaseModel):
    """An individual assertion with its supporting citation identifiers."""

    text: str = Field(..., description="Asserted claim text.")
    citations: list[str] = Field(
        default_factory=list,
        description="Source IDs that strictly substantiate this claim.",
    )


class AnswerModel(BaseModel):
    """Answer for an individual detected question."""

    question: str = Field(..., description="The individual question answered.")
    question_id: str = Field(
        ..., description="Identifier of the question (e.g. Q1, Q2)."
    )
    status: str = Field(
        ...,
        description=(
            "Outcome status: 'answered', 'insufficient_evidence', "
            "'review_rejected', or 'error'."
        ),
    )
    answer_mode: str = Field(..., description="Mode used ('synthesis' or 'evidence').")
    claims: list[ClaimModel] = Field(
        default_factory=list, description="Synthesized claims with citations."
    )
    sources: list[SourceModel] = Field(
        default_factory=list, description="Inspectable source passages."
    )
    display_message: str | None = Field(
        default=None,
        description=(
            "User-facing explanation when evidence is insufficient or review rejected."
        ),
    )


class UnansweredQuestionModel(BaseModel):
    """Record of a question that could not be answered."""

    question_id: str = Field(..., description="Identifier of the unanswered question.")
    question: str = Field(..., description="Text of the unanswered question.")
    reason: str = Field(
        ...,
        description="Reason: 'abstained', 'review_rejected', or 'error'.",
    )


class AskResponse(BaseModel):
    """Top-level response for a user query."""

    question: str = Field(..., description="Original user prompt received.")
    status: str = Field(
        ...,
        description=(
            "Overall status: 'answered', 'partial', "
            "'insufficient_evidence', or 'error'."
        ),
    )
    answers: list[AnswerModel] = Field(
        default_factory=list,
        description="Answers for each decomposed question aspect.",
    )
    unanswered_questions: list[UnansweredQuestionModel] = Field(
        default_factory=list,
        description="Question aspects that were rejected or lacked evidence.",
    )
    wall_seconds: float | None = Field(
        default=None, description="Total server processing duration in seconds."
    )


class HealthResponse(BaseModel):
    """System health and readiness status."""

    status: str = Field(
        ...,
        description="'ok' when catalog and services are ready, 'degraded' otherwise.",
    )
    version: str = Field(default="0.1.0", description="Application version.")
    catalog_ready: bool = Field(
        ..., description="Whether the SQLite document catalog is accessible."
    )
    active_documents: list[str] = Field(
        default_factory=list,
        description="List of active document IDs ready to be queried.",
    )
    ollama_ready: bool = Field(
        default=False,
        description="Whether the local Ollama LLM service is responsive.",
    )


class DocumentInfoModel(BaseModel):
    """Metadata and readiness status of a regulatory corpus document."""

    id: str = Field(..., description="Internal document identifier (e.g. 'eu_ai_act').")
    official_id: str = Field(
        ..., description="Official BOE/DOUE publication identifier."
    )
    title: str = Field(..., description="Full official legal title.")
    short_name: str = Field(..., description="Human-friendly short name for UI.")
    scope_description: str = Field(
        ..., description="Summary of legal articles and recitals."
    )
    active: bool = Field(
        ..., description="Whether this document has an active, queryable index."
    )
    sync_status: str | None = Field(
        default=None, description="BOE synchronization status."
    )
    last_checked_at: str | None = Field(
        default=None, description="ISO timestamp of last check."
    )
    last_updated: str | None = Field(
        default=None, description="Official date of last amendment/update."
    )
    source_url: str | None = Field(
        default=None, description="URL to official publication."
    )


class DocumentsListResponse(BaseModel):
    """List of all target documents in the corpus and their status."""

    documents: list[DocumentInfoModel] = Field(default_factory=list)
    total: int = Field(..., description="Total documents defined in corpus.")
    active_count: int = Field(..., description="Number of actively indexed documents.")


class SyncResultModel(BaseModel):
    """Result of an individual document sync operation."""

    document_id: str
    action: str
    status: str
    error: str | None = None


class SyncResponse(BaseModel):
    """Summary of corpus synchronization batch."""

    status: str
    results: list[SyncResultModel] = Field(default_factory=list)
