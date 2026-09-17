
# RAG-Bogado — Project Plan

Este documento mantiene alcance, arquitectura objetivo, herramientas, hitos y criterios
de aceptación. Consultar [TODO.md](TODO.md) para retomar trabajo,
`ESTUDIAR.md` (apuntes locales, ignorados por Git) para teoría y [el historial](docs/session-history.md)
para entregas pasadas. El protocolo de sesión está en [AGENTS.md](AGENTS.md).

## 1. Objetivo del proyecto

**RAG-Bogado** es un sistema RAG (Retrieval-Augmented Generation) orientado a normativa oficial sobre inteligencia artificial, privacidad y protección de datos.

El sistema debe ser capaz de:

- recibir preguntas en lenguaje natural;
- buscar información relevante en documentos oficiales previamente indexados;
- recuperar los fragmentos más relevantes;
- generar opcionalmente una síntesis mediante un LLM;
- mostrar siempre documento, página y fragmento original exacto;
- añadir metadatos jurídicos cuando estén disponibles;
- evitar respuestas jurídicas no respaldadas por la evidencia recuperada;
- incorporar y actualizar, en una fase posterior, documentos desde fuentes oficiales como BOE o EUR-Lex.

El proyecto tiene además un objetivo formativo: practicar una arquitectura Python cercana a producción, no limitarse a notebooks académicos y aprender a justificar las decisiones técnicas.

### Alcance acordado y criterio de aprendizaje

Revisión del plan: 8 de septiembre de 2026. El objetivo es aprender construyendo un producto pequeño que se pueda explicar, probar y medir. Cada etapa debe dejar una demostración funcional y una breve nota de decisiones; incorporar herramientas es útil cuando permite practicar una competencia con un problema concreto.

**MVP local:** un corpus pequeño y explícito de documentos, una interfaz para preguntar, recuperación de evidencia, síntesis con un LLM local y citas verificables. Debe indicar cuándo el corpus no permite responder. No incluye actualización por Internet, agentes ni despliegue cloud. El modo que solo muestra fragmentos sirve como entrega intermedia y alternativa si el equipo no permite ejecutar el LLM con una latencia aceptable; no equivale a completar la generación.

**Producto posterior:** sincronización de un conjunto elegido de normas del BOE, historial de versiones y respuestas que identifiquen qué versión se consultó y cuándo se comprobó la fuente. EUR-Lex será una integración independiente posterior; no se presupone que BOE cubra todo el corpus europeo.

**Coste:** la ejecución habitual debe ser local, sin APIs de pago ni suscripciones. Medir RAM, espacio y latencia antes de elegir el LLM; registrar modelo, licencia y cuantización. Descargar modelos inicialmente requiere conexión. AWS será un laboratorio opcional y temporal, nunca una dependencia del producto ni una promesa de alojamiento gratuito permanente.

### Orden de ejecución revisado

Los números de hito se conservan para mantener las referencias del plan original; el orden de trabajo pasa a ser:

1. Consolidar la base existente y activar CI (hitos 0, 1, 2 y parte del 12).
2. Crear la evaluación mínima sobre el retriever actual (hito 4).
3. Añadir persistencia vectorial y catálogo SQL (hitos 3 y 3B).
4. Integrar LLM y comportamiento sin evidencia conjuntamente (hitos 5 y 6).
5. Conectar API e interfaz y demostrar el MVP local (hitos 7 y 8).
6. Empaquetar, observar y preparar entregas reproducibles (hitos 9 y 12B).
7. Incorporar sincronización y versiones BOE (hito 10).
8. Documentar el portfolio; elegir después experimentos opcionales (hitos 11, 13 y 14).

### Criterios de aceptación del MVP

- [x] Indexar el corpus elegido una vez y consultarlo tras reiniciar sin recalcular todos los embeddings.
- [ ] Preguntar desde la interfaz y recibir una síntesis con fuentes que se puedan abrir y comprobar.
- [x] Identificar documento, versión local y página o localizador aplicable; no inventar páginas para fuentes estructuradas.
- [x] Mostrar una respuesta de evidencia insuficiente en los casos negativos del conjunto de evaluación.
- [x] Ejecutar sin servicios de pago, con instrucciones reproducibles mediante `uv`.
- [x] Publicar resultados de retrieval y revisión de respuestas, incluidos fallos y latencia en el equipo utilizado.
- [x] Mantener CI de tests deterministas y calidad; las evaluaciones con modelos reales se ejecutan por separado.

No se fija un umbral de calidad arbitrario antes de medir: tras la primera evaluación, registrar el objetivo elegido y comprobarlo antes de dar el MVP por cerrado.

---

## 2. Principios de trabajo

> Entender una parte pequeña, implementarla, probarla, medirla y explicar la decisión antes de avanzar.

- Código sencillo antes que abstracciones prematuras.
- Funciones pequeñas para transformaciones puras.
- Clases cuando exista estado, configuración, recursos reutilizables o varias implementaciones intercambiables.
- Separación clara de responsabilidades.
- Tests para comportamiento importante y errores conocidos.
- Metadatos suficientes para rastrear cada respuesta hasta la fuente original.
- El LLM no sustituye la evidencia.
- Los fragmentos originales se muestran independientemente de la síntesis generada.
- Antes de optimizar retrieval, medir su comportamiento.

---

## 3. Arquitectura objetivo

```text
Usuario
  |
  v
API / interfaz
  |
  v
RagService
  |
  +--------------------+
  |                    |
  v                    v
Retriever           LLM / Generator
  |
  v
EmbeddingModel
  |
  v
VectorStore
  |
  v
Qdrant
  ^
  |
Indexer
  ^
  |
Ingestion pipeline
  |
  +--> Loader
  +--> Normalizer
  +--> Chunker
  |
Documentos oficiales
```

La estructura real de ficheros se mantiene en [README.md](README.md#project-structure).
Los módulos futuros se describen en sus hitos; no crearlos antes de necesitarlos.

---

# 4. Roadmap completo

## Hito 0 — Entorno y base profesional

- [x] Crear proyecto con `uv`
- [x] Python 3.12
- [x] Estructura `src/`
- [x] Git
- [x] GitHub
- [x] SSH para GitHub
- [x] pytest
- [x] Ruff
- [x] Configurar Ruff
- [x] Configurar pytest
- [x] Ignorar documentos/datos locales en Git
- [x] Configure GitHub Actions; successful remote checks reported by the user (details in milestone 12).
- [ ] Docker

---

## Hito 1 — Ingesta documental

### Ingesta estructurada (XML oficial) y pivote desde PDF

- [x] Evaluar extracción inicial en PDF y límites de división por página/caracteres
- [x] Decisión de arquitectura (septiembre 2026): migración completa a XML oficial (BOE / EUR-Lex)
- [x] Eliminar dependencia de PyMuPDF y parseo frágil por caracteres/páginas
- [x] Implementar `load_xml()` para extraer unidades jurídicas semánticas (`LegalUnit`)
- [x] Extraer considerandos desde tablas (`recital`)
- [x] Extraer artículos y títulos normativos (`article`)
- [x] Extraer anexos normativos (`annex`)
- [x] Conservar identificador de norma, número y título

### Normalización

- [x] Normalizar espacios horizontales
- [x] Conservar saltos de línea significativos
- [x] Colapsar exceso de líneas vacías
- [x] Limpiar preámbulos y banners de navegadores en XML

### Chunking semántico jurídico

- [x] Crear `Chunk` con metadatos de unidad (`article`, `unit_type`)
- [x] Agrupar párrafos bajo el prefijo normativo (ej. `Artículo 4. Alfabetización...`)
- [x] Subdivisión por oraciones completas respetando puntuación si la unidad excede `max_chunk_size`
- [x] Soportar texto vacío
- [x] Probar con el AI Act real en XML (180 considerandos, 113 artículos, 13 anexos)
- [x] Crear IDs globalmente únicos/estables por unidad y corte

Resultado actual:

```text
XML oficial (BOE / EUR-Lex)
 ↓
LegalUnit (artículo, considerando, anexo)
 ↓
normalización
 ↓
Chunk + metadatos jurídicos (article, unit_type)
```

---

## Hito 2 — Embeddings y retrieval semántico

### Embeddings

- [x] Añadir `sentence-transformers`
- [x] Usar `intfloat/multilingual-e5-small`
- [x] Crear `EmbeddingModel`
- [x] `embed_query`
- [x] `embed_passages`
- [x] Prefijos `query:` y `passage:`
- [x] Normalizar embeddings
- [x] Embeddings en batch
- [x] Confirmar dimensión 384
- [x] Probar similitud con textos artificiales

### Retriever

- [x] Implementar producto escalar
- [x] Crear `SearchResult`
- [x] Crear `Retriever`
- [x] Ranking por similitud
- [x] `top_k`
- [x] Probar sobre AI Act completo
- [x] Detectar limitaciones reales del chunking
- [x] Añadir tests de similitud, ranking y `top_k`

### Hallazgo de evaluación

Consulta:

```text
¿Qué es un sistema de inteligencia artificial?
```

Resultados observados:

```text
chunk_size=1500 / overlap=200
→ definición formal: ranking 42
→ score ≈ 0.8287

chunk_size=800 / overlap=120
→ definición formal: ranking 12
→ score ≈ 0.8481

definición aislada
→ score ≈ 0.8973
```

Conclusión:

> Este ejemplo sugiere que mezclar contenidos en un chunk perjudica la recuperación de esta definición. Es una hipótesis que debe contrastarse con más preguntas; no demuestra por sí solo la calidad general del embedding ni identifica la única causa del fallo.

No seguir afinando tamaños indefinidamente sin una evaluación sistemática.

---

## Hito 3 — Vector store persistente

Empezar con Qdrant local persistente; el servidor y Docker llegarán al empaquetar. Su función es almacenar y consultar vectores, no mejorar por sí mismo la relevancia. Conservar la búsqueda en memoria como referencia y comparar resultados sobre el mismo corpus.

Objetivo:

```text
INDEXACIÓN

Documento
 ↓
chunks
 ↓
embeddings
 ↓
Qdrant
```

```text
CONSULTA

Pregunta
 ↓
embedding
 ↓
Qdrant
 ↓
top-k
```

Tareas:

- [x] Instalar `qdrant-client`
- [x] Añadir `data/qdrant/` al `.gitignore`
- [x] Crear `QdrantVectorStore`
- [x] Crear colección de dimensión 384
- [x] Configurar métrica compatible con embeddings normalizados
- [x] Diseñar ID estable para cada chunk
- [x] Guardar vectores
- [x] Guardar payload:
  - [x] texto
  - [x] source
  - [x] page_number
  - [x] chunk ID
- [x] Inserción en batch
- [x] Buscar `top_k`
- [x] Reconstruir `SearchResult`
- [x] Tests del vector store
- [x] Separar indexación de consulta
- [x] Añadir `PersistentRetriever`; conservar `Retriever` en memoria como referencia

Clases previstas:

```text
QdrantVectorStore
DocumentIndexer
Retriever
```

### Hito 3B — Catálogo documental con SQL

SQLite permite practicar SQL y resolver el seguimiento de documentos sin añadir un servidor. Qdrant almacena vectores; SQLite registra identidad, versiones y estado de indexación.

- [x] Crear tablas `documents`, `document_versions` e `indexing_runs`, con claves primarias, foráneas y restricciones de unicidad.
- [x] Practicar consultas parametrizadas, JOIN, índices y transacciones con consultas reales: versiones de una norma e indexaciones fallidas.
- [x] Guardar hash del original, fecha de incorporación y localizador.
- [ ] Añadir ID oficial y fechas de la fuente cuando existan (integración de fuentes oficiales).
- [x] Registrar versión del modelo de embeddings y configuración de normalización/chunking para poder reconstruir el índice.
- [x] Diseñar IDs reproducibles por documento, versión, configuración de procesamiento y posición del fragmento.
- [x] Probar reindexación idempotente, reinicio y recuperación de un fallo parcial.

SQLite y Qdrant no comparten una transacción: mantener un estado de preparación y activar una versión solo cuando sus vectores estén completos. Las consultas deben filtrar las versiones activas. Implementar este cambio coordinado al introducir versiones; no dar por resuelta la consistencia con dos escrituras independientes.

---

## Hito 4 — Evaluación del retrieval

Antes del LLM debe existir una evaluación mínima.

- [x] Crear dataset de 10-20 preguntas
- [x] Guardar documento esperado
- [x] Guardar página/artículo esperado cuando se conozca
- [x] Definir fragmento o contenido esperado
- [x] Medir Hit@1
- [x] Medir Hit@5
- [x] Medir Hit@10
- [x] Registrar consultas que fallen
- [x] Perform an initial manual review of results and evidence references.
- [x] Accept reviewed alternative evidence that helps answer the question, including relevant recitals.
- [x] Include questions without an answer in the corpus.
- [ ] Expand coverage with systematic paraphrase cases and questions requiring multiple passages.
- [ ] Separar preguntas para ajustar parámetros de un pequeño conjunto reservado para comprobar mejoras.
- [x] Version questions and stable corpus/model/configuration references; preserve reference results in JSON.
- [x] Measure latency and MRR@10. Hit@k measures whether accepted evidence appears, not whether all necessary evidence is retrieved.

Mejoras a evaluar, no asumir:

- [ ] chunking jurídico
- [ ] tamaño de chunk
- [ ] overlap
- [ ] búsqueda híbrida
- [ ] filtros por metadatos
- [ ] reranking

---

## Hito 5 — Generación con LLM

Implementation status — 2026-09-16: original plus one rewrite, RRF fusion,
question-specific citations, coordinated-question grouping, and explicit rejected,
abstained and failed outcomes are implemented. Fixed-source replay preserves the
saved evidence or fails before inference. The compact synthesis prompt improved
qualifications and coverage in observed d02/d03 runs, but irrelevant claims and
reviewer false positives remain. See [the experiment](docs/synthesis-replay.md).

The target remains readable synthesis with inspectable original sources. Literal
passage output is a temporary protection. Milestones 5/6 are not accepted yet;
retrieval relevance, answer support, coverage and readability need separate review.
Operational next steps belong in [TODO.md](TODO.md).

### Multi-passage synthesis and context selection

The LLM should answer the question by synthesizing several useful retrieved
passages, rather than simply returning the top-ranked passage. Top 3 and top 5
are initial configurations to compare, not fixed requirements. The number of
passages may vary with available evidence and the context token budget.

- [ ] Independently research and document top-k retrieval, similarity thresholds, reranking, adaptive context selection, and context-window limits, using primary sources and small experiments.
- [x] Separate candidate retrieval from selecting the passages actually sent to the LLM.
- [x] Compare fixed top 3/top 5 with a relevance threshold plus a maximum passage count and token budget; allow zero selected passages when evidence is insufficient.
- [ ] Calibrate thresholds on reviewed relevant/irrelevant examples and validate on held-out questions. Similarity is not a probability of correctness, and thresholds may change with the model or corpus.
- [x] Remove overlap duplicates and preserve complementary information, source IDs, and document versions when assembling context.
- [x] Generate a question-focused synthesis with citations for supported claims; distinguish conflicting passages instead of silently merging them.
- [x] Evaluate evidence coverage, answer support, abstention, latency, and token use. Hit@k alone does not measure whether all evidence needed for a multi-passage answer is present.

La síntesis local y la separación de preguntas ya están implementadas y medidas
(véase [el experimento](docs/local-generation.md)). Las casillas abiertas de esta
sección describen la aceptación pendiente, no la ausencia de toda implementación.
No hay un umbral calibrado ni garantía de respaldo semántico.

Objetivo:

```text
Pregunta
 ↓
Retriever
 ↓
fragmentos relevantes
 ↓
LLM
 ↓
síntesis
```

Tareas:

- [x] Crear capa `generation`
- [x] Crear interfaz/clase de generación
- [x] Diseñar prompt
- [x] Entregar al LLM solo contexto recuperado
- [x] Implement empty-evidence abstention and explicit rejected/error outcomes.
- [x] Validate semantic abstention on reviewed positive and negative cases.
- [x] Separar respuesta generada de fragmentos originales
- [x] Tests de casos básicos
- [ ] Aprender y documentar tokens, ventana de contexto, embeddings frente a generación, temperatura y cuantización usando ejemplos del proyecto.
- [x] Seleccionar un modelo instruct local tras medir memoria y latencia en el equipo disponible; fijar su versión y presupuesto de contexto.
- [x] Delimitar documentos como datos: las instrucciones incluidas en el corpus no deben dirigir al asistente.
- [x] Reducción de pasajes de contexto a 5, exclusión de considerandos si hay artículos y ponderación por margen relativo de puntuación.
- [x] Associate citations with supplied source IDs and reject unknown IDs.
- [x] Establish semantic support for every claim; automated review still has false positives.

Respuesta objetivo:

```text
Pregunta:
...

Respuesta:
Síntesis generada.

Fuentes:

1. Documento ...
   Página: 46
   Artículo: 3

   Fragmento original:
   "..."
```

Posibles modelos:

```text
RagResponse
├── answer
└── sources

Source
├── document
├── page
├── article
└── text
```

---

## Hito 6 — Evidencia y seguridad de respuesta

- [x] Implement fail-closed handling for absent evidence and rejected synthesis.
- [x] Show unanswered questions with distinct rejection, abstention and error states.
- [x] Validate the sufficiency policy with reviewed examples, including false rejections.
- [x] No usar conocimiento general del LLM como sustituto de documentos
- [x] Record supplied chunks, citation IDs and document/version identity for each answer.
- [x] Test empty-evidence abstention and preservation of unanswered questions with deterministic fakes.
- [x] Validate abstention with real questions outside the corpus.
- [x] Evaluar alucinaciones y citas
- [x] No interpretar la similitud como probabilidad de respuesta correcta ni decidir suficiencia solo porque existan resultados top-k.
- [x] Evaluar conjuntamente corrección, respaldo de afirmaciones y abstención con respuestas revisadas manualmente; un juez LLM es opcional y no sustituye esas referencias.

Principio:

> No evidence retrieved → no legal answer.

---

## Hito 7 — API con FastAPI

- [x] Añadir FastAPI
- [x] Crear aplicación
- [x] Endpoint de salud
- [x] `POST /ask`
- [x] Modelos Pydantic
- [x] Validación de entrada
- [x] Manejo de errores
- [x] Logging
- [x] Tests de API
- [x] OpenAPI

Respuesta conceptual:

```json
{
  "answer": "...",
  "sources": [
    {
      "document": "eu_ai_act.xml",
      "page": 0,
      "text": "..."
    }
  ]
}
```

---

## Hito 8 — Interfaz

MVP sencillo.

- [x] Campo de pregunta
- [x] Respuesta generada
- [x] Fuentes visibles
- [x] Página
- [x] Fragmentos originales
- [x] Abrir desde la cita la versión original del documento en la página correspondiente.
- [x] Explorar resaltado del pasaje en el visor; comprobar si requiere conservar coordenadas
  de extracción. Mejora posterior de interfaz, sin bloquear la evaluación actual.
- [x] Mensaje claro si no existe evidencia

Opciones:

- [x] HTML mínimo servido con la aplicación como opción inicial; Streamlit solo si facilita claramente la entrega.

No construir un frontend complejo inicialmente.

---

## Hito 9 — Docker

Objetivo:

```bash
docker compose up
```

Arquitectura:

```text
Docker Compose
├── rag-bogado-api
└── qdrant
```

- [ ] `Dockerfile`
- [ ] `docker-compose.yml`
- [ ] FastAPI en contenedor
- [ ] Qdrant en contenedor
- [ ] Persistencia mediante volumen
- [ ] Variables de entorno
- [ ] Comunicación entre servicios
- [ ] Documentar ejecución

---

## Hito 10 — Fuentes oficiales y actualización

Objetivo:

```text
Fuente oficial
 ↓
consultar metadatos
 ↓
¿cambió?
 ├── no → nada
 └── sí
      ↓
   descargar
      ↓
   procesar
      ↓
   reindexar
```

Primera fuente prevista:

- [ ] BOE
- [ ] EUR-Lex posteriormente, como adaptador separado

Metadatos deseables:

```text
DocumentMetadata
├── official_id
├── title
├── source
├── source_url
├── last_updated
├── downloaded_at
└── content_hash
```

Tareas:

- [ ] Investigar API oficial
- [ ] Consultar metadatos
- [ ] Descargar documento
- [ ] Guardar versión local
- [ ] Calcular hash
- [ ] Detectar cambios
- [ ] Reindexar solo si cambia
- [ ] Conservar el original y la versión anterior; activar la nueva solo después de completar y validar la indexación
- [ ] Tests con HTTP simulado

Empezar con una lista explícita de identificadores BOE y una sincronización manual. Añadir después una ejecución programada sencilla, sin agente. Preferir el texto estructurado de la API para preservar artículos y apartados.

- [ ] Separar `last_checked_at`, fecha de actualización del registro, fecha de publicación de versión y fechas de vigencia cuando estén disponibles.
- [ ] Mostrar el estado de consolidación y la fecha de comprobación; si falla la sincronización, conservar la versión utilizable e indicar el fallo.
- [ ] Detectar cambios de contenido por hash y actualizar metadatos sin recalcular embeddings cuando el texto no cambie.
- [ ] Implementar timeouts, reintentos limitados, paginación cuando corresponda y registro de errores.
- [ ] Probar sin cambios, texto modificado, cambio solo de metadatos, fallo de descarga y fallo de indexación; impedir mezcla accidental de versiones.
- [ ] Consultar por defecto la versión activa, conservando el historial para auditoría; las preguntas históricas se incorporarán más adelante.

La API permite acceder a metadatos y versiones por bloques. El BOE distingue la actualización del registro de una nueva versión del texto y publica un estado de consolidación. La consolidación tiene carácter informativo y puede estar pendiente de incorporar modificaciones; debe identificarse como tal en la interfaz. Por ello, “última versión descargada” no debe presentarse como garantía de vigencia jurídica. Fuente: [FAQ oficial de legislación consolidada](https://www.boe.es/datosabiertos/faq/consolidada.php), consultada el 08/09/2026. Contrato técnico: [API de datos abiertos del BOE](https://www.boe.es/datosabiertos/api/api.php?lang=es).

La actualización documental debe ser determinista si puede resolverse de forma determinista.

---

## Hito 11 — LangChain y agentes (opcional)

### LangChain

- [ ] Integrar una parte concreta
- [ ] Comparar con implementación propia
- [ ] Documentar ventajas/inconvenientes
- [ ] No reescribir todo solo para incluir la librería

### Agentes

Solo si existe un caso de uso real.

Posibles herramientas:

```text
search_regulations()
get_document()
get_article()
list_documents()
```

Ejemplo futuro:

```text
"Compara lo que establece el AI Act con el RGPD sobre..."
```

No introducir agentes solo para añadir una tecnología al portfolio.

Comparar dos normas puede resolverse recuperando evidencia de ambas mediante un flujo fijo. Un agente se justifica si necesita decidir dinámicamente qué fuentes o artículos consultar en varios pasos. El experimento debe compararse con ese flujo en calidad, latencia y número de llamadas, con presupuesto de pasos y herramientas de solo lectura. LangChain no es un requisito para RAG ni para agentes.

---

## Hito 12 — CI y calidad profesional

### GitHub Actions

Configured and independently verified remotely for the persistence and catalog
implementations on September 9. Recheck CI for each latest commit before merging.

- [x] Run pytest in GitHub Actions.
- [x] Run `ruff check` in GitHub Actions.
- [x] Run `ruff format --check` in GitHub Actions.
- [x] Install from `uv.lock` and check pull requests without downloading models or accessing BOE.
- [x] Practice a feature branch, focused commits, diff review, and a pull request.
- [ ] Practice issues with acceptance criteria.
- [ ] Practice resolving merge conflicts when an appropriate case arises.

### Type checking

Evaluar:

- [ ] mypy
- [ ] pyright

### Pre-commit

Opcional:

- [ ] Ruff
- [ ] comprobaciones rápidas

### Hito 12B — Observabilidad y entrega

- [ ] Logs estructurados con ID de petición, duración de retrieval/generación, modelo y versiones documentales consultadas.
- [ ] Medir latencia, errores, abstenciones y estado/antigüedad de sincronización; evitar almacenar preguntas completas por defecto.
- [ ] Poder rastrear una respuesta hasta sus fragmentos y una actualización fallida hasta su ejecución.
- [ ] Construir la imagen en CI cuando exista Docker y ejecutar una prueba de arranque.
- [ ] Documentar una release reproducible y su reversión. Distinguir CI de entrega continua y de despliegue automático.
- [ ] Añadir despliegue automatizado solo cuando haya un destino elegido y compatible con el presupuesto.

Empezar con logs y resúmenes locales. OpenTelemetry, Prometheus o Grafana quedan condicionados a una necesidad de diagnóstico concreta.

### Hito 14 — Laboratorios opcionales posteriores

| Competencia | Experimento y condición para incorporarlo |
| --- | --- |
| AWS básico | Práctica temporal de IAM con permisos mínimos y almacenamiento de un artefacto en S3, si las condiciones de la cuenta permiten coste cero. Documentar creación, uso y limpieza; mantener la aplicación local. |
| Agentes | Investigación en varios pasos con herramientas acotadas, comparada con un flujo fijo (hito 11). |
| Fine-tuning / LoRA | Solo con ejemplos de entrenamiento y un fallo medido de comportamiento o formato que prompting/RAG no resuelvan. No sirve para mantener las leyes actualizadas. Verificar recursos de entrenamiento antes de comprometerlo. |
| MLflow | Empezar con resultados JSON/CSV; probar tracking local cuando comparar muchos experimentos resulte difícil. Registro y ciclo completo de modelos solo si se entrenan y gestionan modelos propios. |
| Terraform | Reproducir infraestructura real que ya exista y necesite recrearse; no añadirlo antes de elegir destino. |
| Kubernetes | Laboratorio local separado si interesa aprender despliegue y recuperación; no es necesario para operar este MVP. |
| Spark / Kafka / Databricks | Posponer hasta tener volumen o eventos que justifiquen procesamiento distribuido o streaming. Si no aparece ese problema, aprenderlos en otro proyecto evita forzar esta arquitectura. |

AWS no garantiza gratuidad indefinida: el Free plan actual dura hasta seis meses o hasta agotar créditos. Revisar elegibilidad y servicios antes del laboratorio; los avisos de presupuesto no son un límite duro de gasto. No pasar a un plan de pago para completar este roadmap. Fuente: [AWS: elección de plan](https://docs.aws.amazon.com/en_en/awsaccountbilling/latest/aboutv2/free-tier-plans.html), consultada el 08/09/2026.

---

## Hito 13 — Portfolio

### README

- [ ] Problema
- [ ] Arquitectura
- [ ] Diagrama
- [x] Document basic local installation and quality checks.
- [x] Indexación
- [x] Consulta
- [ ] Ejemplo de respuesta
- [ ] Fuentes
- [x] Document evaluation commands, reference results, and metric interpretation.
- [x] Document current implementation and evaluation limitations.
- [ ] Decisiones técnicas
- [x] Link the project roadmap from the README.

### Demo

- [ ] Capturas/GIF/vídeo
- [ ] Pregunta real
- [ ] Respuesta
- [ ] Fuentes verificables

### Ser capaz de explicar

- [ ] por qué XML oficial y parsing de unidades jurídicas (`LegalUnit`);
- [ ] por qué no depender de páginas arbitrarias de PDF;
- [ ] por qué corte por oraciones completas y prefijo normativo;
- [ ] limitación de chunks grandes;
- [ ] por qué E5;
- [ ] diferencia retrieval/generación;
- [ ] por qué Qdrant;
- [ ] cómo evitar respuestas sin evidencia;
- [ ] cómo evaluar retrieval;
- [ ] funciones vs clases;
- [ ] actualización de normas;
- [ ] despliegue con Docker.

---

# 5. Pautas de código limpio

## Responsabilidad única

Una función o clase debe tener una responsabilidad principal.

Bien:

```text
load_xml()
normalize_text()
chunk_legal_units()
embed_query()
search()
```

Evitar una única función que descargue, procese, genere embeddings, indexe y llame al LLM.

## Funciones vs clases

Usar función cuando:

- no mantiene estado;
- transforma entrada → salida;
- es pequeña y clara;
- no necesita implementaciones intercambiables.

Ejemplos:

```text
normalize_text()
similarity()
find_breakpoint()
```

Usar clase cuando:

- mantiene estado;
- conserva configuración;
- gestiona un cliente/recurso;
- su inicialización es costosa;
- habrá varias implementaciones;
- varias operaciones comparten estado.

Ejemplos:

```text
EmbeddingModel
Retriever
QdrantVectorStore
```

No crear clases vacías solo para agrupar funciones.

## Tipado

Añadir tipos a interfaces públicas:

```python
def embed_query(self, text: str) -> list[float]: ...
```

Evitar `Any` salvo que esté justificado.

## Nombres

Preferir nombres que expresen intención:

```text
embedding_model
page_number
collection_name
search_results
```

Evitar nombres vagos como `data2`, `tmp`, `thing`.

## Tamaño y complejidad

Una función larga no es automáticamente mala, pero si hace varias tareas diferentes debe dividirse.

Pregunta útil:

> ¿Puedo describir esta función con una sola frase sin utilizar “y después”?

## Configuración

Evitar valores mágicos repartidos:

```text
embedding model
chunk_size
overlap
Qdrant collection
paths
LLM model
```

Centralizar cuando la necesidad aparezca, sin crear antes un sistema de configuración complejo.

## Dependencias externas

Mantenerlas detrás de capas claras:

```text
RAG-Bogado
    ↓
QdrantVectorStore
    ↓
qdrant-client
```

No dispersar llamadas directas a Qdrant por todo el proyecto.

## Errores

Validar entradas relevantes y producir errores comprensibles.

---

# 6. Pautas de testing

## Regla

> Probar comportamiento, no detalles internos innecesarios.

### Unit tests

Deben ser:

- rápidos;
- deterministas;
- sin Internet;
- sin APIs externas;
- fáciles de leer.

Usar fakes/mocks cuando corresponda.

Ejemplo actual:

```text
Retriever
→ FakeEmbeddingModel
```

en lugar de descargar/cargar el modelo real.

### Integration tests

Para comprobar varias capas juntas:

```text
XML → chunks
chunks → Qdrant
query → Qdrant → resultados
API → RagService → respuesta
```

### Evaluación semántica

Un modelo semántico no siempre debe probarse con igualdad exacta.

Ejemplo:

```text
pregunta
→ documento/artículo esperado aparece en top-k
```

### Bugs

Cada bug importante corregido debe llevar a considerar un test de regresión.

Ejemplo real:

```text
bug: se perdía contenido entre chunks
fix: corregir cálculo del overlap
test: reconstruir texto y comprobar que no desaparece contenido
```

---

# 7. Checklist antes de commit

Para cerrar la sesión, seguir también [AGENTS.md](AGENTS.md): actualizar TODO y
ESTUDIAR, publicar las notas de cierre y verificar el estado final de la entrega.

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Esperado:

```text
pytest → PASS
ruff check → PASS
ruff format --check → PASS
```

Después:

```bash
git status
git diff
git add <archivos-revisados>
git commit -m "tipo: descripción"
git push
```

---

# 8. Convención de commits

Ejemplos:

```text
feat: add semantic retrieval
feat: add qdrant vector store
fix: prevent chunk content loss
test: add retriever tests
refactor: separate indexing from retrieval
docs: update project roadmap
chore: configure development environment
ci: run tests and ruff on pull requests
```

Tipos:

```text
feat      nueva funcionalidad
fix       corrección
test      tests
refactor  cambio interno
docs      documentación
chore     mantenimiento
ci        integración continua
build     construcción/dependencias
```

---

# 9. Definition of Done

Una funcionalidad relevante se considera terminada cuando:

- [ ] Código implementado
- [ ] Responsabilidades claras
- [ ] Tipos razonables
- [ ] Errores importantes contemplados
- [ ] Tests cuando proceda
- [ ] Integración probada cuando proceda
- [ ] `pytest` pasa
- [ ] `ruff check` pasa
- [ ] `ruff format --check` pasa
- [ ] No contiene secretos
- [ ] No versiona datos o índices innecesarios
- [ ] Commit claro
- [ ] Documentación actualizada si cambia arquitectura o uso

---

# 10. Fuera de alcance inicial

No añadir sin una necesidad clara:

- Kubernetes
- Airflow
- microservicios
- autenticación compleja
- frontend React completo
- fine-tuning
- infraestructura cloud compleja
- Postgres/pgvector si Qdrant cubre las necesidades
- agentes sin caso de uso real
- abstracciones genéricas con una única implementación

---

# 11. Estado de los hitos

Estado de implementación registrado el 2026-09-16. Los pendientes operativos,
fallos y verificaciones de cada sesión se mantienen en [TODO.md](TODO.md).

| Milestone | Current state |
| --- | --- |
| 0 / 12 — Setup and CI | Local checks and remote CI working; Docker and optional quality tools pending |
| 1 / 2 — Ingestion and semantic retrieval | Tested baseline; legal chunking and richer metadata remain experiments |
| 3 — Qdrant persistence | Implemented and compared against in-memory retrieval |
| 3B — SQL catalog | Local versions, indexing history, transactional activation, and standalone query implemented |
| 4 — Retrieval evaluation | 14-question development set; broader coverage and held-out questions pending |
| 5 / 6 — Generation and evidence | Question grouping, explicit outcomes and fixed-source replay implemented; synthesis support/relevance acceptance pending |
| 7 / 8 — API and interface | After the pending terminal synthesis quality review |
| 9 / 12B — Packaging and observability | After the local MVP; logs can be added as needed |
| 10 — BOE / EUR-Lex synchronization | After the local MVP |
| 13 — Portfolio | Basic usage/evaluation docs present; full demo and decision notes pending |
| 11 / 14 — Optional experiments | Deferred until a concrete need or separate learning objective |

---

# 12. Regla para no perder el foco

Antes de añadir una tecnología nueva:

1. ¿Qué problema concreto resuelve?
2. ¿Tenemos ya ese problema?
3. ¿Podemos medir si mejora el sistema?
4. ¿Aporta valor al producto o solo al listado de tecnologías?
5. ¿Complica significativamente la arquitectura?

Si no hay una respuesta clara, dejarla para una iteración posterior.

---
