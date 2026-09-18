"""Client and models for the BOE (Boletín Oficial del Estado) Open Data API."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import httpx

DEFAULT_BOE_API_URL = "https://www.boe.es/datosabiertos/api/legislacion-consolidada"


class BoeError(Exception):
    """Base exception for BOE API operations."""


class BoeDocumentNotFoundError(BoeError):
    """Raised when a requested document is not found in the BOE API."""


class BoeApiError(BoeError):
    """Raised when the BOE API returns an unexpected status or payload."""


class BoeNetworkError(BoeError):
    """Raised when network connectivity or timeouts occur during API requests."""


@dataclass(frozen=True)
class BoeDocumentMetadata:
    """Structured legal metadata retrieved from the BOE open data service."""

    official_id: str
    title: str
    source: str = "BOE"
    source_url: str = ""
    url_eli: str = ""
    fecha_actualizacion: str = ""
    estado_consolidacion: str = ""
    estado_consolidacion_codigo: str = ""
    fecha_publicacion: str = ""
    fecha_vigencia: str = ""
    vigencia_agotada: bool = False
    estatus_derogacion: str = "N"
    last_checked_at: str = ""
    downloaded_at: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def compute_content_hash(content: str | bytes) -> str:
    """Calculate the deterministic SHA-256 hash of document text or bytes."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


class BoeClient:
    """HTTP client for querying metadata and consolidated texts from the BOE API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BOE_API_URL,
        *,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._custom_client = client is not None
        self.client = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "RAG-Bogado/0.1.0 (Retriever Legal Assistant)"},
        )

    def close(self) -> None:
        if not self._custom_client:
            self.client.close()

    def __enter__(self) -> BoeClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_metadata(self, identifier: str) -> BoeDocumentMetadata:
        """Fetch consolidated metadata for a given BOE identifier."""
        identifier = identifier.strip()
        if not identifier:
            raise ValueError("Document identifier cannot be blank")

        url = f"{self.base_url}/id/{identifier}/metadatos"
        try:
            response = self.client.get(url, headers={"Accept": "application/json"})
        except httpx.RequestError as exc:
            msg = f"Network error querying BOE metadata for '{identifier}': {exc}"
            raise BoeNetworkError(msg) from exc

        if response.status_code == 404:
            raise BoeDocumentNotFoundError(
                f"BOE document '{identifier}' was not found (404)"
            )
        if response.status_code != 200:
            raise BoeApiError(
                f"BOE API returned unexpected HTTP status "
                f"{response.status_code} for '{identifier}'"
            )

        try:
            payload = response.json()
        except Exception as exc:
            msg = f"Failed to parse JSON response for '{identifier}': {exc}"
            raise BoeApiError(msg) from exc

        status_obj = payload.get("status", {})
        code = str(status_obj.get("code", ""))
        if code == "404":
            raise BoeDocumentNotFoundError(
                f"BOE document '{identifier}' not found in status payload"
            )
        if code != "200":
            raise BoeApiError(
                f"BOE API reported non-200 code '{code}': {status_obj.get('text', '')}"
            )

        data = payload.get("data")
        if not data or not isinstance(data, list) or not isinstance(data[0], dict):
            raise BoeApiError(
                f"Malformed or empty data block in BOE metadata for '{identifier}'"
            )

        doc = data[0]
        estado = doc.get("estado_consolidacion") or {}
        if isinstance(estado, dict):
            estado_texto = estado.get("texto", "")
            estado_codigo = str(estado.get("codigo", ""))
        else:
            estado_texto = str(estado)
            estado_codigo = ""

        now_utc = datetime.now(timezone.utc).isoformat()

        return BoeDocumentMetadata(
            official_id=doc.get("identificador", identifier),
            title=doc.get("titulo", ""),
            source="BOE",
            source_url=doc.get("url_html_consolidada", ""),
            url_eli=doc.get("url_eli", ""),
            fecha_actualizacion=doc.get("fecha_actualizacion", ""),
            estado_consolidacion=estado_texto,
            estado_consolidacion_codigo=estado_codigo,
            fecha_publicacion=doc.get("fecha_publicacion", ""),
            fecha_vigencia=doc.get("fecha_vigencia", ""),
            vigencia_agotada=doc.get("vigencia_agotada") == "S",
            estatus_derogacion=doc.get("estatus_derogacion", "N"),
            last_checked_at=now_utc,
        )

    def download_xml(self, identifier: str) -> str:
        """Download complete consolidated XML for a given BOE identifier."""
        identifier = identifier.strip()
        if not identifier:
            raise ValueError("Document identifier cannot be blank")

        url = f"{self.base_url}/id/{identifier}"
        try:
            response = self.client.get(url, headers={"Accept": "application/xml"})
        except httpx.RequestError as exc:
            msg = f"Network error downloading BOE XML for '{identifier}': {exc}"
            raise BoeNetworkError(msg) from exc

        if response.status_code == 404:
            raise BoeDocumentNotFoundError(
                f"BOE document '{identifier}' XML was not found (404)"
            )
        if response.status_code != 200:
            raise BoeApiError(
                f"BOE API returned unexpected HTTP status "
                f"{response.status_code} downloading XML for '{identifier}'"
            )

        content = response.text
        if not content.strip():
            raise BoeApiError(
                f"Empty XML payload returned for BOE document '{identifier}'"
            )

        if "<status>" in content and "<code>404</code>" in content:
            raise BoeDocumentNotFoundError(
                f"BOE XML returned 404 status body for '{identifier}'"
            )

        return content
