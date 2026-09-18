# Trabajo entre sesiones

## Al empezar

1. Consultar el mapa de `README.md` y abrir solo los archivos relacionados.
2. Leer la sección pertinente de `PROJECT_PLAN.md` si afecta a alcance, herramientas
   o aceptación.
3. Comprobar rama, cambios locales y estado de entrega antes de modificar nada.
   Los estados históricos de PR y CI no acreditan el estado actual.

Trabajar en pasos pequeños y explicados. Mantener código y documentación técnica
en inglés; notas de sesión y comunicación en español, y preguntas/evidencia en español.
Compartir con la usuaria decisiones materiales sobre modelos y recursos.

## Dónde escribir

- `README.md`: estructura real, instalación, comandos y enlaces de entrada.
- `PROJECT_PLAN.md`: objetivos, arquitectura, herramientas, hitos y aceptación.
- `docs/session-history.md`: entregas o decisiones históricas que merezca conservar.
  No copiar allí cada paso ni duplicar tareas detalladas en el plan.

Distinguir tests fallidos de evaluaciones semánticas deficientes. Si la causa se
desconoce, marcar el archivo como candidato a investigar; no afirmar que contiene el
error sin evidencia.

## Al cerrar cada sesión

1. Revisar el diff y ejecutar las comprobaciones apropiadas. Para código, seguir
   pytest y Ruff del plan; para documentación, revisar enlaces, rutas y coherencia.
   Registrar fecha, comando, resultado y lo que no se ejecutó. No inventar checks.
2. Completar la entrega de código autorizada (commit/push y PR según corresponda).
3. Actualizar `PROJECT_PLAN.md` si cambiaron hitos, herramientas o alcance.
4. Actualizar `README.md` si cambió la estructura de archivos, instalación o uso.
   Guardar una nota histórica breve en `docs/session-history.md` si aporta evidencia
   o una decisión útil.
5. Tras el push del trabajo, incluir estas notas en un último commit documental y
   hacer push también de ese commit cuando la publicación esté autorizada. Revisar
   CI sobre el último commit publicado y el estado local. No asumir que los checks
   del commit anterior cubren las notas nuevas; no crear un ciclo de commits solo
   para anotar el hash del propio cierre.
6. Indicar en la respuesta final qué se entregó, qué se comprobó y qué queda.

Estas instrucciones definen el procedimiento del asistente; no son un hook ni una
tarea automática de Git. No implican fusionar PR ni publicar sin autorización.
