# Pendientes para próximas sesiones

Actualizado: 2026-09-17. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Iniciar el **Hito 9 — Docker** ([PROJECT_PLAN.md](PROJECT_PLAN.md)):
1. Crear `Dockerfile` optimizado y reproducible para `rag-bogado` (Python 3.12, dependencias `uv`).
2. Crear `docker-compose.yml` para orquestar la arquitectura local:
   - Contenedor `rag-bogado-api` exponiendo puerto 8000.
   - Contenedor `qdrant` oficial exponiendo puerto 6333.
   - Volúmenes persistentes para `data/qdrant` y `data/catalog`.
3. Variables de entorno para parametrizar hosts, rutas y puertos.
4. Validar ejecución y ciclo de vida con `docker compose up` y tests automatizados.

## Estado actual

- **Hito 8 completado y aceptado (2026-09-17):**
  - Interfaz web interactiva y responsive servida en `/` por FastAPI desde `src/rag_bogado/api/static/` (`index.html`, `styles.css`, `app.js`).
  - Formulario de consulta con selector dinámico de normas activas (conectado a `GET /health`), selector de modo (`evidence` vs `synthesis`), control de búsquedas (1 o 2 RRF) y control de top-k.
  - Desglose visual de aspectos y subpreguntas con estados semánticos claros: respondida con evidencia, abstención por falta de evidencia (`insufficient_evidence`) y rechazo de soporte (`review_rejected`).
  - Bloque de respuesta con citas interactivas (`Q1-S1`) que resaltan y hacen scroll automático hacia el pasaje de evidencia correspondiente.
  - Panel y modal de fuentes con artículo legal, localizador/página, identificador de chunk y visualización del texto íntegro del pasaje original.
  - Diseño *mobile-first* preparado para acceso multiplataforma y adaptable a pantalla completa en smartphones (PWA / Web App) conectándose a `--host 0.0.0.0`.
  - Tests deterministas en `tests/test_api.py` cubriendo la entrega de HTML y archivos estáticos CSS/JS. Total suite: **139 tests pasando**.
- **Hito 7 completado y fusionado en `main`:**
  - API REST FastAPI con schemas Pydantic, OpenAPI y endpoints `/health` y `/ask` integrados.
- **Hitos 5 y 6 completados y aceptados:**
  - Casos `d01` a `d09` evaluados; abstención *fail-closed* y multi-query RRF operativos.

## Próximas tareas, por orden

### 1. Hito 9 — Docker (activa)
- **Objetivo:** Empaquetar el servicio API y el almacén Qdrant mediante Docker y Docker Compose para ejecución y despliegue reproducible.
- **Archivos:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- **Siguiente acción:** Escribir el `Dockerfile` multietapa con `uv` y definir el `docker-compose.yml`.
- **Cierre:** `docker compose up` levantando ambos servicios interconectados y respondiendo a consultas.

### 2. Hito 10 — Fuentes oficiales y actualización (pendiente)
- **Objetivo:** Sincronización automática con la API del BOE y EUR-Lex para detectar cambios normativos, descargar XML consolidado e indexar bajo demanda.
- **Archivos:** Adaptadores de sincronización e ingesta.
- **Cierre:** Consulta de metadatos, descarga por hash y reindexación atómica validada.

### 3. Hito 11 — Comparación con LangGraph (pendiente)
- **Objetivo:** Implementar un motor alternativo con LangGraph para comparar la orquestación basada en grafos con el pipeline nativo.

## Comprobaciones y entrega

- 2026-09-17: `uv run pytest`, **139 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Aceptación formal del Hito 8 registrada en `PROJECT_PLAN.md` y estructura en `README.md`.
- Rama: `feat/user-interface`.
- [PR #6](https://github.com/tvarmar/rag-bogado/pull/6) abierto en GitHub; CI verificado y superado al 100% (2/2 checks exitosos).
- `ESTUDIAR.md` revisado, local e ignorado por Git. Conservar sin marcar conceptos como aprendidos solo por haberlos implementado.

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
