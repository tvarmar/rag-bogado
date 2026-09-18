"""Official legal documents forming the RAG-Bogado regulatory corpus."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusDocumentDefinition:
    """Specification of an official regulatory document in the corpus."""

    document_id: str
    official_id: str
    title: str
    short_name: str
    scope_description: str


OFFICIAL_CORPUS_DOCUMENTS: list[CorpusDocumentDefinition] = [
    CorpusDocumentDefinition(
        document_id="eu_ai_act",
        official_id="DOUE-L-2024-81079",
        title=(
            "Reglamento (UE) 2024/1689 del Parlamento Europeo y del Consejo, "
            "de 13 de junio de 2024, por el que se establecen normas armonizadas "
            "en materia de inteligencia artificial (Reglamento de IA)"
        ),
        short_name="Reglamento de IA",
        scope_description="113 artículos, 180 considerandos y 13 anexos estructurados.",
    ),
    CorpusDocumentDefinition(
        document_id="rgpd",
        official_id="BOE-A-2018-16673",
        title=(
            "Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos "
            "Personales y garantía de los derechos digitales (LOPDGDD / RGPD)"
        ),
        short_name="RGPD / LOPDGDD",
        scope_description=(
            "97 artículos, 22 disposiciones adicionales y 6 transitorias."
        ),
    ),
    CorpusDocumentDefinition(
        document_id="dsa",
        official_id="DOUE-L-2022-81573",
        title=(
            "Reglamento (UE) 2022/2065 del Parlamento Europeo y del Consejo, "
            "de 19 de octubre de 2022, relativo a un mercado único de servicios "
            "digitales (Reglamento de Servicios Digitales - DSA)"
        ),
        short_name="Servicios Digitales (DSA)",
        scope_description="93 artículos y 156 considerandos estructurados.",
    ),
    CorpusDocumentDefinition(
        document_id="nis2",
        official_id="DOUE-L-2022-81963",
        title=(
            "Directiva (UE) 2022/2555 del Parlamento Europeo y del Consejo, "
            "de 14 de diciembre de 2022, relativa a las medidas destinadas a "
            "garantizar un elevado nivel común de ciberseguridad (Directiva NIS 2)"
        ),
        short_name="Ciberseguridad (NIS 2)",
        scope_description="46 artículos, 144 considerandos y 2 anexos estructurados.",
    ),
]

DOCUMENT_ID_TO_OFFICIAL_ID: dict[str, str] = {
    doc.document_id: doc.official_id for doc in OFFICIAL_CORPUS_DOCUMENTS
}

OFFICIAL_ID_TO_DOCUMENT_ID: dict[str, str] = {
    doc.official_id: doc.document_id for doc in OFFICIAL_CORPUS_DOCUMENTS
}


def resolve_document_identifiers(
    identifier: str, official_id: str | None = None
) -> tuple[str, str]:
    """Resolve an identifier to (document_id, official_id).

    If identifier is a known corpus alias (e.g. 'eu_ai_act', 'rgpd', 'dsa', 'nis2'),
    resolve official_id from the corpus definitions.
    If identifier is an official ID, keep it as document_id unless official_id
    is specified.
    """
    clean_id = identifier.strip()
    if official_id:
        return clean_id, official_id.strip()
    if clean_id in DOCUMENT_ID_TO_OFFICIAL_ID:
        return clean_id, DOCUMENT_ID_TO_OFFICIAL_ID[clean_id]
    return clean_id, clean_id
