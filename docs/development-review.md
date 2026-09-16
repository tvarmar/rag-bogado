# Revisión conjunta de respuestas — desarrollo

Batería: [development-review.json](../src/rag_bogado/evaluation/datasets/development-review.json).
Nueve casos de desarrollo; las preguntas reservadas de `generation.json` no se ejecutan.
No se compara con una frase obligatoria ni se cambia el prompt para acertar un caso.

## Orden de revisión

| Caso | Tipo | Pregunta |
| --- | --- | --- |
| d01 | simple | ¿Quién debe procurar la alfabetización en IA? |
| d02 | paraphrase | ¿A quién le corresponde procurar que el personal sepa utilizar la IA con suficiente formación? |
| d03 | compound | ¿Quién debe procurar la alfabetización en IA y cuándo debe prepararse y actualizarse la documentación técnica de una IA de alto riesgo? |
| d04 | enumerated_subjects | ¿Qué obligaciones de transparencia tienen proveedores y responsables del despliegue? |
| d05 | comparison | ¿Qué diferencias hay entre las obligaciones de proveedores y responsables del despliegue? |
| d06 | explicit_questions | ¿Quién debe procurar la alfabetización en IA? ¿Cuándo debe prepararse la documentación técnica de una IA de alto riesgo? |
| d07 | mixed | ¿Cuándo se elabora la documentación técnica de un sistema de IA de alto riesgo? ¿Cuál es el número de teléfono del delegado de protección de datos de mi empresa? |
| d08 | near_domain_negative | ¿Qué número de teléfono tiene el delegado de protección de datos de mi empresa? |
| d09 | negative | ¿Cuál es la receta de una tortilla de patatas? |

## Cómo valorar

Primero leer pregunta y respuesta completa. Valorar después, por separado:

- **Pertinencia:** sí / parcialmente / no responde a lo pedido.
- **Cobertura:** qué partes solicitadas cubre y cuáles faltan.
- **Respaldo:** para síntesis, comprobar cada afirmación contra sus citas. Para
  pasajes literales, registrar la copia exacta aparte; no llamarla una prueba de
  pertinencia, interpretación ni de que el artículo completo esté disponible.
- **Condiciones:** si conserva sujetos, límites, excepciones y grado de obligación.
- **Información innecesaria:** qué contenido sobra para esta pregunta.
- **Abstención:** si está justificada por la evidencia; un error de ejecución no
  cuenta como abstención correcta, ni una respuesta vacía obtiene 100 % de respaldo.

Mantener separados los juicios de la usuaria y las observaciones del asistente.
No completar una valoración humana sin su respuesta. Guardar dudas y desacuerdos,
y comprobar la fuente cuando hagan falta. No calcular una nota global todavía.

## Ejecución incremental

El runner mantiene sus tres casos históricos por defecto. Para esta batería:

```bash
uv run python scripts/evaluate_multi_query.py \
  --dataset src/rag_bogado/evaluation/datasets/development-review.json \
  --case d02 --search-count 1 \
  --output-dir data/evaluation/development-review-d02-new
```

La carpeta debe ser nueva. `--case` se puede repetir; sin él se ejecutan los nueve.
Sin `--search-count` compara una y dos búsquedas; ambos brazos tienen el mismo
presupuesto final. Por defecto usa pasajes literales. Para medir síntesis, añadir
`--answer-mode synthesis` y revisar también los errores que apruebe su juez.

Para comenzar, reutilizamos una salida real guardada: no es una nueva ejecución.
Tras valorar el baseline, comparar el segundo brazo y revisar la fidelidad de la
reformulación. Si repite la original, anotar que no hubo segunda búsqueda efectiva.

## Caso d01 — pertinencia valorada; síntesis pendiente

**Pregunta:** ¿Quién debe procurar la alfabetización en IA?

**Procedencia:** `multi-query-evidence.json`, caso `simple`, una búsqueda, modo
literal, Qwen3 4B. Documento local `eu_ai_act.pdf`, versión 1. No se ha regenerado.

Los siguientes bloques reproducen **todos** los pasajes devueltos como respuesta,
en su orden original. No son un resumen redactado por el asistente.

### Pasaje 1 — Q1-S2, página 51

```text
Artículo 4
Alfabetización en materia de IA
Los proveedores y responsables del despliegue de sistemas de IA adoptarán medidas para garantizar que, en la mayor
medida posible, su personal y demás personas que se encarguen en su nombre del funcionamiento y la utilización de
sistemas de IA tengan un nivel suficiente de alfabetización en materia de IA, teniendo en cuenta sus conocimientos técnicos,
su experiencia, su educación y su formación, así como el contexto previsto de uso de los sistemas de IA y las personas o los
colectivos de personas en que se van a utilizar dichos sistemas.
CAPÍTULO II
PRÁCTICAS DE IA PROHIBIDAS
Artículo 5
Prácticas de IA prohibidas
1.
Quedan prohibidas las siguientes prácticas de IA:
a) la introducción en el mercado, la puesta en servicio o la utilización de un
```

### Pasaje 2 — Q1-S3, página 6

```text
promover las herramientas de alfabetización en materia de IA, la sensibilización pública y la comprensión de los
beneficios, los riesgos, las salvaguardias, los derechos y las obligaciones en relación con el uso de sistemas de IA. En
cooperación con las partes interesadas pertinentes, la Comisión y los Estados miembros deben facilitar la elaboración
de códigos de conducta voluntarios para promover la alfabetización en materia de IA entre las personas que se
ocupan del desarrollo, el manejo y el uso de la IA.
(21)
Con el objetivo de garantizar la igualdad de condiciones y la protección efectiva de los derechos y libertades de las
personas en toda la Unión, las normas establecidas en el presente Reglamento deben aplicarse a los proveedores de
sistemas de IA sin discriminación, con
```

### Pasaje 3 — Q1-S4, página 6

```text
público como zonas que
no son de acceso público, como los aeropuertos o el vestíbulo de un edificio residencial privado por el que se accede
a una consulta médica. Los espacios en línea no son lugares de acceso público, ya que no son espacios físicos. No
obstante, se debe determinar caso por caso si un espacio es de acceso público o no teniendo en cuenta las
particularidades de la situación concreta.
(20)
Con el fin de obtener los mayores beneficios de los sistemas de IA, protegiendo al mismo tiempo los derechos
fundamentales, la salud y la seguridad, y de posibilitar el control democrático, la alfabetización en materia de IA debe
dotar a los proveedores, responsables del despliegue y personas afectadas de los conceptos necesarios para tomar
decisiones con conocimiento de causa en
```

### Valoración registrada

| Dimensión | Valoración de la usuaria |
| --- | --- |
| ¿Responde a la pregunta? | Sí, el conjunto responde en general. |
| ¿Cubre lo solicitado? | Pendiente |
| ¿Conserva las condiciones relevantes? | Pendiente |
| ¿Qué información sobra? | No se han indicado eliminaciones concretas; el tercer pasaje resulta menos claro. |

Observación del asistente (no una valoración de la usuaria): el primer pasaje
incluye sujetos responsables y condiciones, pero también el inicio del artículo 5.
Los otros pasajes incluyen contenido periférico y frases cortadas. Podemos reconocer
que hay información útil y a la vez señalar que la respuesta contiene demasiado ruido.

Registro estructurado: [development-review-progress.json](../src/rag_bogado/evaluation/reports/development-review-progress.json).

Valoración de la usuaria: el pasaje 1 responde definitivamente; el 2 responde
«más o menos» y necesita más texto previo; el 3 es «un poco más raro». No se ha
confirmado cobertura exhaustiva ni conservación de todas las condiciones.

Preferencia explícita: el LLM debe leer los fragmentos y producir una respuesta
comprensible con evidencia, no limitar el producto final a mostrar pasajes.
La pertinencia de la recuperación queda valorada; falta valorar la síntesis del
caso d01. No interpretar este comentario como aprobación de una respuesta generada.
Si falta contexto, recuperarlo de la misma versión documental, no completarlo de memoria.

## Síntesis real de d01 — pendiente de valoración de la usuaria

Ejecutada el 2026-09-14 con Qwen3 4B, el prompt actual y exactamente los tres
pasajes valorados, sin recuperar ni añadir contexto. S1, S2 y S3 corresponden a
Q1-S2, Q1-S3 y Q1-S4 de la ficha anterior. Una generación y tres llamadas de revisión.
La salida siguiente es literal del modelo; no está corregida por el asistente.

> Los proveedores y responsables del despliegue de sistemas de IA deben adoptar medidas para garantizar que su personal y demás personas que se encargan del funcionamiento y uso de los sistemas de IA tengan un nivel suficiente de alfabetización en materia de IA. [S1]

> La Comisión y los Estados miembros deben facilitar la elaboración de códigos de conducta voluntarios para promover la alfabetización en materia de IA entre las personas que se ocupan del desarrollo, el manejo y el uso de la IA. [S2]

> La alfabetización en materia de IA debe dotar a los proveedores, responsables del despliegue y personas afectadas de los conceptos necesarios para tomar decisiones con conocimiento de causa en relación con el uso de sistemas de IA. [S3]

El revisor automático aprobó las tres afirmaciones. La revisión del asistente
**no acepta** esta salida: la primera omite «en la mayor medida posible», «en su
nombre» y condiciones del contexto; la segunda omite la cooperación con las partes
interesadas; la tercera completa una frase que estaba cortada en su fuente.
La claridad y pertinencia de la síntesis aún deben valorarse con la usuaria.
Estas observaciones no sustituyen esa valoración ni una revisión jurídica experta.

[Registro de ejecución y fuentes](../src/rag_bogado/evaluation/reports/d01-synthesis-review.json).
No se ha cambiado el prompt ni la lógica de producción para este caso.

Reproducción (carpeta de salida nueva, Ollama local en ejecución):

```bash
uv run python scripts/review_saved_answer.py \
  --source-report src/rag_bogado/evaluation/reports/multi-query-evidence.json \
  --output-dir data/evaluation/d01-synthesis-review-new
```

El script conserva borrador y veredicto por separado para diagnóstico, incluso
si la aplicación rechaza la respuesta. No presentar el borrador como respuesta aceptada.

### Comentario de la usuaria sobre la síntesis

«Me gusta bastante la respuesta». Valoración positiva de la redacción, sin dar por
resueltos los problemas de respaldo. Pregunta cómo se presentan las referencias.
La salida actual contiene `sources` con ID, documento, página, chunk y versión;
la ruta al original está en `source_path`. La futura interfaz debe permitir pasar
de la cita a esos datos y al pasaje exacto. Todavía no hay interfaz gráfica.

## Revisión en bloque de d02 y d03

La usuaria prefiere ver juntas las respuestas a una paráfrasis y a una pregunta
compuesta y comentarlas libremente, sin completar una ficha por cada caso.
Comparar A (una búsqueda) y B (original + una reformulación), con los mismos
parámetros y sin cambios de prompt. Si la reformulación repite la original, indicar
el número efectivo de búsquedas; no inventar diferencias entre respuestas iguales.
Los borradores rechazados se presentan solo como material de evaluación, separados
de las respuestas que acepta la aplicación.

Reproducción con registro diagnóstico:

```bash
uv run python scripts/evaluate_multi_query.py \
  --dataset src/rag_bogado/evaluation/datasets/development-review.json \
  --case d02 --case d03 --answer-mode synthesis --record-drafts \
  --output-dir data/evaluation/development-review-batch-new
```

`--record-drafts` conserva las salidas de síntesis en `diagnostic_drafts`, incluidas
las rechazadas por el revisor. No altera ni desactiva el filtro de producción.

Las cuatro opciones ya están en [la comparación en bloque](development-review-batch.md), con los rechazos y las fuentes.

## Ajuste de separación y diagnóstico de la pregunta compuesta

La ejecución anterior sí detectaba alfabetización, preparación y actualización;
las partes ausentes del resultado se habían rechazado durante la revisión.
Tras aclarar la agrupación, el modelo devuelve dos preguntas: alfabetización y
cuándo preparar/actualizar la documentación. La protección de preguntas únicas
conserva todos sus sujetos y condiciones. Nueve casos de desarrollo revisados.

La [nueva ejecución completa](../src/rag_bogado/evaluation/reports/grouped-compound-review.json)
procesa ambas preguntas: devuelve alfabetización y marca explícitamente el rechazo
de preparación/actualización. El borrador cita S1 para un plazo que S1 no sostiene.
La respuesta de alfabetización sigue omitiendo condiciones pese a la aprobación del
revisor. No se da por resuelta la fiabilidad de la síntesis por corregir la separación.
