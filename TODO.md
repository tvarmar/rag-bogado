# Pendientes para próximas sesiones

Actualizado: 2026-09-17. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Revisar y entregar el **Hito 9 — Docker** ([PROJECT_PLAN.md](PROJECT_PLAN.md)):
1. Confirmar con la usuaria la entrega en la rama `feat/docker-containerization` (commit, push y apertura de PR).
2. Nota de entorno: Docker no está instalado en el WSL/Windows local; la configuración está 100% testeada con tests deterministas (`tests/test_docker_setup.py`) y lista para ejecutarse con `docker compose up --build` una vez instalado Docker Desktop o Docker Engine.
3. Tras la fusión en `main`, iniciar el **Hito 10 — Fuentes oficiales y actualización**:
   - Adaptador para la API de datos abiertos del BOE.
   - Consulta de metadatos, descarga por hash y reindexación atómica validada.

## Estado actual

- **Hito 9 completado y verificado (2026-09-17):**
  - `Dockerfile` optimizado y reproducible con construcción multietapa (*multi-stage build*), `uv`, Python 3.12 slim, usuario no privilegiado (`appuser`), comprobación de salud (*healthcheck*) periódica en `/health` y servidor Uvicorn en puerto 8000.
  - `docker-compose.yml` orquestando los servicios `rag-bogado-api` y `qdrant` (oficial v1.13.2) con volúmenes persistentes para `./data/catalog`, `./data/qdrant` y `./data/cache`, resolución DNS interna, healthcheck condicional (`service_healthy`) y acceso al Ollama del host mediante `host.docker.internal`.
  - `.dockerignore` exhaustivo excluyendo cachés, entornos virtuales y datos locales temporales.
  - Adaptabilidad de la base de código mediante variables de entorno:
    - `CATALOG_PATH` y `STATIC_DIR` en `src/rag_bogado/api/app.py`.
    - `QDRANT_URL` y conexión remota por URL/host/puerto en `src/rag_bogado/retrieval/vector_store.py` y `src/rag_bogado/indexing/service.py`.
    - `OLLAMA_BASE_URL` y `OLLAMA_HOST` en `src/rag_bogado/generation/generator.py`.
  - Tests deterministas en `tests/test_docker_setup.py`, `tests/test_vector_store.py`, `tests/test_generation.py`, `tests/test_api.py` y `tests/test_catalog.py`. Total suite: **146 tests pasando**.
- **Hito 8 completado y fusionado en `main`:**
  - Interfaz web interactiva y responsive servida en `/` por FastAPI, modo evidencia literal y presentación estructurada de listas y cláusulas jurídicas.
- **Hito 7 completado y fusionado en `main`:**
  - API REST FastAPI con schemas Pydantic y endpoints `/health` y `/ask`.
- **Hitos 5 y 6 completados y aceptados:**
  - Casos `d01` a `d09` evaluados; abstención *fail-closed* y multi-query RRF operativos.

## Próximas tareas, por orden

### 1. Hito 9 — Docker (cierre y entrega)
- **Objetivo:** Abrir PR de `feat/docker-containerization` a `main`, validar CI y fusionar.
- **Archivos:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `src/`, `tests/`, `README.md`, `PROJECT_PLAN.md`.
- **Cierre:** CI en verde en GitHub y PR fusionado.

### 2. Hito 10 — Fuentes oficiales y actualización (pendiente)
- **Objetivo:** Sincronización automática con la API del BOE y EUR-Lex para detectar cambios normativos, descargar XML consolidado e indexar bajo demanda.
- **Archivos:** `src/rag_bogado/ingestion/` (adaptador BOE).
- **Cierre:** Consulta de metadatos, descarga por hash y reindexación atómica validada.

### 3. Hito 11 — Comparación con LangGraph (pendiente)
- **Objetivo:** Implementar un motor alternativo con LangGraph para comparar la orquestación basada en grafos con el pipeline nativo.

## Comprobaciones y entrega

- 2026-09-17: `uv run pytest`, **146 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Aceptación formal del Hito 9 registrada en `PROJECT_PLAN.md` y documentación en `README.md`.
- Rama: `feat/docker-containerization`.
- `ESTUDIAR.md` ampliado con fundamentos de Docker, multi-stage builds, redes bridge y volúmenes (local e ignorado por Git).

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
