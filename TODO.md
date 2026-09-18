# Pendientes para próximas sesiones

Actualizado: 2026-09-18. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Revisar y entregar el **Hito 10 — Fuentes oficiales y actualización (BOE)** ([PROJECT_PLAN.md](PROJECT_PLAN.md)):
1. Confirmar con la usuaria la entrega en la rama `feat/official-sources-boe` (commit, push y apertura de PR).
2. Tras la validación de CI y fusión en `main`, iniciar el **Hito 11 — Comparación con LangGraph**:
   - Implementar un grafo de ejecución alternativo para orquestar retrieval y generación.
   - Comparar latencia, legibilidad, número de llamadas y control de fallos frente al pipeline nativo de Python.

## Estado actual

- **Hito 10 completado y verificado (2026-09-18):**
  - Cliente de la API de datos abiertos del BOE (`src/rag_bogado/ingestion/boe.py`) para consultar metadatos consolidados (`BoeDocumentMetadata`), descargar textos consolidados y computar hashes deterministas SHA-256 (`compute_content_hash`), con manejo estricto de excepciones (`BoeDocumentNotFoundError`, `BoeApiError`, `BoeNetworkError`).
  - Parser de normas mejorado (`src/rag_bogado/ingestion/xml_loader.py`) con soporte para respuestas anidadas del BOE (`<response><data><texto>`) y desambiguación de títulos de artículos en la cabecera.
  - Almacenamiento de metadatos de sincronización en `DocumentCatalog` (`src/rag_bogado/indexing/catalog.py`) con la tabla `source_metadata` para registrar `last_checked_at`, `last_updated`, `estado_consolidacion`, `fecha_vigencia` y estado de error sin perder versiones previas.
  - Servicio de sincronización atómica (`src/rag_bogado/ingestion/sync.py`):
    - Comprobación previa de metadatos: omite descargas y cómputo si el registro oficial no ha cambiado (`skipped_up_to_date`).
    - Detección de cambios por hash: actualiza metadatos sin regenerar embeddings si el texto legal no varió (`metadata_updated`).
    - Reindexación atómica segura: crea nueva colección, calcula embeddings y solo activa la nueva versión tras validar todos los vectores (`reindexed`).
    - Aislamiento de fallos (*fail-safe*): errores de red o indexación conservan intacta la versión operativa previa.
  - Herramientas CLI:
    - `python -m rag_bogado.ingestion metadata <id>` y `python -m rag_bogado.ingestion sync <id...>`.
    - `python -m rag_bogado.indexing sync-status --document-id <id>`.
  - Promoción de `httpx` a dependencias principales en `pyproject.toml` y `uv.lock`.
  - Tests deterministas y offline en `tests/test_boe_client.py`, `tests/test_boe_sync.py`, `tests/test_ingestion_cli.py`, `tests/test_catalog_cli.py` y `tests/test_xml_loader.py`. Suite total: **165 tests pasando**.
- **Hito 9 completado y fusionado en `main`:**
  - Contenedorización multietapa Docker y orquestación con Docker Compose para API y Qdrant. PR #7 fusionado en `main`.
- **Hito 8 completado y fusionado en `main`:**
  - Interfaz web interactiva y responsive servida en `/` por FastAPI, modo evidencia literal y presentación estructurada de listas y cláusulas jurídicas.
- **Hito 7 completado y fusionado en `main`:**
  - API REST FastAPI con schemas Pydantic y endpoints `/health` y `/ask`.
- **Hitos 5 y 6 completados y aceptados:**
  - Casos `d01` a `d09` evaluados; abstención *fail-closed* y multi-query RRF operativos.

## Próximas tareas, por orden

### 1. Hito 10 — Fuentes oficiales y actualización (cierre y entrega)
- **Objetivo:** Abrir PR de `feat/official-sources-boe` a `main`, validar CI y fusionar.
- **Archivos:** `src/rag_bogado/ingestion/`, `src/rag_bogado/indexing/`, `tests/`, `pyproject.toml`, `uv.lock`, `README.md`, `PROJECT_PLAN.md`.
- **Cierre:** CI en verde en GitHub y PR fusionado.

### 2. Hito 11 — Comparación con LangGraph (pendiente)
- **Objetivo:** Implementar un motor alternativo con LangGraph para comparar la orquestación basada en grafos con el pipeline nativo.
- **Archivos:** `src/rag_bogado/orchestration/` o módulo experimental equivalente.
- **Cierre:** Flujo cíclico con LangGraph implementado y comparado en latencia, control de errores y legibilidad con el pipeline nativo.

## Comprobaciones y entrega

- 2026-09-18: `uv run pytest`, **165 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Aceptación formal del Hito 10 registrada en `PROJECT_PLAN.md` y documentación en `README.md`.
- Rama: `feat/official-sources-boe`.
- `ESTUDIAR.md` ampliado con sección 9 sobre API del BOE, detección de cambios por hash, separación de auditoría temporal y activación atómica fail-safe (local e ignorado por Git).

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
