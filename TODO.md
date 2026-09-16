# Pendientes para próximas sesiones

Actualizado: 2026-09-16. Pendientes operativos; arquitectura y aceptación en
[PROJECT_PLAN.md](PROJECT_PLAN.md), mapa en [README.md](README.md).

## Primera acción

Revisar d03 Q1 en [el experimento de síntesis](docs/synthesis-replay.md), comparar
cada afirmación con su cita y clasificar respaldo, pertinencia y condiciones.
Conservar las fuentes fijas para probar después un único cambio de selección de
contexto o revisión. El objetivo inmediato es evitar información periférica
aceptada por el revisor; no seguir ajustando el prompt sin comparación controlada.

## Estado actual

- Recuperación original + reformulación y RRF implementadas, con hasta diez fuentes.
- Separación de preguntas revisada: acciones coordinadas se mantienen juntas;
  una única pregunta conserva la entrada literal. Rechazo, abstención y error
  se muestran por separado, sin ocultar las otras preguntas.
- Batería de nueve casos de desarrollo y replay de fuentes guardadas disponibles.
  El replay bloquea pérdida de fuentes por presupuesto antes de llamar al modelo.
- El prompt compacto mejora condiciones en d02/d03 y cobertura/citas en d03 Q2
  en las ejecuciones observadas. d03 Q1 aún incluye información periférica y una
  enumeración truncada que el revisor acepta. Síntesis experimental, no aceptada.
- El modo literal sigue siendo la protección provisional. El producto objetivo
  es una síntesis comprensible con fuentes; aceptación de hitos 5/6 pendiente.
  API e interfaz vendrán después de esa revisión.

## Próximas tareas, por orden

### 1. Resolver pertinencia y falsos positivos de síntesis

- **Evidencia:** `src/rag_bogado/evaluation/reports/synthesis-replay-2026-09-16.json`:
  d03 Q1 conserva las condiciones del pasaje principal, pero añade considerandos
  periféricos. El revisor también aprobó omisiones de condiciones en el baseline.
- **Archivos candidatos:** `src/rag_bogado/generation/generator.py`, `support.py`
  en esa carpeta; `tests/test_generation.py`, `tests/test_support.py` y
  `scripts/review_saved_answer.py`. No hay una única causa confirmada.
- **Siguiente acción:** clasificar afirmaciones y fuentes; contrastar ejemplos
  positivos y negativos de desarrollo, comparar un cambio con las mismas fuentes
  y repetir las ejecuciones. Valorar falsos rechazos además de falsas aprobaciones.
- **Cierre:** respaldo, pertinencia y condiciones revisados en ejemplos variados
  y repeticiones. No dar por fiable la síntesis por pasar otro juez ni compensar
  afirmaciones sin respaldo con una nota media. No prometer cero alucinaciones.

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

- 2026-09-16: `.venv/bin/pytest`, **134 aprobados**; `.venv/bin/ruff check .`,
  `.venv/bin/ruff format --check .` y `git diff --check`, correctos.
  Enlaces relativos, rutas y JSON de informes revisados. Sin tests fallidos pendientes.
- Siete ejecuciones de síntesis guardadas, incluidas variantes descartadas.
  No se ejecutó held-out ni se estableció fiabilidad entre repeticiones o latencia
  comparable. No repetir estas evaluaciones para un cambio solo documental.
- Rama: `feat/local-generation`. Entrega local de esta sesión identificada por
  el commit `fix: preserve question coverage and improve synthesis review`.
  Incluye código, tests, documentación e informes pendientes de las últimas sesiones.
- Sin push: la usuaria ha solicitado commit local. Publicación y CI de esta entrega
  pendientes. Última comprobación remota en esta conversación: PR #4 abierta como
  borrador, head `5fab572`, checks correctos; no cubre la entrega local.
- Mantener [PR #4](https://github.com/tvarmar/rag-bogado/pull/4) como borrador.
  Al autorizar publicación, hacer push y verificar CI del último commit publicado.
- No hay bloqueos de entorno confirmados. Runtime y pesos ya instalados; comprobar
  disponibilidad y arrancar con `bash scripts/serve_ollama.sh` si hace falta.
- `ESTUDIAR.md` revisado, local e ignorado por Git. No publicar ni marcar conceptos
  como aprendidos solo por haberlos implementado.

Seguir [AGENTS.md](AGENTS.md) al cerrar: registrar fallos reproducibles con archivos,
siguiente diagnóstico y criterio de cierre; retirar lo resuelto después de verificarlo.
