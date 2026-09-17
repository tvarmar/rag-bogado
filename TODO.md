# Pendientes para próximas sesiones

Actualizado: 2026-09-17. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Iniciar el **Hito 8 — Interfaz de usuario** ([PROJECT_PLAN.md](PROJECT_PLAN.md)):
1. Diseñar el frontend mínimo (HTML/JS servido por FastAPI o componente ligero) para interactuar con la API local:
   - Campo de entrada para la pregunta del usuario y selector de documento activo.
   - Selector de modo de respuesta (`synthesis` vs `evidence`) y número de búsquedas (`search_count`).
2. Visualización estructurada:
   - Descomposición en preguntas individuales con sus estados (`answered`, `abstained`, `review_rejected`, `error`).
   - Bloque de respuesta con citas interactivas vinculadas al panel de fuentes.
   - Panel lateral o modal con el texto íntegro del pasaje recuperado, artículo normativo y localizador.
   - Mensajes explicativos claros ante falta de evidencia o rechazo de soporte.
3. Tests de integración y validación visual.

## Estado actual

- **Hito 7 completado y aceptado (2026-09-17):**
  - Añadidas dependencias `fastapi`, `uvicorn` y `httpx` (dev) mediante `uv`.
  - Servicio FastAPI modular en `src/rag_bogado/api/app.py` con factoría `create_app()` e inyección de dependencias para desacoplar catálogo, generador y función de búsqueda.
  - Endpoint `GET /health` reportando disponibilidad de SQLite y lista de documentos normativos activos.
  - Endpoint `POST /ask` procesando consultas con descomposición de preguntas, multi-query RRF, selección de contexto, modos de respuesta (`synthesis` / `evidence`) y metadatos completos de citas.
  - Modelos Pydantic en `src/rag_bogado/api/schemas.py` con validación estricta y generación de documentación OpenAPI interactiva en `/docs` y `/redoc`.
  - Logging estructurado bajo el logger `rag_bogado.api`.
  - 8 tests deterministas en `tests/test_api.py` cubriendo casos de éxito, 404 (documento inexistente), 422 (validación de entrada), degradación de catálogo y OpenAPI. Total de la suite: 136 tests pasando.
- **Hitos 5 y 6 completados y aceptados:**
  - Casos `d01` a `d09` evaluados y documentados en [docs/development-review.md](docs/development-review.md).
  - Selección de contexto, política *fail-closed*, abstención segura y multi-query RRF consolidados.

## Próximas tareas, por orden

### 1. Hito 8 — Interfaz de usuario (activa)
- **Objetivo:** Proporcionar una interfaz web interactiva para realizar preguntas, visualizar respuestas, examinar fuentes originales y distinguir claramente preguntas respondidas de abstenciones.
- **Archivos:** `src/rag_bogado/ui/` o frontend integrado en `src/rag_bogado/api/`.
- **Siguiente acción:** Diseñar la interfaz mínima y conectarla con los endpoints `GET /health` y `POST /ask`.
- **Cierre:** Consulta completa desde navegador con apertura y verificación visual de fuentes exactas.

### 2. Hito 9 — Docker (pendiente)
- **Objetivo:** Empaquetar el servicio API y el almacén Qdrant mediante Docker y Docker Compose para ejecución reproducible.
- **Archivos:** `Dockerfile`, `docker-compose.yml`.
- **Cierre:** `docker compose up` arrancando los servicios interconectados con persistencia por volumen.

### 3. Hito 10 — Fuentes oficiales y actualización (pendiente)
- **Objetivo:** Sincronización automática con la API del BOE y EUR-Lex para detectar cambios normativos y reindexar bajo demanda.
- **Archivos:** Adaptadores de sincronización e ingesta.

## Comprobaciones y entrega

- 2026-09-17: `uv run pytest`, **136 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Aceptación formal del Hito 7 registrada en `PROJECT_PLAN.md` y estructura documentada en `README.md`.
- Rama: `feat/fastapi-api`.
- [PR #5](https://github.com/tvarmar/rag-bogado/pull/5) abierto en GitHub; CI verificado y superado al 100% (2/2 checks exitosos).
- `ESTUDIAR.md` revisado, local e ignorado por Git. Conservar sin marcar conceptos como aprendidos solo por haberlos implementado.

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
