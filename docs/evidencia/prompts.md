# Índice de prompts — recurso `tasks`

Prompts usados en el reto, por fase y paso, copiados literalmente de
[`bitacora.md`](bitacora.md). Cada paso incluye el prompt principal y, si las hubo, las
iteraciones posteriores del mismo paso.

## Índice

- **Fase 1 — Especificación y contexto**
  - P0 — Línea base del proyecto (0 iteraciones)
  - P1 — Exploración del repo (1 iteración)
  - P2 — Especificación y criterios de aceptación (1 iteración)
  - P3 — Convenciones en CLAUDE.md (1 iteración)
- **Fase 2 — Generación incremental e integración**
  - P4 — Skeleton-first: esqueleto de tasks (1 iteración)
  - P5 — Test-first: tests de aceptación en rojo (1 iteración)
  - P6 — Incremental 1: happy path (1 iteración)
  - P7 — Incremental 2: validaciones de forma (1 iteración)
  - P8 — Incremental 3: fecha límite y responsable (1 iteración)
  - P9 — Incremental 4: idempotencia (1 iteración)
  - P10 — Integración y estilo (0 iteraciones)
- **Fase 3 — Tests, cobertura y mutación**
  - P11 — Configuración de cobertura y mutación (0 iteraciones)
  - P12 — Tests unitarios del service (1 iteración)
  - P13 — Test de integración users + tasks (0 iteraciones)
  - P14 — Cerrar huecos de cobertura (0 iteraciones)
  - P15 — Mutation testing (0 iteraciones)
  - P16 — Matar mutantes supervivientes (0 iteraciones)
- **Fase 4 — Debugging**
  - P17a — Preparación del caso de debugging (0 iteraciones)
  - P17 — Reproducir y presentar el bug (0 iteraciones)
  - P18 — Confirmación de la hipótesis (0 iteraciones)
  - P19a — Test de regresión en rojo (0 iteraciones)
  - P19 — Fix mínimo + test de regresión (1 iteración)
- **Fase 4 — Refactor y code review**
  - P20 — Inventario de code smells (1 iteración)
  - P21.1 — Refactor 1 (0 iteraciones)
  - P21.2 — Refactor 2 (0 iteraciones)
  - P21.3 — Refactor 3 (0 iteraciones)
  - P21.4 — Medición después del refactor (0 iteraciones)
  - P22 — Resultados de la refactorización (0 iteraciones)
  - P23 — Code review por categorías (4 iteraciones)
- **Fase 5 — Documentación**
  - P24 — Docstrings estilo Google (1 iteración)
  - P25 — Documentación OpenAPI (0 iteraciones)
  - P26 — README para onboarding (0 iteraciones)
  - P27 — CHANGELOG y ADR (0 iteraciones)
- **Fase 6 — Evidencia y cierre**
  - P28 — Compilar la evidencia (0 iteraciones)
  - P29 — Reflexión final (1 iteración)
  - P30 — Verificación final (0 iteraciones)

## Fase 1 — Especificación y contexto

### P0 — Línea base del proyecto

**Prompt principal:**

```text
Antes de empezar el reto, verifica la línea base del proyecto sin tocar nada:
ejecuta pytest -q, pytest --cov=. --cov-branch --cov-report=term-missing y ruff check .
Dime si todo está en verde. Si algo falla, detente y explícame qué falla.
```

**Iteraciones:** ninguna.

### P1 — Exploración del repo

**Prompt principal:**

```text
Voy a añadir un recurso nuevo `tasks/` (gestión de tareas de equipo) a este proyecto.
Antes de proponer nada, lee @CLAUDE.md, @main.py, @core/errors.py, @users/routes.py,
@users/service.py, @users/schemas.py, @users/repository.py, @tests/conftest.py,
@tests/test_users.py y @pyproject.toml.

Resume en una lista:
1. El patrón de capas y qué responsabilidad tiene cada archivo.
2. Cómo se levantan los errores y qué formato tiene la respuesta de error.
3. Cómo se aísla el estado entre tests.
4. Las convenciones de nombres, estilo de tests y reglas de linting (pyproject.toml).
5. Qué riesgos ves al añadir un segundo recurso (p. ej., estado compartido entre tests,
   orden de rutas, validaciones de Pydantic frente a errores de dominio).

No cambies código todavía.
```

**Iteración 1:**

```text
Comprueba tu resumen contra esta lista y completa lo que falte: uso de response_model=
en todas las rutas, catálogo core/errors.py (sin HTTPException a mano), repository.reset()
invocado por una fixture autouse de conftest.py, rutas específicas antes que rutas con
parámetro, y migrations/ y legacy/ fuera de límites. Dime qué puntos ya estaban y cuáles
añadiste. No cambies código.
```

### P2 — Especificación y criterios de aceptación

**Prompt principal:**

```text
Este es el ticket de la feature. Redáctalo como documento en docs/feature-tasks.md
con las secciones: Historia de usuario, Objetivo, Alcance (incluye / no incluye),
Contrato de la API (request, response y códigos HTTP), Criterios de aceptación
numerados (CA-01, CA-02, …) en formato Dado/Cuando/Entonces, y Ejemplos de uso con curl.

Historia: Como miembro del equipo de operaciones quiero registrar tareas con
responsable, prioridad y fecha límite para que ningún trabajo quede sin registrar
y se pueda rastrear.

Contrato:
- POST /tasks — cuerpo: title (str, obligatorio), description (str, opcional,
  máx. 1000), priority (int 1–5, por defecto 3), due_date (fecha ISO YYYY-MM-DD,
  opcional), assignee_id (int, opcional). Cabecera opcional: Idempotency-Key (1–64 caracteres).
- GET /tasks — lista; filtro opcional ?assignee_id=<id>.
- GET /tasks/{task_id} — una tarea.
- Respuesta Task: id, title, description, priority, due_date, assignee_id,
  status ("pending" al crear), created_at.

Criterios:
- 201 al crear, con la tarea en el cuerpo y status "pending".
- title se recorta (strip); tras recortar debe tener 3–120 caracteres → si no, 422.
- priority fuera de 1–5 o no entera → 422.
- due_date anterior a hoy (UTC) → 422; hoy es válido.
- assignee_id que no existe en users → 404.
- Misma Idempotency-Key + mismo cuerpo → 200 con la MISMA tarea (no se duplica).
- Misma Idempotency-Key + cuerpo distinto → 409.
- Sin Idempotency-Key, dos POST iguales crean dos tareas.
- GET /tasks/{id} inexistente → 404. GET /tasks?assignee_id=X devuelve solo las de X.
- Mensajes de error en español, generados con core/errors.py.

Después de escribir el documento, lista las ambigüedades o casos que NO cubren
mis criterios (p. ej., límites exactos, tipos inesperados, zona horaria) como
preguntas numeradas para mí. No asumas respuestas: pregúntame.
```

**Iteración 1:**

```text
Mis decisiones a tus preguntas (siguen tu numeración):

1. title
   - Los límites 3 y 120 son inclusivos y se miden tras strip.
   - Título solo de espacios → 422 (queda con longitud 0). Mensaje: el de Pydantic por
     defecto, igual que en users; no hay mensaje propio en español para errores de forma.
   - title que no sea string (número, null) → 422.

2. description
   - No se le quitan los espacios de los extremos (a diferencia de title); se guarda tal
     cual.
   - "" es válido y se guarda como "". Omitida y null son equivalentes (se guarda null).
   - El máximo de 1000 se cuenta sobre el valor recibido, sin recortar.
   - Sin longitud mínima.

3. priority
   - Entero estricto: 3.0, 3.5, "3", "alta", true y null → 422.
   - Omitida → 3. Rango 1–5 (0 o 6 → 422).

4. due_date
   - Solo YYYY-MM-DD. Un datetime con hora → 422, y una fecha inexistente (2026-02-30)
     también.
   - "Hoy" es la fecha UTC del servidor al recibir la petición, calculada con una función
     de core/clock.py, aunque el cliente esté en otra zona horaria. Hoy es válido, ayer → 422.
   - Sin fecha máxima. Omitida y null son equivalentes (se guarda null).

5. assignee_id
   - 0 o negativo → 422 (forma, no 404). Entero ≥ 1 que no existe en users → 404 con
     errors.not_found.
   - null explícito se acepta y equivale a omitido (tarea sin responsable).

6. Varios errores a la vez
   - Orden: (1) forma de cuerpo y cabecera → 422; (2) fecha pasada → 422; (3) búsqueda de
     Idempotency-Key → 200 o 409; (4) existencia del responsable → 404; (5) creación.
   - Título corto + responsable inexistente → 422. Fecha pasada + responsable inexistente
     → 422 (el 422 va antes que el 404).

7. Campos desconocidos o asignados por el servidor (status, id, created_at, foo)
   - Mismo comportamiento que users (el de Pydantic por defecto). Los campos que asigna el
     servidor enviados por el cliente nunca se usan: el servidor siempre pone los suyos.

8. Idempotencia, "mismo cuerpo"
   - La huella se calcula sobre el cuerpo YA validado y normalizado (tras strip y valores
     por defecto). El orden de claves no importa.
   - {"title":"x"} y {"title":"x","priority":3} son el mismo cuerpo. También " Revisar " y
     "Revisar".

9. Idempotencia cuando la primera petición falla
   - Si la primera petición con la clave K falla (422 o 404), la clave NO se guarda. Solo
     se guarda tras un 201.
   - Una petición válida posterior con K crea la tarea (201).
   - Cuerpo inválido con una clave ya usada → 422 (no 200 ni 409).

10. Idempotencia, alcance y duración
    - Clave global (no hay usuarios), sin caducidad. Almacén en memoria que se limpia con
      reset().
    - Sin restricción de caracteres y sin strip. Sensible a mayúsculas ("abc" ≠ "ABC").
    - Longitud 1–64; el límite cuenta caracteres (len()), no bytes. Vacía o más larga → 422.

11. Idempotencia, respuesta repetida
    - Misma clave + misma huella → 200 con la misma Task, idéntica a la original (mismo id
      y mismo created_at), sin crear tarea nueva.
    - Misma clave + huella distinta → 409 con mensaje en español del catálogo. Se reutiliza
      la función de core/errors.py que ya sirva para conflictos (already_exists u otra
      equivalente); no se añade ninguna nueva. [AJUSTAR: nombre real de la función]

12. GET /tasks?assignee_id=X con un usuario inexistente → 200 con lista vacía (es un
    filtro, no una consulta del usuario). Vale también para 0 y negativos. Solo un valor
    no entero → 422.

13. Orden del listado: por id ascendente.

14. Datos semilla: el almacén de tareas arranca vacío. reset() vacía tareas y claves de
    idempotencia. GET /tasks sin tareas → 200 con [].

15. GET /tasks/{task_id} con task_id ≤ 0 → 404 (es un entero que no corresponde a ninguna
    tarea). Solo un valor no entero → 422.

Otras:
- status: solo "pending" en este sprint; created_at en UTC, formato ISO 8601.
- El 422 por fecha pasada se valida en el service y su detail sale de una función de
  core/errors.py en español; el resto de 422 de forma usan el formato por defecto de
  Pydantic. [AJUSTAR: nombre de esa función]

Para cualquier pregunta que no esté aquí, aplica la opción más conservadora y coherente
con estas decisiones. Añade al documento una sección "Decisiones" con todas ellas y
asegúrate de que cada criterio CA-XX sea verificable con un test.
```

### P3 — Convenciones en CLAUDE.md

**Prompt principal:**

```text
Actualiza @CLAUDE.md para incorporar el recurso `tasks/` sin romper lo existente:
1. En "Estructura", añade `tasks/` con el mismo patrón de 4 archivos y
   `tests/test_tasks.py`. Añade `core/clock.py` y `docs/` (especificaciones y ADR).
2. En "Convenciones", añade:
   - La lógica que depende de la fecha actual no llama a `date.today()` ni a
     `datetime.now()` directamente: usa una función de `core/clock.py` para poder
     mockearla en los tests.
   - Las validaciones de forma (tipos, rangos, longitudes) van en los schemas
     Pydantic; las reglas de dominio (fecha pasada, responsable inexistente,
     idempotencia) van en service.py con core/errors.py.
   - Un recurso consulta otro recurso a través de su service.py, nunca de su repository.py.
   - Todo repositorio nuevo expone `reset()` y conftest.py lo invoca.
   - Docstrings estilo Google en las funciones públicas de service.py.
3. En "Cómo ejecutar", añade la cobertura de ramas
   (`pytest --cov --cov-branch --cov-report=term-missing`) y el mutation testing.
4. Añade una sección "Definición de hecho": tests en verde, cobertura >90 % en
   tasks/, `ruff check .` limpio, docstrings, README y CHANGELOG actualizados.

Mantén el tono y el formato del archivo y no borres ninguna regla existente.
Aplica el cambio y muéstrame el diff.
```

**Iteración 1:**

```text
Revisa tu diff: confirma que siguen intactas la regla del orden de rutas, la de
migrations/ y legacy/ fuera de límites y la de response_model=. Si alguna se perdió,
restáurala.
Además, registra como decisión de este paso el patrón de generación elegido:
skeleton-first para la estructura (feature nueva con varias piezas: schemas,
repositorio, service, rutas y reloj), seguido de test-first para las reglas (son
verificables y están en los criterios), todo con cadencia incremental (un criterio por
iteración y un commit por paso). Señales de alarma que vigilaré: skeleton-first → que el
esqueleto traiga lógica; test-first → que los tests se escriban leyendo el código y no
los criterios; incremental → pasos que mezclen varias reglas o commits sin tests en verde.
```

## Fase 2 — Generación incremental e integración

### P4 — Skeleton-first: esqueleto de tasks

**Prompt principal:**

```text
Lee @CLAUDE.md, @docs/feature-tasks.md y usa como ejemplo @users/routes.py,
@users/service.py, @users/schemas.py y @users/repository.py.

Crea SOLO el esqueleto del recurso tasks, sin implementar lógica:
- core/clock.py con `def today() -> date:` (TODO).
- tasks/__init__.py
- tasks/schemas.py: TaskBase, TaskCreate, Task con los campos y tipos del contrato
  (sin validadores todavía; deja TODOs donde irían).
- tasks/repository.py: firmas add, get, list_all, list_by_assignee,
  find_by_idempotency_key, save_idempotency_key y reset, con `raise NotImplementedError`
  y TODOs.
- tasks/service.py: firmas create_task, get_task, list_tasks con TODOs que nombren
  el criterio CA-XX que implementará cada parte.
- tasks/routes.py: APIRouter(prefix="/tasks", tags=["tasks"]) con las 3 rutas,
  response_model y status_code, leyendo la cabecera Idempotency-Key con Header(...)
  y delegando en service.

No registres el router en main.py todavía. No implementes nada: si una función
tiene lógica, el esqueleto está mal. Al final ejecuta ruff check . y pytest -q y lista
los archivos creados y los TODOs.
```

**Iteración 1:**

```text
Revisa tu esqueleto con esta lista y corrige lo que no cumpla, diciéndome qué cambiaste:
1. ¿Alguna función tiene lógica (if, bucles, cálculos, acceso real a datos)? Si sí,
   vacíala: el esqueleto debe estar "más vacío".
2. Nombres en inglés y snake_case, sin abreviaturas, como en users/.
3. Tipos: due_date: date | None, assignee_id: int | None, priority: int.
4. La ruta POST lee Idempotency-Key con Header(...) y no contiene lógica.
Vuelve a ejecutar ruff check . y pytest -q.
```

### P5 — Test-first: tests de aceptación en rojo

**Prompt principal:**

```text
Escribe tests/test_tasks.py a partir de los criterios de @docs/feature-tasks.md,
NO del código. Sigue el estilo de @tests/test_users.py y reutiliza @tests/conftest.py
(no inventes fixtures paralelas).

Reglas:
- Un test por criterio CA-XX, con nombre descriptivo en español que incluya el id
  (p. ej. test_ca03_titulo_con_solo_espacios_devuelve_422).
- Arrange / act / assert separados por una línea en blanco.
- Aserciones específicas: status code + el campo del cuerpo que demuestra el criterio
  (nada de `is not None` como única aserción).
- Para la fecha, NO dependas del día real: fija "hoy" con monkeypatch sobre
  core.clock.today (p. ej. 2026-01-15) y prueba ayer (422), hoy (201) y mañana (201).
- Incluye los límites: title de 2, 3, 120 y 121 caracteres; priority 0, 1, 5, 6 y
  "alta"; assignee_id inexistente; idempotencia (misma clave y mismo cuerpo, misma
  clave y cuerpo distinto, sin clave).

Añade al conftest la fixture que resetee también el repositorio de tasks. Si
tasks.repository.reset() aún lanza NotImplementedError, implementa SOLO reset() para no
romper los tests de users. No implementes nada más en tasks/. Ejecuta pytest y
muéstrame que los tests nuevos fallan por la razón correcta (NotImplementedError o 404
de ruta inexistente), no por errores de sintaxis, y que los de users siguen en verde.
```

**Iteración 1:**

```text
Antes de dar los tests por buenos, verifica: (1) cada CA-XX de @docs/feature-tasks.md
tiene al menos un test que lo nombra; dame la tabla CA → test; (2) los límites están a
ambos lados (ayer/hoy, 2/3 y 120/121 caracteres, priority 0/1 y 5/6); (3) ningún test
usa la fecha real. Añade lo que falte sin implementar código de producción y vuelve a
ejecutar pytest -q.
```

### P6 — Incremental 1: happy path

**Prompt principal:**

```text
Implementa SOLO lo necesario para que pasen los tests del happy path:
crear tarea (CA de 201 con status "pending"), GET /tasks/{id} existente e
inexistente (404) y GET /tasks. Registra el router en @main.py siguiendo cómo se
registra users_router. Implementa core/clock.py (hoy en UTC).

No implementes validaciones, idempotencia ni assignee todavía. Fix mínimo:
no toques los tests. Luego ejecuta pytest -q y ruff check . y dime qué tests pasan
y cuáles siguen en rojo (deben ser los de las reglas pendientes).
```

**Iteración 1:**

```text
Revisa tu diff completo y confírmame punto por punto, corrigiendo lo que no cumpla:
la ruta no tiene lógica; los 404 salen de core/errors.py; repository.reset() reinicia
también el contador de ids; no se tocó ningún test. Vuelve a ejecutar pytest -q.
```

### P7 — Incremental 2: validaciones de forma

**Prompt principal:**

```text
Implementa las validaciones de forma en @tasks/schemas.py para los criterios y
decisiones de title, priority, description, assignee_id e Idempotency-Key de
@docs/feature-tasks.md:
- title: strip; 3–120 caracteres tras recortar; solo espacios → 422.
- priority: entero 1–5, por defecto 3 (rechaza "alta" y 3.5).
- description: opcional, máx. 1000.
- assignee_id: entero ≥ 1 si se informa.
Usa las herramientas de Pydantic v2 (Field, StringConstraints o field_validator);
explícame en 3 líneas por qué elegiste cada una. No toques service ni los tests.
Ejecuta pytest -q y ruff check .
```

**Iteración 1:**

```text
Decisión: priority 3.0 → 422, porque el contrato dice "int" y aceptar floats ocultaría
errores del cliente (3.5 y 3.0 deben tratarse igual). Usa modo estricto solo en ese
campo (p. ej. Field(strict=True) o StrictInt) y comprueba que el envío JSON normal con
un entero sigue funcionando y que true también da 422. Si no hay un test para 3.0 y
para true, añádelos en tests/test_tasks.py con el CA de priority. Vuelve a ejecutar
pytest -q y ruff check .
```

### P8 — Incremental 3: fecha límite y responsable

**Prompt principal:**

```text
Implementa en @tasks/service.py las reglas de dominio:
- due_date < clock.today() → errors.invalid_request con mensaje en español (422).
  Hoy es válido.
- assignee_id informado que no existe → errors.not_found("usuario", assignee_id) (404).
  Consulta los usuarios a través de users.service (no del repositorio de users
  directamente), respetando las capas de @CLAUDE.md.
- Filtro GET /tasks?assignee_id=X.
Fix mínimo, no toques los tests. Ejecuta pytest -q y ruff check .
```

**Iteración 1:**

```text
Verifica y corrige si hace falta: (1) tasks/ no importa users.repository en ningún
archivo (muéstrame el grep); (2) la comparación de due_date es entre objetos date
usando core.clock.today(), sin date.today() ni datetime.now() en tasks/;
(3) assignee_id None no consulta users. Vuelve a ejecutar pytest -q.
```

### P9 — Incremental 4: idempotencia

**Prompt principal:**

```text
Implementa la idempotencia de POST /tasks según @docs/feature-tasks.md:
- La cabecera Idempotency-Key es opcional (1–64 caracteres).
- Guarda la clave junto con una huella del cuerpo normalizado.
- Misma clave + misma huella → devuelve la tarea existente con 200.
- Misma clave + huella distinta → 409 desde el catálogo de errores
  (si hace falta una función nueva en core/errors.py, propónla antes de crearla).
- El almacén de claves se limpia en tasks.repository.reset().

Antes de escribir código, propón el diseño en 5 líneas (dónde vive la huella, cómo
se devuelve 200 frente a 201 sin meter lógica en la ruta, qué error usa el 409) y
espera mi OK.
```

**Iteración 1:**

```text
OK al diseño con estas condiciones (si tu propuesta difiere, ajústala a esto y dime qué
cambiaste y por qué lo rechazo):
1. La decisión 200/201 vive en service: create_task devuelve (task, created: bool) y la
   ruta solo asigna response.status_code según created. Nada de lógica ni HTTPException
   en la ruta.
2. La huella es un hash (sha256) del cuerpo validado serializado con claves ordenadas
   (model_dump con mode="json"); la calcula service, el repositorio solo la guarda.
3. Para el 409 añade a core/errors.py una función genérica conflict(message: str) con el
   mismo estilo y docstring que invalid_request; already_exists no encaja porque el
   problema no es que la tarea exista, sino que la clave se reutilizó con otro cuerpo.
4. reset() limpia tareas, contador de ids y claves.
Impleméntalo y ejecuta pytest -q y ruff check .
```

### P10 — Integración y estilo

**Prompt principal:**

```text
Verifica la integración de tasks con el proyecto:
1. Ejecuta pytest -q y ruff check .: ¿todo en verde y sin avisos?
2. ¿El router está registrado y /docs mostrará los 3 endpoints con sus response_model?
3. Revisa contra @CLAUDE.md: capas, catálogo de errores, nombres, orden de rutas y
   que no se tocaron migrations/ ni legacy/ (git diff main --stat).
4. Lista cualquier incumplimiento con archivo:línea y corrígelo con el cambio mínimo.
5. Levanta la app en segundo plano (uvicorn main:app --port 8000), ejecuta dos veces
   curl -i -X POST localhost:8000/tasks -H 'Content-Type: application/json'
   -H 'Idempotency-Key: demo-1' -d '{"title":"Revisar backups","priority":2,"assignee_id":1}'
   (debe dar 201 y luego 200), muéstrame ambas respuestas y detén la app.
```

**Iteraciones:** ninguna.

## Fase 3 — Tests, cobertura y mutación

### P11 — Configuración de cobertura y mutación

**Prompt principal:**

```text
Configura @pyproject.toml para medir bien la cobertura y la mutación:
- [tool.coverage.run]: branch = true, source = ["core", "users", "tasks"] más main.py
  (o el equivalente) y omite tests/, legacy/ y migrations/.
- [tool.coverage.report]: show_missing = true y fail_under = 90.
- Añade mutmut a requirements.txt e instálalo. Comprueba la versión instalada
  (mutmut --version) y usa la sintaxis de configuración de ESA versión para mutar solo
  tasks/ y core/clock.py; si necesita copiar otros paquetes para correr los tests
  (core/, users/, main.py), configúralo.
- Añade a .gitignore los artefactos de mutmut (p. ej. mutants/ o .mutmut-cache) y
  verifica que htmlcov/ y .coverage ya están.
Muéstrame el diff y ejecuta pytest --cov --cov-report=term-missing para ver la línea base.
```

**Iteraciones:** ninguna.

### P12 — Tests unitarios del service

**Prompt principal:**

```text
Crea tests/test_tasks_service.py con tests UNITARIOS de @tasks/service.py
(sin TestClient). Unidad: create_task, get_task, list_tasks.
Reglas: las de @docs/feature-tasks.md.
Qué es dependencia y qué es lógica:
- Dependencias (mockear con monkeypatch): core.clock.today (reloj) y la consulta de
  usuarios a users.service (I/O simulado).
- Lógica bajo prueba (NO mockear): validación de fecha, idempotencia, filtro.
Casos (happy path primero, luego edge cases):
1. Crea tarea válida → status "pending" e id incremental.
2. due_date = ayer → 422; = hoy → OK; = None → OK.
3. assignee inexistente → 404 (el mock levanta not_found); assignee None → no consulta usuarios.
4. Idempotencia: misma clave y mismo cuerpo → misma tarea y created False;
   misma clave y otro cuerpo → 409; claves distintas → dos tareas.
5. Huella del cuerpo: el mismo contenido con description None frente a omitida (decide
   el comportamiento esperado y pregúntame si no está en la especificación).
6. list_tasks con filtro sin coincidencias → lista vacía.
Estilo: AAA con comentarios # Arrange / # Act / # Assert, un caso por test, nombre
en español, aserciones específicas (pytest.raises con .value.status_code y el detail).
Pregunta de control para cada test: "¿qué mutación no detectaría?". Si encuentras
alguno débil, refuérzalo. Ejecuta pytest -q y ruff check .
```

**Iteración 1:**

```text
Caso 5: description omitida y description None son el mismo cuerpo (decisión 3 y 7 de la
especificación): misma clave → misma tarea, created False, sin 409. Deja el test así.
Revisa además que ningún test mockea la lógica bajo prueba y que hay más líneas de
aserción que de mock; dame el recuento (líneas de mock / líneas de assert) y refuerza
los que no cumplan. Vuelve a ejecutar pytest -q.
```

### P13 — Test de integración users + tasks

**Prompt principal:**

```text
Crea tests/test_tasks_integration.py con 1–2 tests de INTEGRACIÓN que usen la app
real (TestClient de @tests/conftest.py), el repositorio en memoria real y el recurso
users real. Solo se fija el reloj (core.clock.today) con monkeypatch.

Mapa de dependencias: routes → tasks.service → tasks.repository y users.service →
users.repository. Nada de eso se mockea.

Flujo (receta numerada):
1. Estado inicial: usuarios semilla (Ada id=1) y ninguna tarea.
2. POST /users crea a "Margaret" → guarda su id.
3. POST /tasks asignada a Margaret con Idempotency-Key "k-1" → 201.
4. Repite el mismo POST con "k-1" → 200 y mismo id.
5. POST /tasks asignada a Ada sin clave → 201.
6. GET /tasks?assignee_id=<Margaret> → exactamente 1 tarea, la del paso 3.
7. GET /tasks/{id} → coincide con lo creado.
Éxito = todas las aserciones y que no haya estado filtrado de otros tests.

Documenta en el docstring del módulo el setup/teardown (fixture autouse de reset).
Ejecuta la suite completa dos veces y, si pytest-randomly está instalado, una tercera
en orden aleatorio. Dime si todas las ejecuciones dan el mismo resultado.
```

**Iteraciones:** ninguna.

### P14 — Cerrar huecos de cobertura

**Prompt principal:**

```text
Ejecuta pytest --cov --cov-branch --cov-report=term-missing y toma las líneas de
tasks/ y core/clock.py con sus columnas Missing y BrPart.
Para cada línea o rama faltante dime: qué caso de negocio representa, si vale la
pena probarlo o es código muerto, y el test concreto que la cubre. No escribas
tests que solo "ejecuten" líneas: cada test debe afirmar un resultado de la
especificación. Si encuentras código muerto, elimínalo en lugar de testearlo.
Después añade los tests acordados y vuelve a ejecutar la cobertura añadiendo
--cov-report=html. Objetivo: >90 % de líneas y de ramas en tasks/.
```

**Iteraciones:** ninguna.

### P15 — Mutation testing

**Prompt principal:**

```text
Ejecuta mutmut run y mutmut results. Para cada mutante superviviente ejecuta
mutmut show <id>.
Para cada uno: explica qué cambió el mutante, qué criterio de @docs/feature-tasks.md
debería haberlo detectado y por qué ningún test falló (¿aserción débil, límite sin
probar, código equivalente?). Clasifícalos en una tabla: matar con un test / mutante
equivalente (justificar) / código sobrante. Dame los totales (muertos / vivos /
equivalentes). No cambies código todavía.
Si mutmut no puede ejecutarse en este entorno, dímelo con el error exacto y haz en su
lugar estas mutaciones manuales UNA a UNA en tasks/service.py, ejecutando pytest -q
tras cada una y restaurando el código original después: (1) `<` → `<=` en la
comparación de due_date; (2) invertir la condición de la huella de idempotencia;
(3) devolver created=True siempre; (4) quitar el filtro por assignee_id. Entrega la
tabla mutación | resultado | test que la mató.
```

**Iteraciones:** ninguna.

### P16 — Matar mutantes supervivientes

**Prompt principal:**

```text
Escribe los tests que matan los mutantes clasificados como "matar con un test".
Cada test debe nombrar el criterio que protege. No modifiques el código de
producción. Ejecuta de nuevo mutmut (o la mutación manual) y muéstrame la tabla
antes/después: total, muertos, vivos y equivalentes; y la cobertura con ramas.
```

**Iteraciones:** ninguna.

## Fase 4 — Debugging

### P17a — Preparación del caso de debugging

**Prompt principal:**

```text
Prepara el caso de debugging del reto, con honestidad:
1. Revisa @docs/evidencia/bitacora.md (P5–P16): ¿hubo algún fallo real (tests en rojo
   inesperados, comodín de "tests en rojo", errores 500, tests inestables)?
2. Si lo hubo, recréalo temporalmente en el working tree revirtiendo SOLO su fix.
3. Si no lo hubo, reprodúcelo a propósito desde un estado realista: quita la limpieza de
   las claves de idempotencia en tasks.repository.reset(). Ejecuta pytest -q; si ningún
   test falla con ese cambio, revierte y usa en su lugar la comparación de due_date
   invertida a `<=` en tasks/service.py.
4. Confirma que pytest -q falla. No hagas commit ni arregles nada.
Dime en una línea qué opción usaste (real o reproducido) y qué cambiaste.
```

**Iteraciones:** ninguna.

### P17 — Reproducir y presentar el bug

**Prompt principal:**

```text
Ejecuta pytest -q. Tengo un fallo. Te lo presento:
- Qué esperaba: que toda la suite pase y que cada test cumpla su criterio CA-XX de
  @docs/feature-tasks.md partiendo de un estado limpio (fixture autouse de reset).
- Qué pasó: el stack trace COMPLETO de la salida de pytest (léelo entero, no solo la
  última línea).
- Cómo reproducirlo: pytest -q, y después el nodo exacto del primer test que falla
  (pytest <archivo>::<test> -q).
- Contexto: @tasks/service.py @tasks/repository.py @tests/conftest.py @core/clock.py.

Primero resume qué está pasando y en qué línea de MI código empieza el problema
(ignora los frames de FastAPI/Starlette). Después dame 2–3 hipótesis de la causa,
de más a menos probable, y cómo confirmar cada una. No cambies código todavía.
```

**Iteraciones:** ninguna.

### P18 — Confirmación de la hipótesis

**Prompt principal:**

```text
Ejecuta la confirmación que propusiste para la hipótesis 1 (print temporal, test
focalizado o lectura del código), muéstrame la salida observada y dime si la confirma
o la descarta. Si la descarta, haz lo mismo con la hipótesis 2 y luego con la 3.
Retira cualquier print o cambio temporal que hayas añadido. No corrijas el bug todavía.
```

**Iteraciones:** ninguna.

### P19a — Test de regresión en rojo

**Prompt principal:**

```text
Con la hipótesis confirmada, escribe primero un test de regresión que falle con el
código actual (nombre: test_regresion_<descripcion>), en el archivo de tests que
corresponda. Ejecútalo solo y muéstrame que falla por la causa confirmada.
No cambies código de producción.
```

**Iteraciones:** ninguna.

### P19 — Fix mínimo + test de regresión

**Prompt principal:**

```text
Aplica el FIX MÍNIMO que corrige la causa confirmada. No refactorices, no cambies
otros tests y no relajes validaciones. Ejecuta el test de regresión, la suite completa
(pytest -q) y ruff check ., y muéstrame el diff del fix.
```

**Iteración 1:**

```text
Revisa tu parche: si cambia algún test existente para que pase, toca archivos que no
tienen que ver con la causa o relaja una validación, recházalo y rehazlo como fix
mínimo; dime qué descartaste. Si cumple, confírmamelo en una línea.
```

## Fase 4 — Refactor y code review

### P20 — Inventario de code smells

**Prompt principal:**

```text
Revisa @tasks/service.py, @tasks/routes.py, @tasks/schemas.py y @tasks/repository.py
y lista los code smells que veas, con archivo:línea, por qué es un problema y el
refactor que propones (Extract function, Rename, Simplify conditional, constante
con nombre, parameter object…). Ordénalos por impacto en la mantenibilidad en una tabla
numerada. No cambies nada.
```

**Iteración 1:**

```text
Elijo, de tu tabla, los smells que encajen en estas categorías, en este orden (si alguna
no aparece, sustitúyela por el siguiente de mayor impacto de tu tabla):
1. Números mágicos (1, 5, 3, 120, 1000, 64) → constantes con nombre en tasks/schemas.py.
2. create_task demasiado larga (mezcla idempotencia, validación de dominio y
   persistencia) → Extract function para la huella y para las reglas de dominio.
3. Mensajes de error o literales duplicados → una sola definición.
Descarto el resto porque son cosméticos o de bajo impacto y no justifican riesgo en una
feature recién estabilizada, o porque romperían la consistencia con users/ (p. ej.
renombrados o cambios de estructura que users no sigue).
Dime la lista final de elegidos (numerada) y los descartados con su motivo.
No cambies nada todavía.
```

### P21.1 — Refactor 1

**Prompt principal:**

```text
Refactoriza en pasos pequeños los smells que elegimos en el paso anterior, en su orden.
Reglas:
- Un refactor por paso. Después de cada paso PARA, ejecuta pytest -q y ruff check .
  y espera a que te diga "sigue".
- No cambies el comportamiento: los tests NO se tocan. Si un test necesita cambiar,
  detente y explícame por qué.
- No borres abstracciones existentes (core/errors.py, capas) ni optimices sin datos.
Paso 1: el smell número 1 de la lista de elegidos.
```

**Iteraciones:** ninguna.

### P21.2 — Refactor 2

**Prompt principal:**

```text
sigue. Paso 2: el smell número 2 de la lista de elegidos. Si no queda ninguno, dímelo y no cambies nada.
```

**Iteraciones:** ninguna.

### P21.3 — Refactor 3

**Prompt principal:**

```text
sigue. Paso 3: el smell número 3 de la lista de elegidos. Si no queda ninguno, dímelo y no cambies nada.
```

**Iteraciones:** ninguna.

### P21.4 — Medición después del refactor

**Prompt principal:**

```text
fin. Ejecuta la cobertura con ramas y la mutación (mutmut run y mutmut results, o la
mutación manual si mutmut no corre) y compárala con la de antes del refactor.
```

**Iteraciones:** ninguna.

### P22 — Resultados de la refactorización

**Prompt principal:**

```text
Compara el código de tasks/ antes y después del refactor: usa git diff entre el último
commit anterior al primer refactor(tasks) y HEAD, limitado a tasks/. Resume en una
tabla: cambio realizado | smell que resuelve | impacto en claridad/mantenibilidad |
tests que lo protegieron. Incluye métricas simples (líneas por función, número de ramas
en create_task, constantes con nombre) y la cobertura y mutación antes/después.
```

**Iteraciones:** ninguna.

### P23 — Code review por categorías

**Prompt principal:**

```text
Revisa el diff de la rama contra main (git diff main...HEAD, excluyendo docs/evidencia/)
contra @CLAUDE.md y @docs/feature-tasks.md. Reporta hallazgos en una tabla numerada,
agrupados en: seguridad, corrección, manejo de errores, convenciones del proyecto,
tests y documentación. Para cada uno: archivo:línea, qué está mal, severidad propuesta
(bloqueante / menor / nota) y el arreglo sugerido. Señala también lo que NO puedes
juzgar (negocio, arquitectura). No cambies código.
```

**Iteración 1:**

```text
Clasifica cada hallazgo con esta regla y dame la tabla final:
- Bloqueante: incumple un CA-XX, una decisión de @docs/feature-tasks.md, una convención
  de @CLAUDE.md o introduce un riesgo de seguridad.
- Menor: claridad o estilo sin impacto en el comportamiento.
- Falso positivo: lo que es intencional por una decisión documentada (p. ej. 409 con
  conflict(), status 200 en la repetición idempotente, almacén en memoria sin caducidad
  de claves); responde cada uno con "intencional porque <decisión>".
Después corrige SOLO el primer bloqueante, ejecuta pytest -q y ruff check . y para.
Si no hay bloqueantes, dímelo y no cambies nada.
```

**Iteración 2:**

```text
Corrige el siguiente bloqueante de la tabla, ejecuta pytest -q y ruff check . y para.
Si no quedan bloqueantes, dímelo y no cambies nada.
```

**Iteración 3:**

```text
Corrige el siguiente bloqueante de la tabla, ejecuta pytest -q y ruff check . y para.
Si no quedan bloqueantes, dímelo y no cambies nada.
```

**Iteración 4:**

```text
Corrige el siguiente bloqueante de la tabla, ejecuta pytest -q y ruff check . y para.
Si no quedan bloqueantes, dímelo y no cambies nada.
```

## Fase 5 — Documentación

### P24 — Docstrings estilo Google

**Prompt principal:**

```text
Genera docstrings estilo Google para las funciones públicas de @tasks/service.py,
@tasks/repository.py y @core/clock.py, y un docstring de módulo para cada archivo
de tasks/ siguiendo el tono de @users/service.py.
Cada docstring: qué hace, Args, Returns, Raises (con código HTTP) y un Example
breve en las funciones clave (create_task: alta normal y repetición idempotente).
Describe lo que el código DEBE hacer según @docs/feature-tasks.md; si encuentras
una diferencia entre el código y la especificación, NO la documentes como correcta:
avísame. No cambies la lógica. No escribas docstrings triviales.
Ejecuta pytest -q y ruff check .
```

**Iteración 1:**

```text
Para cada diferencia código/especificación que encontraste: si el código incumple la
especificación, corrige el código con el cambio mínimo y añade un test que lo nombre;
si la especificación quedó desactualizada por una decisión ya registrada, actualiza
docs/feature-tasks.md. Si no hubo diferencias, confírmalo. Ejecuta pytest -q.
```

### P25 — Documentación OpenAPI

**Prompt principal:**

```text
Mejora la documentación OpenAPI de tasks sin cambiar el comportamiento:
- summary y description en cada ruta de @tasks/routes.py, y `responses=` con
  los códigos 200/201/404/409/422 y su significado.
- Field(description=..., examples=[...]) en @tasks/schemas.py y un ejemplo
  completo de TaskCreate (model_config json_schema_extra).
- Documenta la cabecera Idempotency-Key.
Ejecuta pytest -q y ruff check .
```

**Iteraciones:** ninguna.

### P26 — README para onboarding

**Prompt principal:**

```text
Actualiza @README.md a partir del repo REAL (@pyproject.toml, @requirements.txt,
@main.py, @tasks/routes.py, @docs/feature-tasks.md), sin inventar comandos:
1. Qué es el proyecto (añade el recurso tasks y su objetivo de trazabilidad).
2. Requisitos, instalación, arranque.
3. Tabla de endpoints actualizada (users + tasks) con códigos de respuesta.
4. Sección "Uso de tasks" con ejemplos curl: crear, repetir con Idempotency-Key
   (200), conflicto (409), validación (422), filtrar por responsable.
5. Tests y calidad: pytest, cobertura con ramas, umbral, mutmut, ruff.
6. "Guía rápida para colaboradores": estructura por capas, cómo añadir un recurso
   nuevo siguiendo tasks/ como plantilla y dónde están las convenciones (CLAUDE.md).
7. Enlaces a CHANGELOG.md, docs/feature-tasks.md y docs/adr/.
Mantén las secciones existentes que sigan siendo ciertas (tabla de ramas del módulo).
Después ejecuta cada comando y cada curl del README (con la app en segundo plano),
corrige lo que no funcione, dime qué corregiste y detén la app.
```

**Iteraciones:** ninguna.

### P27 — CHANGELOG y ADR

**Prompt principal:**

```text
1. Crea CHANGELOG.md con el formato "Keep a Changelog" y versionado semántico.
   Versión 0.2.0 con la fecha de hoy (Added / Changed / Fixed), a partir de
   `git log main..HEAD --oneline`. Incluye la entrada 0.1.0 como base existente.
   Actualiza la versión a 0.2.0 en @pyproject.toml y en FastAPI(version=) de @main.py
   (si main.py no declara version, añádela).
2. Crea docs/adr/0001-idempotencia-en-alta-de-tareas.md (Contexto, Decisión,
   Alternativas consideradas, Consecuencias). Redacta la estructura y las
   alternativas técnicas; el PORQUÉ de negocio es este: el objetivo del sprint es
   reducir las pérdidas de trabajo no registrado y mejorar la trazabilidad; los
   reintentos del cliente ante timeouts o fallos de red, y los dobles envíos del
   equipo de soporte operativo, podían duplicar tareas y romper esa trazabilidad.
3. Ejecuta pytest -q y ruff check .
```

**Iteraciones:** ninguna.

## Fase 6 — Evidencia y cierre

### P28 — Compilar la evidencia

**Prompt principal:**

```text
Con @docs/evidencia/bitacora.md, los logs de docs/evidencia/logs/, las capturas de
docs/evidencia/capturas/ y git log main..HEAD, genera dos documentos:

A) docs/evidencia/EVIDENCIA.md siguiendo EXACTAMENTE la estructura del formato de entrega:
1. Especificación y contexto (1.a funcionalidad y criterios, 1.b contexto para la IA
   con los @archivos usados y el diff de CLAUDE.md, 1.c patrón y justificación).
2. Generación (2.a iteraciones solicitud → revisión → refinamiento con snippets,
   2.b integración y linting, 2.c tabla de propuestas aceptadas/rechazadas y por qué).
3. Tests (3.a unitarios con AAA y mocks, 3.b integración con fixtures y
   setup/teardown, 3.c tabla de cobertura antes/después y tabla de mutación).
4. Debugging y refactor (4.a trace, hipótesis, confirmación, fix y regresión;
   4.b refactors y red de seguridad; 4.c resultados).
5. Documentación (5.a docstrings y README, 5.b changelog, 5.c índice de prompts y
   capturas).
6. Reflexión: deja solo el título y el texto "[PENDIENTE: reflexión]".

B) docs/evidencia/prompts.md: índice de los prompts usados, por fase y paso, con cada
   prompt literal tal como aparece en la bitácora (prompt principal e iteraciones).

Usa solo datos reales de los logs: si falta un dato, márcalo como [PENDIENTE] en
lugar de inventarlo. Donde vaya una imagen, enlaza la captura que corresponda con
ruta relativa. Al final dame la lista de [PENDIENTE] que dejaste.
```

**Iteraciones:** ninguna.

### P29 — Reflexión final

**Prompt principal:**

```text
Voy a escribir la reflexión final del reto. Hazme entre 8 y 10 preguntas difíciles
basadas en @docs/evidencia/bitacora.md para que la reflexión sea profunda, por ejemplo:
qué propuesta de la IA casi se acepta y habría sido un error, qué contexto cambió más
la calidad de la salida, dónde la cobertura daba falsa seguridad y la mutación lo
destapó, qué hipótesis de debugging fue incorrecta, qué haría distinto en el próximo
proyecto, qué prompts reutilizaría como plantilla y qué tareas no delegaría a la IA.
```

**Iteración 1:**

```text
Revisa la ortografía, la redacción y la claridad de toda @docs/evidencia/EVIDENCIA.md
sin cambiar las ideas ni añadir contenido. Aplica los cambios y dime cuántos hiciste.
```

### P30 — Verificación final

**Prompt principal:**

```text
Verifica la definición de hecho de @CLAUDE.md y el checklist de entrega:
ejecuta pytest -q, la cobertura con ramas, ruff check . y git status.
Comprueba que cada criterio CA-XX de @docs/feature-tasks.md tiene al menos un
test que lo nombra, que README/CHANGELOG/ADR/EVIDENCIA/prompts existen y que no se
modificaron migrations/ ni legacy/ (git diff main...HEAD --stat).
Entrega una tabla requisito | estado | evidencia. No cambies código.
```

**Iteraciones:** ninguna.
