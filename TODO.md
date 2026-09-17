# Pendientes para próximas sesiones

Actualizado: 2026-09-17. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Iniciar el **Hito 7 — API con FastAPI** ([PROJECT_PLAN.md](PROJECT_PLAN.md)):
1. Añadir dependencias de `fastapi` y `httpx` (para test client) vía `uv add`.
2. Crear módulo de API en `src/rag_bogado/api/`:
   - Endpoint de salud: `GET /health`.
   - Endpoint de consulta: `POST /ask` recibiendo la pregunta y devolviendo la respuesta estructurada (síntesis o fragmentos literales, fuentes con metadatos de versión y localizadores, citas y estados de abstención/error).
3. Modelos Pydantic para peticiones y respuestas, garantizando validación estricta y documentación OpenAPI interactiva (`/docs`).
4. Tests deterministas en `tests/test_api.py` utilizando fakes para simular el servicio de consulta sin requerir LLM ni modelos pesados en CI.

## Estado actual

- **Hitos 5 y 6 completados y aceptados (2026-09-17):**
  - Los 9 casos de desarrollo (`d01` a `d09` de `development-review.json`) han sido evaluados y documentados en [docs/development-review.md](docs/development-review.md).
  - Selección de contexto refinada (`max_passages=5`, exclusión de considerandos si hay artículos, margen relativo `relative_margin=0.025`): probada en vivo eliminando el ruido periférico y preservando citas directas a artículos normativos.
  - Respaldo estricto y ausencia de alucinaciones verificado en `d01`, `d02`, `d03` y `d06`.
  - Política de seguridad *fail-closed* observada en `d04` y `d05`: ante afirmaciones que no superan la revisión estricta de soporte, el sistema rechaza el borrador y se abstiene de forma segura (`review_rejected` / `insufficient_evidence`).
  - Descomposición y cobertura verificada en preguntas compuestas (`d03`) y explícitas (`d06`).
  - Abstención robusta ante falta de evidencia verificada en `d07` (caso mixto: responde la parte jurídica y declara explícitamente la abstención en el dato privado), `d08` (negativo cercano: número de teléfono del DPD) y `d09` (negativo fuera de dominio: receta de cocina), sin recurrir a la memoria paramétrica del LLM.
- **Fuentes estructuradas oficiales en XML:**
  - Migración completa de PDF a XML oficial en `src/rag_bogado/ingestion/xml_loader.py`.
  - Catálogo Qdrant activo sobre `eu_ai_act.xml` (versión 3, 773 chunks estructurados por artículos, considerandos y anexos).

## Próximas tareas, por orden

### 1. Hito 7 — API con FastAPI (activa)
- **Objetivo:** Exponer el servicio de consulta RAG como API HTTP local para dar paso a la interfaz (Hito 8).
- **Archivos:** `src/rag_bogado/api/`, `tests/test_api.py`, `pyproject.toml`.
- **Siguiente acción:** Añadir `fastapi` y `httpx` vía `uv add`, implementar endpoints `/health` y `/ask` con esquemas Pydantic y tests de integración con TestClient.
- **Cierre:** Endpoints funcionando con validación de entrada/salida y tests deterministas pasando en CI.

### 2. Hito 8 — Interfaz de usuario (pendiente)
- **Objetivo:** Proporcionar una interfaz web interactiva que permita al usuario realizar preguntas, ver la síntesis, examinar las fuentes originales y comprobar qué parte quedó sin evidencia.
- **Archivos:** `src/rag_bogado/ui/` o frontend integrado.
- **Siguiente acción:** Definir tecnología mínima (HTML/JS ligero servido por FastAPI o framework liviano) tras completar la API.
- **Cierre:** Consulta completa desde navegador con apertura y verificación de fuentes exactas.

## Comprobaciones y entrega

- 2026-09-17: `uv run pytest`, **128 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Verificación cualitativa de `d01` a `d09` registrada en `docs/development-review.md`
  y aceptación formal de Hitos 5 y 6 en `PROJECT_PLAN.md`.
- Rama: `feat/local-generation`.
- Push autorizado por la usuaria; verificación de CI pendiente tras el push.
- Mantener [PR #4](https://github.com/tvarmar/rag-bogado/pull/4) como borrador.
- `ESTUDIAR.md` revisado, local e ignorado por Git. No publicar ni marcar conceptos
  como aprendidos solo por haberlos implementado.

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
