# Trabajo entre sesiones

## Al empezar

1. Leer `TODO.md` para conocer el punto de partida, fallos y siguiente acción.
2. Consultar el mapa de `README.md` y abrir solo los archivos relacionados.
3. Leer la sección pertinente de `PROJECT_PLAN.md` si afecta a alcance, herramientas
   o aceptación. Consultar `ESTUDIAR.md`, si existe localmente, para acompañar el
   trabajo con teoría. Está ignorado por Git; no forzar su publicación.
4. Comprobar rama, cambios locales y estado de entrega antes de modificar nada.
   Los estados históricos de PR y CI no acreditan el estado actual.

Trabajar en pasos pequeños y explicados. Mantener código y documentación técnica
en inglés; notas de sesión y estudio en español, y preguntas/evidencia en español.
Compartir con la usuaria decisiones materiales sobre modelos y recursos.

## Dónde escribir

- `README.md`: estructura real, instalación, comandos y enlaces de entrada.
- `PROJECT_PLAN.md`: objetivos, arquitectura, herramientas, hitos y aceptación.
- `TODO.md`: pendientes accionables, fallos reproducibles, bloqueos y entrega.
- `ESTUDIAR.md`: conceptos tratados, preguntas para comprenderlos y práctica.
- `docs/session-history.md`: entregas o decisiones históricas que merezca conservar.
  No copiar allí cada paso ni mantener una segunda lista de pendientes vigente.

No duplicar tareas detalladas en el plan. Cada pendiente debe indicar archivos,
siguiente acción y criterio de cierre. Distinguir tests fallidos de evaluaciones
semánticas deficientes. Si la causa se desconoce, marcar el archivo como candidato
a investigar; no afirmar que contiene el error sin evidencia.

## Al cerrar cada sesión

1. Revisar el diff y ejecutar las comprobaciones apropiadas. Para código, seguir
   pytest y Ruff del plan; para documentación, revisar enlaces, rutas y coherencia.
   Registrar fecha, comando, resultado y lo que no se ejecutó. No inventar checks.
2. Completar la entrega de código autorizada (commit/push y PR según corresponda).
3. Actualizar `TODO.md`: quitar lo resuelto tras verificarlo, añadir nuevos fallos
   o tareas con sus archivos, conservar bloqueos y dejar una primera acción clara.
   Registrar rama, referencia de entrega y si CI está verificado o pendiente.
4. Revisar `ESTUDIAR.md`: añadir conceptos nuevos sin duplicados; no marcar como
   aprendido algo solo porque se haya implementado. Conservar el progreso previo.
5. Actualizar README si cambió la estructura y el plan si cambiaron hitos o alcance.
   Guardar una nota histórica breve solo si aporta evidencia o una decisión útil.
6. Tras el push del trabajo, incluir estas notas en un último commit documental y
   hacer push también de ese commit cuando la publicación esté autorizada. Revisar
   CI sobre el último commit publicado y el estado local. No asumir que los checks
   del commit anterior cubren las notas nuevas; no crear un ciclo de commits solo
   para anotar el hash del propio cierre.
7. Indicar en la respuesta final qué se entregó, qué se comprobó y qué queda.
   Si no hubo publicación o no se pudo verificar CI, decirlo explícitamente y dejar
   el pendiente en TODO. Mantener las notas aunque la sesión termine sin push.

Estas instrucciones definen el procedimiento del asistente; no son un hook ni una
tarea automática de Git. No implican fusionar PR ni publicar sin autorización.
