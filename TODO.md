# Pendientes para próximas sesiones

Actualizado: 2026-09-18. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Documentación y presentación de portfolio (Hito 13):
1. Incorporar en [README.md](README.md) diagramas de arquitectura (flujo de sincronización de fuentes oficiales BOE y pipeline RAG multi-query + RRF con modo evidencia literal y síntesis experimental).
2. Documentar la justificación técnica de diseño (por qué Python nativo vs librerías pesadas, parseo XML vs extracción desestructurada de PDF, y activación atómica fail-safe).
3. Evaluar e integrar comprobación estática de tipos con `mypy` o `pyright` según Hito 12.

## Estado actual

- **Sincronización del corpus oficial (4 documentos) y resiliencia en API completada (2026-09-18, rama `feat/corpus-boe-sync`):**
  - Identificadores oficiales y catálogo normativo en `src/rag_bogado/ingestion/corpus.py`:
    - `eu_ai_act`: `DOUE-L-2024-81079` (Reglamento de Inteligencia Artificial)
    - `rgpd`: `BOE-A-2018-16673` (LOPDGDD / RGPD)
    - `dsa`: `DOUE-L-2022-81573` (Reglamento de Servicios Digitales)
    - `nis2`: `DOUE-L-2022-81963` (Directiva de Ciberseguridad NIS 2)
  - Soporte `DOUE-L-*` en `BoeClient` vía `xml.php` y extracción robusta de `<texto>` en `xml_loader.py`.
  - Sincronización automática no bloqueante en el arranque (`lifespan`) de FastAPI y endpoint manual `POST /api/documents/sync`.
  - Selector dinámico de normas y estado de sincronización en la interfaz web (`index.html` y `app.js`), predeterminado en «Todo el corpus (4 normas activas)» y con cache-busting en assets estáticos (`?v=2`).
  - Auto-arranque de Ollama en `lifespan`: si el demonio de Ollama no está activo al iniciar FastAPI (`uvicorn`), la aplicación lo arranca automáticamente en segundo plano con las variables de entorno correspondientes y lo detiene al apagar el servidor. Si se detuviera de forma imprevista durante una consulta, `/ask` degrada a HTTP 503 accionable.
  - Modo multicanal en `query_active` y `/ask`: soporte para `document_id="all"` que recupera y ordena candidatos de las 4 normas activas simultáneamente.
  - Catálogo local con los 4 documentos indexados y activos.
- **Hito 10 (Sincronización BOE básica) completado y fusionado en `main` (PR #8).**
- **Hito 11 (LangGraph / Agentes):** Relegado a hitos futuros/opcionales por decisión de alcance.

## Próximas tareas, por orden

### 1. Documentación para portfolio y diagramas de arquitectura (Hito 13)
- **Objetivo:**
  - Explicar problema, solución, arquitectura, consideraciones legales y métricas en `README.md`.
  - Añadir diagrama Mermaid del ciclo de vida del dato y pipeline RAG.
- **Archivos:** `README.md`, `docs/`.
- **Cierre:** README claro, visual y preparado para presentación profesional en portfolio.

### 2. Comprobación estática de tipos y observabilidad (Hitos 12 y 12B)
- **Objetivo:**
  - Evaluar `mypy` / `pyright` sobre el código fuente.
  - Añadir logs estructurados con tiempos de latencia y versión consultada en endpoints del API.
- **Archivos:** `pyproject.toml`, `src/rag_bogado/api/app.py`.
- **Cierre:** CI ejecutando chequeo de tipos sin errores y trazas estructuradas disponibles.

## Comprobaciones y entrega

- 2026-09-18: `uv run pytest`, **172 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Aceptación registrada en `PROJECT_PLAN.md` y `README.md`.
- Rama: `feat/corpus-boe-sync`.
- `ESTUDIAR.md` ampliado con sección 10 sobre resiliencia en inferencia (HTTP 503), ciclo de vida con `lifespan` y resolución de identificadores europeos `DOUE-L-*` (local e ignorado por Git).

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
