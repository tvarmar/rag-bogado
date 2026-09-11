
# RAG-Bogado — Project Plan

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
- [ ] Mostrar una respuesta de evidencia insuficiente en los casos negativos del conjunto de evaluación.
- [x] Ejecutar sin servicios de pago, con instrucciones reproducibles mediante `uv`.
- [ ] Publicar resultados de retrieval y revisión de respuestas, incluidos fallos y latencia en el equipo utilizado.
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

Estructura aproximada:

```text
src/rag_bogado/
|
├── ingestion/
│   ├── loader.py
│   ├── normalizer.py
│   └── chunker.py
│
├── retrieval/
│   ├── embeddings.py
│   ├── retriever.py
│   └── vector_store.py
│
├── generation/
│   └── generator.py
│
├── indexing/
│   └── indexer.py
│
├── sources/
│   ├── boe.py
│   └── eurlex.py
│
├── api/
│   └── ...
│
└── __init__.py
```

La estructura puede evolucionar. No se deben crear módulos o abstracciones antes de que exista una necesidad real.

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

### PDF

- [x] Evaluar `pypdf`
- [x] Detectar problemas de extracción
- [x] Migrar a PyMuPDF
- [x] Crear `Page`
- [x] Extraer texto por página
- [x] Conservar `page_number`
- [x] Conservar `source`
- [x] Eliminar cabecera y pie mediante posición
- [ ] Hacer configurable la estrategia de márgenes por fuente
- [x] Revisar uso de context manager para cerrar documentos

### Normalización

- [x] Normalizar espacios horizontales
- [x] Conservar saltos de línea significativos
- [x] Colapsar exceso de líneas vacías
- [x] Evitar correcciones manuales agresivas

### Chunking

- [x] Crear `Chunk`
- [x] Chunking por tamaño
- [x] Overlap
- [x] Evitar cortes de palabras
- [x] Evitar pérdida de contenido
- [x] Validar `chunk_size`
- [x] Validar `overlap`
- [x] Soportar texto vacío
- [x] Probar con el AI Act real
- [x] Establecer baseline `chunk_size=800`, `overlap=120`
- [x] Crear IDs globalmente únicos/estables
- [ ] Evaluar chunking jurídico por artículos/apartados
- [ ] Añadir metadatos: artículo, apartado, sección, capítulo

Resultado actual:

```text
PDF
 ↓
Page
 ↓
normalización
 ↓
Chunk + metadatos
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

### Multi-passage synthesis and context selection

The LLM should answer the question by synthesizing several useful retrieved
passages, rather than simply returning the top-ranked passage. Top 3 and top 5
are initial configurations to compare, not fixed requirements. The number of
passages may vary with available evidence and the context token budget.

- [ ] Independently research and document top-k retrieval, similarity thresholds, reranking, adaptive context selection, and context-window limits, using primary sources and small experiments.
- [ ] Separate candidate retrieval from selecting the passages actually sent to the LLM.
- [ ] Compare fixed top 3/top 5 with a relevance threshold plus a maximum passage count and token budget; allow zero selected passages when evidence is insufficient.
- [ ] Calibrate thresholds on reviewed relevant/irrelevant examples and validate on held-out questions. Similarity is not a probability of correctness, and thresholds may change with the model or corpus.
- [ ] Remove overlap duplicates and preserve complementary information, source IDs, and document versions when assembling context.
- [ ] Generate a question-focused synthesis with citations for supported claims; distinguish conflicting passages instead of silently merging them.
- [ ] Evaluate evidence coverage, answer support, abstention, latency, and token use. Hit@k alone does not measure whether all evidence needed for a multi-passage answer is present.

This is future generation work; the current retrieval evaluation does not implement
an LLM, a relevance threshold, or a guarantee that returned passages are valid answers.

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
- [ ] Definir comportamiento cuando falta evidencia
- [x] Separar respuesta generada de fragmentos originales
- [x] Tests de casos básicos
- [ ] Aprender y documentar tokens, ventana de contexto, embeddings frente a generación, temperatura y cuantización usando ejemplos del proyecto.
- [ ] Seleccionar un modelo instruct local tras medir memoria y latencia en el equipo disponible; fijar su versión y presupuesto de contexto.
- [ ] Delimitar documentos como datos: las instrucciones incluidas en el corpus no deben dirigir al asistente.
- [ ] Asociar citas con IDs de fragmentos entregados al LLM y comprobar que los IDs citados existen; revisar también si el texto respalda cada afirmación.

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

- [ ] Estrategia para evidencia insuficiente
- [ ] Responder explícitamente cuando no se pueda justificar una respuesta
- [ ] No usar conocimiento general del LLM como sustituto de documentos
- [ ] Registrar chunks usados en cada respuesta
- [ ] Tests de preguntas sin respuesta
- [ ] Evaluar alucinaciones y citas
- [ ] No interpretar la similitud como probabilidad de respuesta correcta ni decidir suficiencia solo porque existan resultados top-k.
- [ ] Evaluar conjuntamente corrección, respaldo de afirmaciones y abstención con respuestas revisadas manualmente; un juez LLM es opcional y no sustituye esas referencias.

Principio:

> No evidence retrieved → no legal answer.

---

## Hito 7 — API con FastAPI

- [ ] Añadir FastAPI
- [ ] Crear aplicación
- [ ] Endpoint de salud
- [ ] `POST /ask`
- [ ] Modelos Pydantic
- [ ] Validación de entrada
- [ ] Manejo de errores
- [ ] Logging
- [ ] Tests de API
- [ ] OpenAPI

Respuesta conceptual:

```json
{
  "answer": "...",
  "sources": [
    {
      "document": "eu_ai_act.pdf",
      "page": 46,
      "text": "..."
    }
  ]
}
```

---

## Hito 8 — Interfaz

MVP sencillo.

- [ ] Campo de pregunta
- [ ] Respuesta generada
- [ ] Fuentes visibles
- [ ] Página
- [ ] Fragmentos originales
- [ ] Mensaje claro si no existe evidencia

Opciones:

- [ ] HTML mínimo servido con la aplicación como opción inicial; Streamlit solo si facilita claramente la entrega.

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

- [ ] por qué PyMuPDF;
- [ ] por qué conservar páginas;
- [ ] por qué overlap;
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
load_pdf()
normalize_text()
chunk_page()
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
PDF → chunks
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

# 11. Próximo paso

Updated: 2026-09-11. Experimental local synthesis is implemented and measured;
quality acceptance, API, and user interface remain pending. See the September 11
session log and docs/local-generation.md for evidence and known failures.

| Milestone | Current state |
| --- | --- |
| 0 / 12 — Setup and CI | Local checks and remote CI working; Docker and optional quality tools pending |
| 1 / 2 — Ingestion and semantic retrieval | Tested baseline; legal chunking and richer metadata remain experiments |
| 3 — Qdrant persistence | Implemented and compared against in-memory retrieval |
| 3B — SQL catalog | Local versions, indexing history, transactional activation, and standalone query implemented |
| 4 — Retrieval evaluation | 14-question development set; broader coverage and held-out questions pending |
| 5 / 6 — Generation and evidence | Synthesis and separate question workflow implemented; evidence quality acceptance pending |
| 7 / 8 — API and interface | After the first evaluated terminal synthesis |
| 9 / 12B — Packaging and observability | After the local MVP; logs can be added as needed |
| 10 — BOE / EUR-Lex synchronization | After the local MVP |
| 13 — Portfolio | Basic usage/evaluation docs present; full demo and decision notes pending |
| 11 / 14 — Optional experiments | Deferred until a concrete need or separate learning objective |

## Next session: reliable evidence for each separated question

1. Review the September 11 `feat/local-generation` delivery and its latest remote
   checks. Read `docs/local-generation.md` and the `local-generation.json` and
   `question-workflow.json` reference reports before changing the baseline.
2. Start Ollama with `bash scripts/serve_ollama.sh` if it is not already running.
   The selected model and weights are local; no new download is normally needed.
3. Prioritize the preparation-timing subquestion. Inspect its ten retrieved
   candidates against the expected Article 11 sentence (page 58). Compare a small
   context-selection/retrieval change that recovers complete supporting evidence.
   Do not count a page hit without checking the actual fragment.
4. Check every claim against its specific citation. The model still infers timing
   from a cut recital and can add peripheral literacy claims. Prompt-only tweaks
   did not resolve this. Measure a concrete support/abstention improvement before
   calling the generation stage accepted.
5. Improve the question separator's enumeration handling. It correctly separates
   the three-part query and preserves the tested comparison, but sometimes splits
   a single request about two subject categories. Keep separate answers, citations,
   partial status and per-question errors as implemented.
6. Expand reviewed development evidence and calibrate any threshold only after
   measuring relevant/irrelevant examples. Keep held-out cases reserved until the
   development policy is fixed; then evaluate them once.
7. Only proceed to FastAPI/UI after reviewing support, coverage, abstention and
   acceptable latency. A successful response schema does not establish quality.

Session deliverables: local synthesis, per-question retrieval/generation,
reproducible measurements, and 86 passing deterministic tests. Milestones 5/6
remain open for quality acceptance. The closing GitHub delivery is on
`feat/local-generation`; check its PR/CI rather than repeating model setup.

Work in small explained steps. Material model/resource choices remain shared
with the user. Keep code documentation in English and questions/evidence in Spanish.

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

# 13. Session log and next session

## Session — 2026-09-08

### Completed

- Revised the roadmap around a local MVP, learning goals, free local execution, and later BOE synchronization.
- Fixed empty chunks, PDF resource handling, and retrieval edge cases; added regression tests.
- Preserved the existing module organization and the retriever's reference to `EmbeddingModel`.
- Organized evaluation code, questions, documentation, and reference reports under `src/rag_bogado/evaluation/`; kept automated tests in `tests/`.
- Wrote the project and evaluation README files in English; retained Spanish questions and evidence to match the corpus.
- Created a reproducible evaluation with 12 answerable questions and two negative questions.
- Updated relevance judgments to accept reviewed alternative evidence that helps answer the question, including appropriate recitals.
- Recorded results under the updated criterion: Hit@1 = 50%, Hit@5 = 91.67%, Hit@10 = 91.67%, MRR@10 = 0.6597. These reflect a changed evaluation criterion, not an improved retrieval algorithm.
- Added future multi-passage LLM synthesis and independent research on top-k, thresholds, context selection, and token budgets to the plan.
- Verified 34 passing tests, Ruff lint, and formatting locally.
- Prepared GitHub Actions and provided the branch, commit, and pull request workflow; the user published the PR and reported two successful checks in GitHub.

### State at the end of the session

- The PR remains open; merging it is pending.
- Remote CI success was reported by the user, not independently checked by the assistant.
- Qdrant persistence and LLM generation have not been implemented.
- This session-log update was added after the reported successful checks and still needs to be committed and pushed to the PR branch.

## Next session

1. Review the working tree and commit/push this session-log update if it is still pending.
2. Review the PR's final diff and confirm that checks pass for its latest commit.
3. Merge the PR, then update the local `main` branch.
4. Start the Qdrant persistence milestone on a new branch: first review what a collection, vector, point ID, and payload represent and how they fit the current code.
5. Define the first small implementation: persist a few chunks with their metadata, reopen the store, and retrieve them without recalculating their embeddings.
6. Preserve the current retriever and evaluation as references; compare results when the persistent retrieval path is ready.

Continue in small, explained steps, following the existing folder structure and
writing new code documentation in English. Update this log at the end of the next
session with completed work, remaining work, and the next starting point.

## Session — 2026-09-09

### Completed and verified

- Closed the September 8 delivery: session notes committed as `b4a7039`, PR #1
  merged, and local `main` updated after independently checking remote CI.
- Implemented Qdrant disk persistence, reproducible point/index identities, batch
  insertion, compatibility/input validation, and `SearchResult` reconstruction.
- Added resumable `DocumentIndexer`, `PersistentRetriever`, and evaluation
  build/reuse modes. Preserved the in-memory retriever as the reference.
- Compared memory, Qdrant build, and Qdrant reuse in separate processes on the
  AI Act: 1,041 chunks, 14 questions, all 140 top-ten positions identical.
  Hit@1 = 50%, Hit@5 = Hit@10 = 91.67%, MRR@10 = 0.6597. Maximum score difference
  was approximately 1.2e-7; reuse calculated zero passage embeddings.
- Committed persistence as `efc68fb` and merged PR #2 after both remote checks passed.
- Implemented SQLite documents, original versions, and indexing attempts with
  foreign keys, uniqueness constraints, parameterized JOINs, and transactions.
- Built and verified separate vector collections before activating a run. Tested
  failure isolation, rollback during activation, and retry of missing passages.
- Added index/query/history/failures commands, retained hash-addressed originals,
  and active-only query without rereading, chunking, or embedding the PDF.
- Registered `eu_ai_act`, local version 1, reusing all existing vectors. A separate
  query returned five passages with version identity and the retained original.
- Committed the catalog implementation as `5795376` and published PR #3; both
  remote implementation checks passed. This closing plan update travels in the
  same PR, whose final commit must pass CI before the closing merge.
- Verified 56 tests plus Ruff lint/format. No model download or paid service was
  required for the real local validation; embeddings ran on `cuda:0`.

### Evidence and reproduction

- `src/rag_bogado/evaluation/reports/persistence-comparison.json`: comparison,
  provenance, and measurements. Full local runs live in `data/evaluation/`.
- `data/evaluation/catalog-query-2026-09-09.json`: real catalog query output.
- `README.md`: indexing, standalone querying, history, and failures commands.
- Delivery links: [PR #2](https://github.com/tvarmar/rag-bogado/pull/2),
  [PR #3](https://github.com/tvarmar/rag-bogado/pull/3).

### Remaining scope and next starting point

- The local retrieval/persistence/catalog increment is implemented. Generation,
  abstention, API, and UI have not been implemented.
- The development evaluation is small and contains no held-out split yet.
- Official identifiers/source dates, schema migrations, and multiwriter
  coordination remain future work. Hard termination can leave a preparing attempt;
  a new attempt resumes vectors while retaining the previous active version.
- End-of-day procedure: commit/push this handoff, check CI on the latest PR #3
  commit, merge PR #3, and update local `main`. Keep branch history and local data.
- The next work session follows section 11: inspect hardware, compare local LLM
  options with the user, and build a first measured terminal synthesis with citations.

The September 8 next-session instructions above are historical. Section 11 and
this September 9 handoff define the current starting point.


## Session — 2026-09-11

### Implemented and measured

- Selected Qwen3 4B Instruct Q4_K_M with the user after checking WSL RAM and the
  RTX 4050 6 GB GPU. Installed Ollama 0.34.0 locally under ignored `data/runtime/`
  and model weights under `data/models/`; loopback server with cloud disabled.
- Created `feat/local-generation`. Added an Ollama adapter, bounded context
  selection, exact-source output, per-claim citation-ID validation, terminal
  query/replay commands, and deterministic generation tests.
- Measured known Article 4 synthesis: 7.44 s after model reload, 1.98 s warm,
  445 prompt tokens / 96 output tokens, sampled device VRAM 3,133 MiB.
- Compared top three/five on four development questions at 8,192 context tokens;
  device VRAM reached 4,388 MiB including retained embedding allocations.
- Added a development/held-out split, an exploratory selection-only threshold
  sweep, and a reference report with 12 runs and assistant evidence review.
- Preserved failed initial outputs. Corrected an ambiguous status instruction;
  validation continues to reject inconsistent or truncated answers.
- Initial synthesis increment passed 68 tests; the final question-workflow
  increment passed 86 tests plus Ruff lint/format locally. Closing delivery is
  tracked on `feat/local-generation`; remote CI is checked after pushing.

### Findings and remaining work

- Top five recovers the useful fourth-ranked passage for the paraphrase; top
  three appropriately abstains on its selected context.
- Both compound-question answers fail coverage and do not acknowledge missing
  parts. Top five additionally uses a cut, out-of-scope passage. This is an
  explicitly recorded quality failure, not an accepted completed feature.
- The known response identifies actors and the duty to adopt measures but omits
  qualifications; it must not be presented as an exhaustive legal explanation.
- The tested negative questions abstain, but broader and held-out validation,
  threshold calibration, and coverage-aware selection remain pending.
- `src/rag_bogado/evaluation/reports/local-generation.json` preserves results,
  model digest, prompt, metrics, exact passages, and review. Full local attempts
  are in `data/evaluation/generation-2026-09-11*`.
- `docs/local-generation.md` documents reproduction and measurement limits.
  The local server can be started with `bash scripts/serve_ollama.sh`.
- First measured-synthesis target complete; milestones 5/6 and MVP acceptance
  remain open. Section 11 defines the next starting point.


### Question-workflow increment and session handoff

- Agreed with the user to separate explicit questions, retrieve independently,
  and answer each with its own evidence and abstention status.
- Added a bounded local question separator and orchestration that preserves each
  question, namespaces citations, isolates failures, and rejects mixing document
  versions. Live CLI uses this flow; saved evidence replay stays unchanged.
- Real compound query produced three self-contained questions and three separate
  retrievals/answers. Mixed query produced one answer and one explicit abstention.
- Measured 22.54 s total for the compound pipeline and 12.13 s for the mixed case;
  these include retrieval and separation, unlike the earlier generation-only times.
- Preserved comparison and simple-question cases, but recorded over-splitting of
  a subject enumeration. The compound preparation answer is still unsupported:
  separation improves organization but does not guarantee retrieval or generation
  correctness. No semantic acceptance is claimed.
- Reference: `src/rag_bogado/evaluation/reports/question-workflow.json`; full local
  runs: `data/evaluation/question-workflow-2026-09-11/`. A prompt-only follow-up
  did not resolve the remaining failures and is retained separately as v2.
- Final local checks: 86 tests passed, Ruff lint/format passed. Runtime and weights
  remain ignored by Git. The user requested plan updates and GitHub publication;
  publish the code, tests, docs, and reference reports together.
- The next session starts with section 11. Do not repeat installation or treat
  the old single-query coverage work as still unimplemented.
