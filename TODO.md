# Pendientes para próximas sesiones

Actualizado: 2026-09-14. Fuente operativa de pendientes; los objetivos completos
están en [PROJECT_PLAN.md](PROJECT_PLAN.md) y el mapa en [README.md](README.md).

## Punto de partida

- Síntesis local y recuperación por pregunta implementadas; aceptación de calidad
  de los hitos 5/6 pendiente. API e interfaz vendrán después de esa revisión.
- Rama de entrega: `feat/local-generation`, PR #4 (borrador).
- Entrega del 2026-09-14 publicada en [PR #4](https://github.com/tvarmar/rag-bogado/pull/4),
  que sigue como borrador: implementación e informes en `8ed3161`.
  Estas notas se publican en un commit documental posterior en la misma rama.
  CI estaba en ejecución al redactar el cierre; comprobar el último head en GitHub
  al retomar, sin asumir que los checks de un commit anterior lo cubren.
- Primera acción de la próxima sesión: revisar [el flujo implementado](docs/multi-query.md)
  y los informes `multi-query-evidence.json` y `multi-query-synthesis.json` en
  `src/rag_bogado/evaluation/reports/`. Completar la valoración humana de respuestas
  y fidelidad de reformulaciones antes de ajustar la política.
- Implementado: original + una reformulación, unión RRF, hasta diez fuentes finales,
  identidad documental y citas por pregunta. Default conservador: pasajes literales;
  `--answer-mode synthesis` conserva la síntesis experimental con revisión obligatoria.
- No repetir instalación: el runtime y los pesos estaban guardados localmente.
  Para una evaluación real, comprobar disponibilidad y arrancar, si hace falta,
  con `bash scripts/serve_ollama.sh`.

## Tests y comprobaciones

No hay tests automatizados fallidos documentados. Última verificación del 2026-09-14:
`uv run pytest`: **125 aprobados**; `.venv/bin/ruff check .` y
`.venv/bin/ruff format --check .`: correctos. `git diff --check`: correcto.

Evaluaciones reales: dos matrices de seis ejecuciones (una/dos búsquedas para
preguntas simple, compuesta y mixta), doce respuestas por modo. Guardadas en
`src/rag_bogado/evaluation/reports/multi-query-{evidence,synthesis}.json`.
Todos los textos devueltos en modo literal coinciden exactamente con sus citas.
La síntesis tuvo falsos positivos del revisor: no está aceptada como fiable.
No se ejecutaron casos held-out. La comparación anterior de contexto se conserva.

Comandos de referencia:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Si falla un test, registrar aquí: fecha, comando y nodo `archivo::test`, error
observado, archivo de implementación confirmado o candidato, siguiente diagnóstico
y criterio de cierre. Si impide ejecutar la suite, clasificarlo como bloqueo de
entorno. Quitar la entrada tras verificar la corrección.

## Trabajo completado en esta sesión

- Separación de documentación: mapa de archivos, plan, TODO e historial.
- Diagnóstico y comparación de selección de contexto conservados como referencia.
- Original + una reformulación, fusión RRF, trazabilidad y comparación de una/dos búsquedas.
- Respuestas literales por defecto y síntesis experimental con revisión por afirmación.
- Rúbrica de evaluación, informes reales y tests de regresión; 125 tests aprobados.
- Apuntes locales de estudio sobre reformulación, RRF, evaluación y límites del juez LLM.

Este resumen fija el punto de partida; la lista de abajo contiene solo pendientes.

## Próximas tareas, por orden

### 1. Evaluar fidelidad y utilidad de las reformulaciones

- **Estado:** las dos búsquedas y RRF están implementadas sin reglas por pregunta
  o artículo. Se conservan los resultados exclusivos y se evita contar dos veces
  una reformulación idéntica. Máximo diez fuentes dentro del presupuesto existente.
- **Hallazgo:** todas las reformulaciones del experimento literal repitieron la
  original. Su brazo nominal de dos búsquedas ejecutó una; no demuestra una mejora.
  El experimento de síntesis sí produjo una reformulación distinta de alfabetización,
  con posible aumento del grado de obligación («procurar» → «garantizar»).
- **Revisar:** `src/rag_bogado/generation/multi_query.py`,
  `scripts/evaluate_multi_query.py`, `tests/test_multi_query.py` y los informes.
- **Siguiente acción:** añadir preguntas de desarrollo variadas y valorar fidelidad,
  evidencia útil, cobertura y latencia con la ficha; mantener las reservadas intactas.
- **Cierre:** comparación con reformulaciones fieles y distintas, sin privilegiar
  artículos ni exigir una respuesta textual específica. No declarar calibrados umbrales.

### 2. Resolver los falsos positivos del revisor de síntesis

- **Fallo medido:** el revisor aprueba una afirmación de alfabetización sin las
  condiciones del original y una obligación de preparación inferida de un fragmento
  cortado. Temperatura cero tampoco produjo veredictos idénticos en repeticiones.
- **Protección implementada:** el modo por defecto solo permite IDs y copia íntegro
  el chunk citado. No incorpora redacción factual del LLM. Esto verifica procedencia,
  pero no pertinencia, contexto completo ni aplicabilidad jurídica.
- **Revisar:** `src/rag_bogado/generation/support.py`, `generator.py` en esa carpeta,
  `tests/test_support.py`, `tests/test_generation.py`, informe `multi-query-synthesis.json`.
- **Siguiente acción:** revisión humana de falsos positivos y falsos rechazos con la
  ficha. La síntesis es explícitamente experimental; no promoverla por pasar otro juez.
- **Cierre:** respaldo y condiciones revisados en ejemplos variados. No usar una nota
  media para compensar afirmaciones no respaldadas ni prometer cero alucinaciones.

### 3. Evitar dividir una enumeración de sujetos en varias preguntas

- **Fallo semántico observado:** una petición sobre dos categorías de sujetos
  puede separarse de más. La comparación y la consulta simple medidas se conservan.
- **Revisar/candidatos:** `src/rag_bogado/generation/questions.py`,
  `tests/test_question_workflow.py`, `scripts/evaluate_question_workflow.py`,
  `src/rag_bogado/evaluation/reports/question-workflow.json`.
- **Siguiente acción:** recuperar el ejemplo fallido del informe y comparar con
  preguntas compuestas reales. Un fake determinista no valida la fidelidad del LLM.
- **Cierre:** evaluación real que conserve la enumeración como una petición sin
  perder separación de preguntas independientes, citas propias ni errores parciales.

### 4. Ampliar evaluación y fijar criterios de aceptación

- **Revisar/candidatos:** `src/rag_bogado/evaluation/datasets/generation.json`,
  `src/rag_bogado/evaluation/datasets/questions.json`,
  `src/rag_bogado/evaluation/metrics.py`, `scripts/evaluate_generation.py`,
  `src/rag_bogado/evaluation/README.md`.
- **Siguiente acción:** añadir ejemplos revisados de desarrollo y pasajes
  relevantes/irrelevantes. Calibrar cualquier umbral solo tras medir; reservar los
  casos held-out hasta fijar la política y después evaluarlos una vez.
- **Cierre:** criterios acordados y resultados de respaldo, cobertura, abstención
  y latencia documentados antes de dar por aceptados los hitos 5/6.

## Entrega y bloqueos

- [ ] Mantener PR #4 como borrador mientras siga pendiente la aceptación semántica.
  Verificar CI del último head antes de proponer un merge.
- Código, documentación e informes publicados en `8ed3161`; cierre documental
  en la misma PR. No hay una publicación de implementación pendiente.
- `ESTUDIAR.md` permanece local e ignorado por Git; no forma parte de la publicación.
- No hay otros bloqueos de entorno confirmados. Las evaluaciones reales requieren
  corpus, índice y modelo locales; los tests deterministas no los necesitan.

## Cómo mantener esta lista

Conservar solo trabajo pendiente. Para cada nueva tarea: prioridad, problema,
evidencia/comando, archivos a revisar o corregir, siguiente acción y criterio de
cierre. Indicar hipótesis y dependencias. Mover decisiones duraderas al plan o a
una guía; resultados históricos útiles al historial. Seguir [AGENTS.md](AGENTS.md)
al finalizar y revisar también `ESTUDIAR.md` cuando esté disponible localmente.
