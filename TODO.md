# Pendientes para próximas sesiones

Actualizado: 2026-09-18. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

1. Revisar y autorizar la fusión del Pull Request #9 (`feat/corpus-boe-sync`) a la rama `main` en GitHub.
2. Evaluar comprobación estática de tipos con `mypy` / `pyright` (Hito 12).

## Estado actual

- **Documentación de Portfolio y Showcase Profesional (Hito 13) completado (2026-09-18):**
  - [README.md](README.md) completamente renovado:
    - Badges de estado (CI, Python 3.12, uv, FastAPI, Qdrant, Docker).
    - Planteamiento del problema específico de Legal Tech RAG (coste de alucinaciones, pérdida de estructura en PDFs, control de versiones).
    - Diagramas Mermaid:
      - Pipeline RAG extremo a extremo (descomposición multi-query, búsqueda densa con E5, fusión RRF, selección de fuentes vs síntesis, verificación de citas).
      - Flujo de sincronización oficial BOE e indexación atómica con cambio seguro de puntero en SQLite.
    - Tabla comparativa de decisiones técnicas y compensaciones de arquitectura (Python nativo vs LangChain/LangGraph, XML estructurado vs PDF, Qdrant + SQLite, modelo local Ollama vs APIs de pago).
    - Mapeo del corpus oficial de 4 normas europeas/nacionales (`eu_ai_act`, `rgpd`, `dsa`, `nis2`).
    - Guías de reproducción rápida: local con `uv` y contenedorizada con `docker compose`.
    - Documentación de la API REST y Single Page Application interactiva.
  - Auditoría de archivos `.md`: confirmada la idoneidad de conservar todos los archivos de `docs/` (informes empíricos de generación, selección de contexto y multi-query) y de gestión (`PROJECT_PLAN.md`, `TODO.md`, `AGENTS.md`) como evidencia de madurez técnica. `ESTUDIAR.md` permanece local e ignorado por Git.
  - [PROJECT_PLAN.md](PROJECT_PLAN.md) actualizado con los criterios del Hito 13 completados.

- **Sincronización del corpus oficial (4 documentos) y resiliencia en API completada (PR #9 en GitHub):**
  - Identificadores oficiales y catálogo normativo en `src/rag_bogado/ingestion/corpus.py`:
    - `eu_ai_act`: `DOUE-L-2024-81079` (Reglamento de Inteligencia Artificial)
    - `rgpd`: `BOE-A-2018-16673` (LOPDGDD / RGPD)
    - `dsa`: `DOUE-L-2022-81573` (Reglamento de Servicios Digitales)
    - `nis2`: `DOUE-L-2022-81963` (Directiva de Ciberseguridad NIS 2)
  - Soporte `DOUE-L-*` en `BoeClient` vía `xml.php` y extracción robusta de `<texto>` en `xml_loader.py`.
  - Sincronización automática no bloqueante en el arranque (`lifespan`) de FastAPI y endpoint manual `POST /api/documents/sync`.
  - Selector dinámico de normas y estado de sincronización en la interfaz web (`index.html` y `app.js`), predeterminado en «Todo el corpus (4 normas activas)» y con cache-busting en assets estáticos (`?v=3`).
  - Auto-arranque y parada limpia de Ollama en `lifespan` de FastAPI. Si se detuviera de forma imprevista durante una consulta, `/ask` degrada a HTTP 503 accionable.
  - Modo multicanal en `query_active` y `/ask`: soporte para `document_id="all"` que recupera y ordena candidatos de las 4 normas activas simultáneamente.
  - Catálogo local con los 4 documentos indexados y activos.
  - Pull Request #9 abierto y CI en GitHub Actions verificado en verde (2 checks aprobados).

- **Hito 11 (LangGraph / Agentes):** Relegado a hitos futuros/opcionales por decisión de alcance.

## Próximas tareas, por orden

### 1. Fusión de PR #9 y sincronización de `main`
- **Objetivo:** Integrar la rama `feat/corpus-boe-sync` en `main` tras la verificación remota de CI.
- **Cierre:** Rama `main` actualizada con todo el corpus y la documentación del portfolio.

### 2. Comprobación estática de tipos y observabilidad (Hitos 12 y 12B)
- **Objetivo:**
  - Evaluar `mypy` / `pyright` sobre el código fuente de `src/`.
  - Añadir logs estructurados con tiempos de latencia y versión consultada en endpoints del API.
- **Archivos:** `pyproject.toml`, `src/rag_bogado/api/app.py`.
- **Cierre:** Chequeo estático de tipos sin errores en CI y métricas estructuradas disponibles.

## Comprobaciones y entrega

- 2026-09-18: `uv run pytest`, **173 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Aceptación registrada en `PROJECT_PLAN.md` y `README.md`.
- Rama: `feat/corpus-boe-sync`.
- Pull Request #9: https://github.com/tvarmar/rag-bogado/pull/9 (CI verificado en verde).
- `ESTUDIAR.md` local e ignorado por Git.

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
