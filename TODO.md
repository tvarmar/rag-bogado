# Pendientes para próximas sesiones

Actualizado: 2026-09-17. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Evaluar la fidelidad y utilidad de las reformulaciones en casos de desarrollo variados
([src/rag_bogado/generation/multi_query.py](src/rag_bogado/generation/multi_query.py),
[scripts/evaluate_multi_query.py](scripts/evaluate_multi_query.py)).
Analizar si la reformulación altera el deber normativo («procurar» vs. «garantizar»)
y comparar cobertura, evidencia útil y latencia entre una y dos búsquedas.

## Estado actual

- Recuperación original + reformulación y RRF implementadas, con hasta 5 fuentes por defecto.
- Selección de contexto refinada (`src/rag_bogado/generation/generator.py`):
  1) `max_passages` reducido de 10 a 5;
  2) filtrado estricto de considerandos (`recital`) cuando existen artículos normativos (`article`) en los resultados;
  3) filtro por margen relativo (`relative_margin=0.025`): cuando el mejor resultado tiene alta relevancia (score >= 0.85), se descartan pasajes con puntuación inferior a `max_score - relative_margin`.
- Verificado en vivo en `d01`, `d02` y `d03` con XML oficial y `qwen3:4b-instruct` (2026-09-17):
  - En d01 (`simple`): selecciona exclusivamente el Artículo 4 (score 0.8918); se eliminan considerandos (20, 21, 56) y Artículo 66 por margen. Una única afirmación limpia respaldada al 100% con calificaciones completas.
  - En d02 (`paraphrase`): se descartan todos los considerandos; la síntesis cita exclusivamente el Artículo 4 ignorando el solapamiento de Anexo III y los artículos 54 y 14.
  - En d03 (`compound`): Q1 selecciona exclusivamente el Artículo 4 (score 0.8918); Q2 selecciona exclusivamente fragmentos del Artículo 11 y Artículo 18.
  - Multi-query: en d01 la reformulación aumentó la obligación («procurar» → «garantizar»), aunque ambas recuperaron Art. 4 como #1; en d02 la reformulación repitió la original y evitó una segunda búsqueda redundante.
- Migración completa de PDF a XML oficial (`src/rag_bogado/ingestion/xml_loader.py`):
  eliminado PyMuPDF (`pymupdf`), eliminado `loader.py` y `chunk_page`. Ahora se parsean
  unidades semánticas (`LegalUnit`: artículos, considerandos y anexos) y se dividen
  respetando oraciones completas y prefijos jurídicos. Integrados metadatos (`article`,
  `unit_type`) en Qdrant.
- El modo literal sigue siendo la protección provisional. El producto objetivo
  es una síntesis comprensible con fuentes; aceptación de hitos 5/6 pendiente.
  API e interfaz vendrán después de esa revisión.

## Próximas tareas, por orden

### 1. Pertinencia y selección de contexto resueltas en d01, d02 y d03 (verificado)

- **Evidencia y resolución:** d01 y d03 Q1 incluían considerandos periféricos porque se enviaban
  hasta 10 pasajes sin discriminación de unidades normativas. Con `max_passages=5`, exclusión estricta de
  considerandos (`recital`) cuando existen artículos (`article`), y filtrado por margen
  relativo (`relative_margin=0.025` cuando `max_score >= 0.85`), se verificó en vivo:
  d01 selecciona únicamente Artículo 4 (score 0.8918); d02 cita exclusivamente Artículo 4;
  d03 Q1 selecciona únicamente Artículo 4 y Q2 Artículos 11 y 18.
- **Archivos:** `src/rag_bogado/generation/generator.py`, `tests/test_generation.py`,
  `src/rag_bogado/generation/__main__.py`, `docs/development-review.md`.
- **Cierre:** ausencia de considerandos periféricos verificada en preguntas sobre obligaciones
  normativas con artículos directos. Citas y calificaciones preservadas sin alucinaciones. Resuelto.

### 2. Evaluar fidelidad y utilidad de las reformulaciones

- **Evidencia:** las reformulaciones del experimento literal repiten la original;
  no demuestran una mejora por dos búsquedas. Una reformulación de síntesis podría
  aumentar la obligación («procurar» → «garantizar»). d02 A/B coinciden.
- **Archivos:** `src/rag_bogado/generation/multi_query.py`,
  `scripts/evaluate_multi_query.py`, `tests/test_multi_query.py` y los informes
  `multi-query-{evidence,synthesis}.json` en el paquete de evaluación.
- **Siguiente acción:** preguntas variadas de desarrollo con reformulaciones
  distintas; comparar fidelidad, evidencia útil, cobertura y latencia.
- **Cierre:** comparación con reformulaciones fieles y distintas, sin reglas por
  artículo ni respuesta textual obligatoria. No declarar calibrados umbrales.

### 3. Comprobar generalización y cobertura de preguntas compuestas

- **Evidencia:** nueve casos de desarrollo preservan sus peticiones en la
  descomposición; la última síntesis de d03 Q2 cubre preparación y actualización.
  Eso no acredita generalización ni cobertura de otras preguntas.
- **Archivos:** `src/rag_bogado/generation/questions.py`, `service.py` en esa carpeta,
  `scripts/evaluate_multi_query.py --split-only`, `tests/test_question_workflow.py`.
- **Siguiente acción:** añadir entradas de desarrollo y revisar por separado
  descomposición y cobertura de cada aspecto en la respuesta final.
- **Cierre:** todas las peticiones conservadas y cada aspecto respondido o señalado
  explícitamente como pendiente, incluidos rechazos y errores.

### 4. Completar revisión humana y criterios de aceptación

- **Pendiente humano:** en d01 la redacción gustó y la recuperación se consideró
  pertinente, pero el respaldo no está aprobado. Comentario global de d02/d03
  pendiente; no exigir puntuaciones caso por caso. Las observaciones del asistente
  del 16 de septiembre no sustituyen esa valoración.
- **Archivos:** `docs/development-review.md`, `docs/development-review-batch.md`,
  `src/rag_bogado/evaluation/reports/development-review-progress.json`, datasets
  `generation.json` y `questions.json`, `metrics.py` y `README.md` del paquete de
  evaluación; `scripts/evaluate_generation.py`.
- **Siguiente acción:** ampliar ejemplos revisados y acordar criterios de respaldo,
  cobertura, abstención y latencia. Calibrar umbrales solo después de medir.
- **Cierre:** política fijada y evaluación final de casos reservados una vez;
  resultados documentados antes de aceptar hitos 5/6. Mantener held-out intacto
  durante el desarrollo.

## Comprobaciones y entrega

- 2026-09-17: `uv run pytest`, **128 aprobados**; `uv run ruff check .`,
  `uv run ruff format --check .` y `git diff --check`, correctos.
  Verificación cualitativa de `d01` y `d02` registrada en `docs/development-review.md`.
- Rama: `feat/local-generation`.
- Push autorizado por la usuaria; verificación de CI pendiente tras el push.
- Mantener [PR #4](https://github.com/tvarmar/rag-bogado/pull/4) como borrador.
- `ESTUDIAR.md` revisado, local e ignorado por Git. No publicar ni marcar conceptos
  como aprendidos solo por haberlos implementado.

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
