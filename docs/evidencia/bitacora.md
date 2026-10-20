# Bitácora del reto M2 — recurso tasks

- **Fecha:** 2026-10-19
- **Rama:** feature/tasks
- **Herramienta:** Claude Code

## Paso P0 — Línea base del proyecto

- **Prompt usado:**

  ```text
  Antes de empezar el reto, verifica la línea base del proyecto sin tocar nada:
  ejecuta pytest -q, pytest --cov=. --cov-branch --cov-report=term-missing y ruff check .
  Dime si todo está en verde. Si algo falla, detente y explícame qué falla.
  ```

- **Qué propuso la IA:**
  - Ejecutó los tres comandos con `.venv` activado, sin modificar ningún archivo.
  - Informó que la línea base está en verde: 6 tests pasan, cobertura total 98 % y ruff sin avisos.
  - Señaló las dos líneas sin cubrir, que son huecos de cobertura previos y no fallos:
    `core/errors.py:20` (cuerpo de `invalid_request()`, el 422) y `main.py:16` (`GET /health`).
  - Propuso usar ese 98 % como referencia para comparar durante el reto.

  ```text
  Name                  Stmts   Miss Branch BrPart  Cover   Missing
  -----------------------------------------------------------------
  core/errors.py            7      1      0      0    86%   20
  main.py                   7      1      0      0    86%   16
  users/repository.py      23      0      2      0   100%
  users/routes.py          13      0      0      0   100%
  users/service.py         14      0      4      0   100%
  -----------------------------------------------------------------
  TOTAL                   113      2      6      0    98%
  6 passed in 0.11s
  ```

- **Qué acepté / rechacé y por qué:** Aceptado tras revisar que los tres comandos
  terminan con código de salida 0 y que las líneas sin cubrir no corresponden a fallos.
- **Iteraciones:** ninguna.
- **Validación:**
  - `pytest -q` → 6 tests sin fallos (`......  [100%]`). No aparece la línea de resumen
    porque `pyproject.toml` ya define `addopts = "-q"` y el `-q` extra la suprime.
    Log: [`logs/00-linea-base-tests.txt`](logs/00-linea-base-tests.txt)
  - `pytest --cov=. --cov-branch --cov-report=term-missing` → 6 passed, cobertura 98 %
    (faltan `core/errors.py:20` y `main.py:16`).
    Log: [`logs/00-linea-base-cobertura.txt`](logs/00-linea-base-cobertura.txt)
  - `ruff check .` → All checks passed!
    Log: [`logs/00-linea-base-ruff.txt`](logs/00-linea-base-ruff.txt)
- **Captura:** [P00-linea-base.png](capturas/P00-linea-base.png)
- **Commit:** `pendiente`

## Paso P1 — Exploración del repo

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Capas: `routes.py` (solo `APIRouter` + `response_model=` y delega), `service.py` (reglas y
    errores, único que importa `repository`), `schemas.py` (`XBase` / `XCreate` / `X`) y
    `repository.py` (`dict` en memoria, `_next_id`, `_SEED`, `reset()`).
  - Errores: funciones de `core/errors.py` que devuelven `HTTPException` (404 / 422 / 409) con
    `{"detail": "<texto>"}`. Las validaciones de Pydantic también responden 422, pero con `detail` en forma de lista.
  - Aislamiento: fixture `autouse` `_reset_data` en `tests/conftest.py`, que hoy solo resetea `users`.
  - Convenciones: inglés + `snake_case`, mensajes en español, tests `test_<función>_<descripción>`
    con preparación, ejecución y comprobación separadas; ruff `E,F,I,UP,B`, líneas de 100 y py310.
  - Riesgos: reset de `tasks` en `conftest`, orden de rutas, ambigüedad del 422, referencias a
    `users` vía service, copia en updates (`model_copy`), ids dependientes de la semilla y falta
    de especificación de campos.

  ```python
  @pytest.fixture(autouse=True)
  def _reset_data():
      """Cada test arranca con los datos semilla y no contamina a los demás."""
      repository.reset()
      yield
      repository.reset()
  ```

- **Qué acepté / rechacé y por qué:** No rechacé nada del resumen. Pedí contrastarlo con una
  lista de control para asegurar que recogía todas las convenciones obligatorias de CLAUDE.md.
  Acepté la versión completada: confirmaba tres puntos, precisaba dos y añadía el que faltaba.
- **Iteraciones:**

  ```text
  Comprueba tu resumen contra esta lista y completa lo que falte: uso de response_model=
  en todas las rutas, catálogo core/errors.py (sin HTTPException a mano), repository.reset()
  invocado por una fixture autouse de conftest.py, rutas específicas antes que rutas con
  parámetro, y migrations/ y legacy/ fuera de límites. Dime qué puntos ya estaban y cuáles
  añadiste. No cambies código.
  ```

  → La IA indicó que ya estaban el `reset()` autouse y el orden de rutas (este último como
  riesgo), que estaban a medias `response_model=` y la prohibición de `HTTPException` a mano,
  y que faltaba `migrations/` y `legacy/` fuera de límites. También señaló que `GET /health`
  en `main.py` devuelve un `dict` crudo sin `response_model=` (excepción previa, no replicable).
  → Ajuste: el resumen queda completo con las cinco convenciones; sin cambios de código.
- **Validación:** ninguna (paso de solo lectura, sin comandos).
- **Captura:** N/A
- **Commit:** `pendiente`

## Paso P2 — Especificación y criterios de aceptación

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Redactó `docs/feature-tasks.md` con las seis secciones pedidas: historia, objetivo,
    alcance, contrato con tablas de request, response y códigos, 23 criterios Dado/Cuando/Entonces y ejemplos curl.
  - Añadió dos criterios derivados del contrato: formato inválido de `due_date` → 422 y
    `Idempotency-Key` vacía o de más de 64 caracteres → 422.
  - Planteó 15 preguntas abiertas: límites, tipos laxos de Pydantic, zona horaria,
    precedencia de errores, huella de idempotencia, fallos con clave, filtro con usuario
    inexistente, orden del listado, datos semilla e ids ≤ 0.
  - Tras las respuestas, añadió la sección "Decisiones" con 17 puntos y 5 decisiones
    conservadoras propias (A1–A5). Rellenó los `[AJUSTAR]` con `already_exists` (409) e
    `invalid_request` (fecha pasada) y amplió los criterios a CA-01…CA-43, todos con valores concretos.

  ```markdown
  **Orden de evaluación**

  1. Forma del cuerpo y de la cabecera → `422` (Pydantic, formato por defecto).
  2. `due_date` anterior a hoy → `422` (dominio, `errors.invalid_request`).
  3. Búsqueda de la `Idempotency-Key` → `200` (misma huella) o `409` (huella distinta).
  4. Existencia del responsable → `404` (`errors.not_found`).
  5. Creación → `201`; si hay clave, se guarda junto con la huella y la tarea.

  - **CA-27 — Huella normalizada.**
    - **Dado** un `POST` con `K` y `{"title": "Revisar"}` que devolvió `201`.
    - **Cuando** hago `POST` con `K` y `{"priority": 3, "title": " Revisar "}`.
    - **Entonces** recibo `200` con la misma tarea.
  ```

- **Qué acepté / rechacé y por qué:** Acepté la estructura del documento y las 15 preguntas.
  No dejé que la IA asumiera respuestas: las decidí yo para cerrar la especificación antes
  de implementar y para que cada CA fuera verificable con un test. Pedí aplicar la opción más
  conservadora en lo no cubierto. Acepté las decisiones A1–A5 que propuso la IA.
  - **Decisiones clave:**
    1. Límites de `title` → 3 y 120 inclusivos tras `strip`. Solo espacios → 422 con el
       mensaje por defecto de Pydantic. Si no es texto → 422.
    2. `description` → no se recorta, `""` es válido, omitida = `null`, el máximo de 1000 se
       cuenta sobre el valor recibido y no hay mínimo.
    3. Tipos de `priority` → entero estricto (`3.0`, `"3"`, `true`, `null` → 422). Omitida → 3.
    4. Formato y zona de `due_date` → solo `YYYY-MM-DD`; con hora o fecha inexistente → 422.
       "Hoy" = fecha UTC del servidor vía `core/clock.py`. Sin máximo. Omitida = `null`.
    5. `assignee_id` 0, negativo o `null` → 0 o negativo da 422; ≥ 1 inexistente da 404 con
       `errors.not_found`; `null` = sin responsable.
    6. Precedencia de errores → forma (422), fecha pasada (422), clave (200/409),
       responsable (404), creación. El 422 va antes que el 404.
    7. Campos desconocidos o asignados por el servidor → comportamiento por defecto de
       Pydantic, como en `users`; el servidor pone siempre los suyos.
    8. "Mismo cuerpo" → huella sobre el cuerpo validado y normalizado; no importa el orden
       de claves; `" Revisar "` = `"Revisar"`.
    9. Primera petición con clave que falla → la clave no se guarda (solo tras 201). Cuerpo
       inválido con clave usada → 422.
    10. Alcance de la clave → global, sin caducidad, limpiada por `reset()`, sin `strip`,
        sensible a mayúsculas, 1–64 caracteres por `len()`.
    11. Respuesta repetida → 200 con la Task idéntica. Huella distinta → 409 con la función
        de conflicto del catálogo, sin funciones nuevas.
    12. Filtro con usuario inexistente → 200 `[]` (también 0 y negativos). No entero → 422.
    13. Orden del listado → `id` ascendente.
    14. Datos semilla → almacén vacío; `reset()` vacía tareas y claves.
    15. `GET /tasks/{task_id}` ≤ 0 → 404. No entero → 422.
    - Además: `status` solo `"pending"`, `created_at` en UTC ISO 8601. El 422 de fecha
      pasada se valida en el service con `core/errors.py`.
- **Iteraciones:**

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

  → La IA añadió la sección "Decisiones" (1–17) y "Decisiones propuestas por la IA y
  aceptadas":
  - A1: `assignee_id` es un entero estricto.
  - A2: repetir con clave cuando la fecha ya ha pasado → 422.
  - A3: el 404 dice "tarea no encontrado" porque se usa el catálogo sin cambios.
  - A4: el recorte es `str.strip()`.
  - A5: la huella solo incluye los cinco campos de entrada.

  Concretó los `[AJUSTAR]` como `errors.already_exists("clave de idempotencia", <clave>)` y
  `errors.invalid_request("la fecha límite no puede ser anterior a hoy (UTC)")`.
  → Ajuste: contrato con tipos estrictos, orden de evaluación y doble formato de 422; los
  criterios pasan de 23 a 43 (CA-01…CA-43), con el reloj fijado en `2026-10-20` para los de fecha.
- **Validación:** ninguna (paso de especificación, sin comandos).
- **Captura:** N/A
- **Commit:** `docs: especificación y criterios de aceptación de tasks`

## Paso P3 — Convenciones en CLAUDE.md

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - En "Estructura" añadió `tasks/` (mismo patrón de 4 archivos), `core/clock.py` como único
    punto que consulta la fecha del sistema, `docs/` (especificaciones y ADR) y los nombres
    `test_users.py` y `test_tasks.py` en la línea de `tests/`.
  - En "Convenciones" añadió las cinco reglas pedidas al final de la lista, sin tocar las existentes.
  - En "Cómo ejecutar" añadió la cobertura de ramas y `mutmut run` / `mutmut results` para
    mutation testing. Avisó de que no verificó que `mutmut` esté instalado.
  - Creó la sección "Definición de hecho" entre "Cómo ejecutar" y "Fuera de límites". Avisó
    de que `CHANGELOG.md` aún no existe.
  - Diff de `CLAUDE.md`:

  ```diff
  diff --git a/CLAUDE.md b/CLAUDE.md
  index 747ece0..c00e925 100644
  --- a/CLAUDE.md
  +++ b/CLAUDE.md
  @@ -11,8 +11,13 @@ el proyecto corre sin infraestructura.
     - `service.py` — lógica de negocio. Única capa que habla con `repository.py`.
     - `schemas.py` — modelos Pydantic de entrada (`*Create`) y salida.
     - `repository.py` — acceso a datos (aquí, un `dict` en memoria).
  +- `tasks/` — tareas de equipo. Mismo patrón de 4 archivos que `users/`
  +  (`routes.py`, `service.py`, `schemas.py`, `repository.py`).
   - `core/errors.py` — catálogo de errores. Toda respuesta de error sale de aquí.
  -- `tests/` — un archivo por recurso: `test_<recurso>.py`.
  +- `core/clock.py` — reloj de la aplicación (fecha actual en UTC). Único punto que consulta
  +  la fecha del sistema.
  +- `docs/` — especificaciones de features (`feature-<recurso>.md`) y ADR.
  +- `tests/` — un archivo por recurso: `test_<recurso>.py` (`test_users.py`, `test_tasks.py`).
   
   ## Convenciones
   
  @@ -25,6 +30,14 @@ el proyecto corre sin infraestructura.
     feliz y un caso de error.
   - Rutas específicas antes que rutas con parámetro: `/users/search` debe declararse
     **antes** de `/users/{user_id}`.
  +- La lógica que depende de la fecha actual no llama a `date.today()` ni a `datetime.now()`
  +  directamente: usa una función de `core/clock.py` para poder mockearla en los tests.
  +- Las validaciones de forma (tipos, rangos, longitudes) van en los schemas Pydantic. Las
  +  reglas de dominio (fecha pasada, responsable inexistente, idempotencia) van en `service.py`
  +  con `core/errors.py`.
  +- Un recurso consulta otro recurso a través de su `service.py`, nunca de su `repository.py`.
  +- Todo repositorio nuevo expone `reset()` y la fixture autouse de `tests/conftest.py` lo invoca.
  +- Docstrings estilo Google en las funciones públicas de `service.py`.
   
   ## Cómo ejecutar
   
  @@ -36,9 +49,22 @@ pip install -r requirements.txt
   uvicorn main:app --reload          # API en http://127.0.0.1:8000  ·  /docs para el Swagger
   pytest                             # tests
   pytest --cov=. --cov-report=term-missing   # cobertura
  +pytest --cov --cov-branch --cov-report=term-missing   # cobertura de ramas
   ruff check .                       # linter
  +mutmut run                         # mutation testing
  +mutmut results                     # mutantes supervivientes
   ```
   
  +## Definición de hecho
  +
  +Un cambio está hecho cuando:
  +
  +- `pytest` está en verde.
  +- La cobertura de `tasks/` supera el 90 % (`pytest --cov=tasks --cov-branch`).
  +- `ruff check .` está limpio.
  +- Las funciones públicas de `service.py` tienen docstrings estilo Google.
  +- `README.md` y `CHANGELOG.md` están actualizados.
  +
   ## Fuera de límites
   
   - `migrations/` y `legacy/` — no modificar.
  ```

- **Qué acepté / rechacé y por qué:**
  - Rechacé la primera ejecución de la IA. Antes de editar, quiso consultar `requirements.txt`
    y los paquetes instalados (`pip list`) para identificar la herramienta de mutation testing.
    Interrumpí esa llamada y reenvié la misma petición. Motivo: [PENDIENTE].
  - Acepté el diff tras revisar que conserva intactas las reglas de `response_model=`, del
    orden de rutas y de `migrations/` y `legacy/`.
  - Registré como decisión del paso el patrón de generación (ver sub-sección).

  ### Patrón elegido (1.c)

  - **Patrón:**
    - Skeleton-first para la estructura: `tasks/schemas.py`, `tasks/repository.py` con
      `reset()`, `tasks/service.py`, `tasks/routes.py`, `core/clock.py`, router en `main.py`
      y reset en `conftest.py`.
    - Seguido de test-first para las reglas.
    - Todo con cadencia incremental: un criterio por iteración y un commit por paso.
  - **Justificación:**
    - Skeleton-first, porque es una feature nueva con varias piezas (schemas, repositorio,
      service, rutas y reloj) y conviene fijar antes la estructura.
    - Test-first para las reglas, porque son verificables y están en los criterios CA-XX de
      `docs/feature-tasks.md`.
    - Incremental, para que cada paso sea pequeño, revisable y quede en verde.
  - **Señales de alarma:**
    - Skeleton-first → que el esqueleto traiga lógica (validaciones, reglas de dominio,
      idempotencia) en vez de solo firmas, modelos y conexiones entre capas.
    - Test-first → que los tests se escriban leyendo el código y no los criterios. Cada test
      debe citar su CA-XX y usar los valores del documento.
    - Incremental → pasos que mezclen varias reglas, o commits sin tests en verde.

- **Iteraciones:**

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

  → La IA comprobó con `grep` que las tres reglas siguen en `CLAUDE.md` (líneas 24, 31-32 y
  70) y que la única línea borrada del diff es la de `tests/`, reemplazada por una versión
  ampliada. No restauró nada porque no faltaba nada. Anotó el patrón de generación y sus
  señales de alarma como decisión del paso.
  → Ajuste: ninguno en `CLAUDE.md`; el patrón queda registrado en esta entrada.
- **Validación:** `pytest -q` → 6 tests sin fallos (`......  [100%]`, exit 0); el cambio
  es solo de documentación y no altera la suite.
  Log: [`logs/03-tests.txt`](logs/03-tests.txt)
- **Captura:** N/A
- **Commit:** `docs(claude): convenciones para el recurso tasks`

## Paso P4 — Skeleton-first: esqueleto de tasks

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Un plan (modo plan) con los 6 archivos, las firmas y los CA-XX de cada TODO, siguiendo
    el patrón de `users/`.
  - `core/clock.py` con `today() -> date` y `tasks/__init__.py` vacío.
  - `tasks/schemas.py`: `TaskBase` (`title: str`, `description: str | None`,
    `priority: int = 3`, `due_date: date | None`, `assignee_id: int | None`), `TaskCreate` y
    `Task` (`id`, `status`, `created_at`), con TODOs de validación por campo.
  - `tasks/repository.py` y `tasks/service.py`: firmas con `raise NotImplementedError`,
    docstrings Google en el service y TODOs en el orden de evaluación del contrato.
  - `tasks/routes.py`: 3 rutas con `response_model=`, `POST` con 201 y cabecera
    `Header(default=None, alias="Idempotency-Key")` (opcional, según CA-33).
  - Dejó fuera del paso `main.py` y la llamada a `reset()` en `conftest.py`, porque
    `NotImplementedError` rompería los tests de `users`.

  ```python
  @router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
  def create_task(
      data: TaskCreate,
      # TODO(CA-32): min_length=1, max_length=64 en el Header.
      idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
  ) -> Task:
      # TODO(CA-26, CA-27): responder 200 (no 201) en una repetición idempotente.
      return service.create_task(data, idempotency_key)
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan antes de que se escribiera código.
  - Pedí una revisión con una lista de comprobación (sin lógica, nombres, tipos y
    `Header(...)`) para vigilar la señal de alarma de skeleton-first: que el esqueleto traiga
    lógica.
  - Rechacé el desempaquetado `task, created = service.create_task(...)` en la ruta y el
    retorno `tuple[Task, bool]` del service, por ser lógica en un esqueleto.
  - La cabecera queda opcional (`Header(default=None, alias=...)`) en lugar de `Header(...)`
    literal, que la haría obligatoria y contradiría CA-33. Es una decisión propuesta por la
    IA y aceptada.

- **Iteraciones:**

  ```text
  Revisa tu esqueleto con esta lista y corrige lo que no cumpla, diciéndome qué cambiaste:
  1. ¿Alguna función tiene lógica (if, bucles, cálculos, acceso real a datos)? Si sí,
     vacíala: el esqueleto debe estar "más vacío".
  2. Nombres en inglés y snake_case, sin abreviaturas, como en users/.
  3. Tipos: due_date: date | None, assignee_id: int | None, priority: int.
  4. La ruta POST lee Idempotency-Key con Header(...) y no contiene lógica.
  Vuelve a ejecutar ruff check . y pytest -q.
  ```

  → La IA encontró lógica en la ruta `POST` (el desempaquetado de la tupla). Confirmó que
  los nombres y los tipos ya cumplían, y explicó por qué la cabecera usa
  `Header(default=None, alias="Idempotency-Key")`.
  → Ajuste: la ruta queda como `return service.create_task(...)` con un TODO(CA-26, CA-27);
  `create_task` devuelve `Task` en lugar de `tuple[Task, bool]`.

- **Validación:**
  - `ruff check .` → `All checks passed!`. Log: [`logs/04-ruff.txt`](logs/04-ruff.txt)
  - `pytest -q` → 6 tests sin fallos (`......  [100%]`), todos de `users`; `tasks` aún no
    está montado. Log: [`logs/04-tests.txt`](logs/04-tests.txt)
- **Captura:** N/A
- **Commit:** `feat(tasks): esqueleto del recurso`

## Paso P5 — Test-first: tests de aceptación en rojo

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Un plan (modo plan) con los 43 tests, uno por CA. Los CA con varios valores usan
    `@pytest.mark.parametrize`, lo que da 81 casos.
  - Implementar solo `tasks.repository.reset()`, que vacía las tareas y las claves y
    reinicia `_next_id`.
  - Ampliar la fixture autouse `_reset_data` de `tests/conftest.py` para que resetee `users`
    y `tasks`, sin fixtures paralelas.
  - Fijar "hoy" en `2026-10-20` (la fecha de los criterios, en lugar de la `2026-01-15` del
    ejemplo) con una fixture autouse en `test_tasks.py`; CA-19 la cambia a `2026-10-21`.
  - Comprobar los 404 de dominio con el texto `"no encontrado"`, para que no pasen con el
    404 genérico `"Not Found"` mientras el router no está montado.
  - Mantener el router fuera de `main.py`: todos los tests de tasks fallan con 404 de ruta.

  ```python
  TODAY = date(2026, 10, 20)


  @pytest.fixture(autouse=True)
  def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
      """Los criterios con fecha parten de hoy = 2026-10-20 (UTC)."""
      monkeypatch.setattr("core.clock.today", lambda: TODAY)


  def test_ca16_fecha_limite_ayer_devuelve_422_con_detalle_en_texto(client: TestClient) -> None:
      body = {"title": "Revisar backups", "due_date": "2026-10-19"}

      response = _post(client, body)

      assert response.status_code == 422
      assert "anterior a hoy" in response.json()["detail"]
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan antes de que se escribiera código.
  - Acepté fijar "hoy" en `2026-10-20` en lugar de `2026-01-15`, para que los valores de los
    tests coincidan con los de los criterios. Es una decisión propuesta por la IA y aceptada.
  - Acepté que el router siga fuera de `main.py`, de modo que la razón del rojo sea el 404 de
    ruta inexistente.
  - Antes de dar los tests por buenos pedí una verificación (cobertura CA → test, límites a
    ambos lados y que no se use la fecha real), para vigilar la señal de alarma de test-first:
    que los tests salgan del código y no de los criterios.

- **Iteraciones:**

  ```text
  Antes de dar los tests por buenos, verifica: (1) cada CA-XX de @docs/feature-tasks.md
  tiene al menos un test que lo nombra; dame la tabla CA → test; (2) los límites están a
  ambos lados (ayer/hoy, 2/3 y 120/121 caracteres, priority 0/1 y 5/6); (3) ningún test
  usa la fecha real. Añade lo que falte sin implementar código de producción y vuelve a
  ejecutar pytest -q.
  ```

  → La IA cruzó con un script los 43 `CA-XX —` de la especificación con las funciones
  `test_caXX_` y no faltaba ninguno. Confirmó los límites a ambos lados: fecha
  `2026-10-19`/`2026-10-20`/`2026-10-21`, `title` 2/3 y 120/121, `priority` 0/1 y 5/6, y
  además `description` 1000/1001, clave 1/64 frente a vacía/65 y `assignee_id` 0/1. Con
  `grep` comprobó que no hay `date.today`, `datetime.now`, `utcnow` ni `time.time` en `tests/`.
  → Ajuste: ninguno; no faltaba nada. Se repitió `pytest -q` con el mismo resultado.

  **Tabla CA → test** (`tests/test_tasks.py`):

  | CA | Test |
  |---|---|
  | CA-01 | `test_ca01_creacion_minima_devuelve_201_con_valores_por_defecto` |
  | CA-02 | `test_ca02_creacion_completa_devuelve_los_valores_enviados` |
  | CA-03 | `test_ca03_ignora_campos_del_servidor_y_desconocidos` |
  | CA-04 | `test_ca04_titulo_se_recorta` |
  | CA-05 | `test_ca05_titulo_en_los_limites_3_y_120_devuelve_201` |
  | CA-06 | `test_ca06_titulo_corto_o_vacio_devuelve_422` |
  | CA-07 | `test_ca07_titulo_de_121_caracteres_devuelve_422` |
  | CA-08 | `test_ca08_titulo_ausente_o_no_texto_devuelve_422` |
  | CA-09 | `test_ca09_descripcion_se_guarda_tal_cual` |
  | CA-10 | `test_ca10_descripcion_omitida_o_null_se_guarda_null` |
  | CA-11 | `test_ca11_descripcion_maximo_1000_sobre_el_valor_recibido` |
  | CA-12 | `test_ca12_prioridad_por_defecto_3_y_limites_1_y_5` |
  | CA-13 | `test_ca13_prioridad_fuera_de_rango_devuelve_422` |
  | CA-14 | `test_ca14_prioridad_no_entera_estricta_devuelve_422` |
  | CA-15 | `test_ca15_fecha_limite_hoy_o_futura_devuelve_201` |
  | CA-16 | `test_ca16_fecha_limite_ayer_devuelve_422_con_detalle_en_texto` |
  | CA-17 | `test_ca17_fecha_limite_con_formato_o_fecha_invalidos_devuelve_422` |
  | CA-18 | `test_ca18_fecha_limite_omitida_o_null_se_guarda_null` |
  | CA-19 | `test_ca19_la_referencia_es_el_reloj_del_servidor` |
  | CA-20 | `test_ca20_responsable_existente_devuelve_201` |
  | CA-21 | `test_ca21_responsable_inexistente_devuelve_404` |
  | CA-22 | `test_ca22_responsable_con_forma_invalida_devuelve_422` |
  | CA-23 | `test_ca23_responsable_null_explicito_queda_sin_responsable` |
  | CA-24 | `test_ca24_la_forma_gana_al_responsable_inexistente` |
  | CA-25 | `test_ca25_la_fecha_pasada_gana_al_responsable_inexistente` |
  | CA-26 | `test_ca26_misma_clave_y_mismo_cuerpo_devuelve_200_con_la_misma_tarea` |
  | CA-27 | `test_ca27_la_huella_se_calcula_sobre_el_cuerpo_normalizado` |
  | CA-28 | `test_ca28_misma_clave_y_cuerpo_distinto_devuelve_409` |
  | CA-29 | `test_ca29_un_fallo_no_guarda_la_clave` |
  | CA-30 | `test_ca30_cuerpo_invalido_con_clave_usada_devuelve_422` |
  | CA-31 | `test_ca31_la_clave_distingue_mayusculas` |
  | CA-32 | `test_ca32_longitud_de_la_clave_entre_1_y_64` |
  | CA-33 | `test_ca33_sin_clave_no_hay_deduplicacion` |
  | CA-34 | `test_ca34_listado_vacio_devuelve_lista_vacia` |
  | CA-35 | `test_ca35_listado_completo_ordenado_por_id` |
  | CA-36 | `test_ca36_filtro_por_responsable_devuelve_solo_sus_tareas` |
  | CA-37 | `test_ca37_filtro_sin_coincidencias_devuelve_lista_vacia` |
  | CA-38 | `test_ca38_filtro_no_entero_devuelve_422` |
  | CA-39 | `test_ca39_consultar_tarea_existente_devuelve_la_misma_tarea` |
  | CA-40 | `test_ca40_consultar_tarea_inexistente_devuelve_404` |
  | CA-41 | `test_ca41_task_id_no_entero_devuelve_422` |
  | CA-42 | `test_ca42_reset_limpia_tareas_y_claves` |
  | CA-43 | `test_ca43_errores_de_dominio_en_texto_y_de_forma_en_lista` |

- **Validación:**
  - `pytest -q` → 81 casos de `tests/test_tasks.py` en rojo (43 tests) y 6 de `users` en
    verde. Todos los rojos se deben al 404 de ruta inexistente: `assert 404 == 422` (38),
    `assert 404 == 201` (31), `assert 404 == 200` (6), `'no encontrado' in 'Not Found'` (4),
    `{'detail': 'Not Found'} == []` (1) y `KeyError: 'id'` porque el cuerpo del 404 no trae
    `id` (1). No hay errores de colección, `SyntaxError` ni `ImportError`.
    Log: [`logs/05-tests-rojos.txt`](logs/05-tests-rojos.txt)
  - `ruff check .` → `All checks passed!` (ejecutado en el paso; sin log propio).
- **Captura:** ![Tests de aceptación en rojo](capturas/P05-tests-rojos.png)
- **Commit:** `test(tasks): tests de aceptación (rojo)`

## Paso P6 — Incremental 1: happy path

- **Prompt usado:**

  ```text
  Implementa SOLO lo necesario para que pasen los tests del happy path:
  crear tarea (CA de 201 con status "pending"), GET /tasks/{id} existente e
  inexistente (404) y GET /tasks. Registra el router en @main.py siguiendo cómo se
  registra users_router. Implementa core/clock.py (hoy en UTC).

  No implementes validaciones, idempotencia ni assignee todavía. Fix mínimo:
  no toques los tests. Luego ejecuta pytest -q y ruff check . y dime qué tests pasan
  y cuáles siguen en rojo (deben ser los de las reglas pendientes).
  ```

- **Qué propuso la IA:**
  - Un plan (modo plan) con los cambios mínimos y la previsión de qué tests pasarían a verde
    y cuáles seguirían en rojo.
  - Registrar `tasks_router` en `main.py` igual que `users_router`.
  - En `core/clock.py`, `today()` en UTC y además `now()` para `created_at`, porque
    `CLAUDE.md` dice que `core/clock.py` es el único punto que consulta la fecha del sistema.
  - En `tasks/repository.py`, implementar `add` (con `status="pending"`), `get` y `list_all`
    con el patrón de `users`. `list_by_assignee` y las funciones de idempotencia siguen en
    `NotImplementedError`.
  - En `tasks/service.py`, `create_task` delega en `repository.add` sin comprobaciones,
    `get_task` da 404 con `errors.not_found` y `list_tasks` sin filtro llama a `list_all`.
  - No tocar `routes.py`, `schemas.py` ni los tests.

  ```python
  def get_task(task_id: int) -> Task:
      task = repository.get(task_id)
      if task is None:
          raise errors.not_found("tarea", task_id)
      return task


  def list_tasks(assignee_id: int | None) -> list[Task]:
      if assignee_id is None:
          return repository.list_all()
      # TODO(CA-36, CA-37): implementar repository.list_by_assignee (sin comprobar que el
      #     usuario exista).
      return repository.list_by_assignee(assignee_id)
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan antes de que se escribiera código.
  - Acepté añadir `clock.now()`, que no estaba pedido, para cumplir la regla de `CLAUDE.md`
    sobre el único punto de consulta de la fecha. Es una decisión propuesta por la IA y
    aceptada.
  - Acepté que el filtro por responsable siga llamando a `list_by_assignee` sin implementar,
    para que CA-36/37 queden en rojo con `NotImplementedError` explícito.
  - Pedí revisar el diff contra cuatro condiciones (ruta sin lógica, 404 desde
    `core/errors.py`, `reset()` reinicia ids, tests intactos) antes de darlo por bueno.

- **Iteraciones:**

  ```text
  Revisa tu diff completo y confírmame punto por punto, corrigiendo lo que no cumpla:
  la ruta no tiene lógica; los 404 salen de core/errors.py; repository.reset() reinicia
  también el contador de ids; no se tocó ningún test. Vuelve a ejecutar pytest -q.
  ```

  → La IA confirmó los cuatro puntos:
  - `tasks/routes.py` no está en el diff y sus rutas son un solo `return service...`.
  - El único 404 de tasks es `errors.not_found("tarea", task_id)`; no hay ningún
    `HTTPException` en `tasks/`.
  - `reset()` pone `_next_id = 1`, y lo confirman CA-01 y CA-42.
  - `git diff -- tests/` sale vacío.

  → Ajuste: ninguno. Se repitió `pytest -q` con el mismo resultado.

- **Validación:**
  - `pytest -q` → 48 verdes y 39 rojos, con los 6 de `users` en verde. Los 39 rojos son reglas
    pendientes:
    - strip y longitud de `title`.
    - `description` > 1000.
    - `priority` estricto y en rango.
    - Fecha pasada y formato `T00:00:00`.
    - Responsable.
    - Idempotencia y longitud de la clave.
    - Filtro por responsable (`NotImplementedError`).
    - CA-43.

    Log: [`logs/06-tests.txt`](logs/06-tests.txt)
  - `ruff check .` → `All checks passed!`. Log: [`logs/06-ruff.txt`](logs/06-ruff.txt)
- **Captura:** N/A
- **Commit:** `feat(tasks): alta y consulta de tareas (happy path)`

## Paso P7 — Incremental 2: validaciones de forma

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Un plan (modo plan) con una herramienta de Pydantic v2 por campo y la previsión de qué
    tests pasarían a verde.
  - `title`: `field_validator`, que recorta con `str.strip()` de Python (A4) y mide la
    longitud 3–120 sobre el valor ya recortado. Se descartó
    `StringConstraints(strip_whitespace=True)` porque recorta en pydantic-core, no con
    `str.strip()`.
  - `priority` y `assignee_id`: `Annotated[int, Field(strict=True, ge=..., le=...)]`, para
    rechazar `3.0`, `"3"` y `true` (decisión 3 y A1). Al ir dentro de `| None`,
    `assignee_id` sigue aceptando `null`.
  - `description`: `Field(default=None, max_length=1000)`, sin recorte ni mínimo.
  - `Idempotency-Key`: `Header(..., min_length=1, max_length=64)` en `tasks/routes.py`, porque
    es una cabecera y no un campo del cuerpo. La ruta sigue sin lógica.

  ```python
  class TaskBase(BaseModel):
      title: str
      description: str | None = Field(default=None, max_length=1000)
      priority: Annotated[int, Field(strict=True, ge=1, le=5)] = 3
      # TODO(CA-17): solo formato YYYY-MM-DD y fecha real (sin hora).
      due_date: date | None = None
      assignee_id: Annotated[int, Field(strict=True, ge=1)] | None = None

      @field_validator("title")
      @classmethod
      def strip_title(cls, value: str) -> str:
          """Recorta con `str.strip()` y mide la longitud ya recortada."""
          title = value.strip()
          if not TITLE_MIN_LENGTH <= len(title) <= TITLE_MAX_LENGTH:
              raise ValueError(...)
          return title
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan antes de que se escribiera código.
  - Acepté la validación de `Idempotency-Key` en `tasks/routes.py`, ya que no se puede
    expresar en `schemas.py`. Es una decisión propuesta por la IA y aceptada.
  - Decidí que `priority` `3.0` dé 422: el contrato dice "int" y aceptar floats ocultaría
    errores del cliente, así que `3.5` y `3.0` deben tratarse igual. Pedí modo estricto solo
    en ese campo y comprobar que un entero normal sigue funcionando y que `true` da 422.
  - `assignee_id` se mantiene estricto por A1. La IA interpretó "solo en ese campo" como "a
    nivel de campo y no de modelo" (decisión propuesta por la IA y aceptada).

- **Iteraciones:**

  ```text
  Decisión: priority 3.0 → 422, porque el contrato dice "int" y aceptar floats ocultaría
  errores del cliente (3.5 y 3.0 deben tratarse igual). Usa modo estricto solo en ese
  campo (p. ej. Field(strict=True) o StrictInt) y comprueba que el envío JSON normal con
  un entero sigue funcionando y que true también da 422. Si no hay un test para 3.0 y
  para true, añádelos en tests/test_tasks.py con el CA de priority. Vuelve a ejecutar
  pytest -q y ruff check .
  ```

  → La IA comprobó que `priority` ya usaba `Field(strict=True)` a nivel de campo, sin
  `ConfigDict(strict=True)` en el modelo. Con peticiones reales: `3` → 201 con `priority`
  `3`; `3.0`, `true` y `3.5` → 422 (`int_type`). CA-14 ya incluía `3.0` y `true`, y los 11
  casos de CA-12/13/14 están en verde.
  → Ajuste: ninguno; no se añadieron tests ni se cambió código.

- **Validación:**
  - `pytest -q` → 73 verdes y 14 rojos, con los 6 de `users` en verde. Los 14 rojos son reglas
    pendientes: fecha pasada (CA-16, 19, 25), `due_date` con `T00:00:00` (CA-17), responsable
    inexistente (CA-21, CA-29 `tras_404`), idempotencia (CA-26, 27, 28), filtro por
    responsable (CA-36, 37 → `NotImplementedError`) y CA-43.
    Log: [`logs/07-tests.txt`](logs/07-tests.txt)
  - `ruff check .` → `All checks passed!`. Log: [`logs/07-ruff.txt`](logs/07-ruff.txt)
- **Captura:** N/A
- **Commit:** `feat(tasks): validación de título, prioridad y descripción`

## Paso P8 — Incremental 3: fecha límite y responsable

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Un plan (modo plan) que respeta el orden de evaluación del contrato: primero la fecha,
    después el hueco de la idempotencia y luego el responsable.
  - Fecha pasada: `data.due_date < clock.today()` lanza
    `errors.invalid_request("la fecha límite no puede ser anterior a hoy (UTC)")`, el texto
    de la decisión 17. Hoy es válido porque la comparación es `<`. Se llama a `clock` a
    través del módulo para que funcione el `monkeypatch`.
  - Responsable: si llega `assignee_id`, se llama a `users_service.get_user(...)`, que ya lanza
    `errors.not_found("usuario", id)`. Se reutiliza en lugar de duplicar la regla.
  - Filtro: `repository.list_by_assignee` con una comprensión de lista sobre `_tasks`, sin
    consultar `users` (decisión 12). Es el único cambio fuera de `service.py`.

  ```python
  if data.due_date is not None and data.due_date < clock.today():
      raise errors.invalid_request(PAST_DUE_DATE_MESSAGE)
  # TODO(CA-26, CA-27, CA-28, CA-30, CA-31, CA-33): si hay clave, buscarla; ...
  if data.assignee_id is not None:
      # get_user lanza errors.not_found("usuario", assignee_id) si no existe.
      users_service.get_user(data.assignee_id)
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan antes de que se escribiera código.
  - Acepté reutilizar `users_service.get_user` en lugar de llamar a `errors.not_found` a mano:
    produce el mismo 404 y respeta la capa `service` de `users`. Es una decisión propuesta
    por la IA y aceptada.
  - Acepté implementar `list_by_assignee` en `tasks/repository.py`, porque el acceso a datos
    vive en el repositorio. Es una decisión propuesta por la IA y aceptada.
  - Pedí verificar las capas, el uso de `core.clock.today()` y que `assignee_id` `None` no
    consulte `users` antes de dar el paso por bueno.

- **Iteraciones:**

  ```text
  Verifica y corrige si hace falta: (1) tasks/ no importa users.repository en ningún
  archivo (muéstrame el grep); (2) la comparación de due_date es entre objetos date
  usando core.clock.today(), sin date.today() ni datetime.now() en tasks/;
  (3) assignee_id None no consulta users. Vuelve a ejecutar pytest -q.
  ```

  → La IA mostró las comprobaciones:
  - (1) El `grep` de `users.repository` en `tasks/` sale vacío; la única importación de
    `users` es `from users import service as users_service`.
  - (2) No hay `date.today`, `datetime.now` ni `utcnow` en `tasks/`. La comparación es
    `date | None` frente a `clock.today() -> date`.
  - (3) Un espía sobre `users_service.get_user` registra 0 llamadas con `assignee_id`
    omitido o `null`, y 1 con `assignee_id` `1`.

  → Ajuste: ninguno. Se repitió `pytest -q` con el mismo resultado.

- **Validación:**
  - `pytest -q` → 82 verdes y 5 rojos, con los 6 de `users` en verde. Los 5 rojos son reglas
    pendientes:
    - Idempotencia: CA-26 y CA-27 (`201 == 200`), CA-28 (`201 == 409`).
    - CA-43, que depende del 409.
    - CA-17 con `2026-10-20T00:00:00`, por el formato estricto de `due_date`.

    Log: [`logs/08-tests.txt`](logs/08-tests.txt)
  - `ruff check .` → `All checks passed!`. Log: [`logs/08-ruff.txt`](logs/08-ruff.txt)
- **Captura:** N/A
- **Commit:** `feat(tasks): reglas de fecha límite y responsable`

## Paso P9 — Incremental 4: idempotencia

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Un diseño en 5 puntos (modo plan):
    1. Huella SHA-256 en `service.py`.
    2. Orden fecha → clave → responsable → alta → guardar la clave.
    3. `create_task` devuelve `(task, código HTTP)`.
    4. 409 con `errors.already_exists`.
    5. `reset()` sin cambios.
  - Tras aprobarse el plan, lo implementó: 86 verdes y 1 rojo (CA-17 `T00:00:00`, fuera del
    paso).
  - `tasks/repository.py`: `find_by_idempotency_key` y `save_idempotency_key` sobre el dict
    `clave -> (huella, tarea)`.
  - `tasks/service.py`: `_fingerprint()` hace un SHA-256 de
    `model_dump(mode="json", include=<5 campos>)` con `sort_keys=True`. La clave se guarda
    solo después de crear la tarea (CA-29).
  - `tasks/routes.py`: parámetro `response: Response` para fijar 201 o 200.

  ```python
  fingerprint = _fingerprint(data)
  if idempotency_key is not None:
      stored = repository.find_by_idempotency_key(idempotency_key)
      if stored is not None:
          stored_fingerprint, stored_task = stored
          if stored_fingerprint != fingerprint:
              raise errors.conflict(
                  f"clave de idempotencia ya existe: {idempotency_key}"
              )
          return stored_task, False
  ...
  if idempotency_key is not None:
      repository.save_idempotency_key(idempotency_key, fingerprint, task)
  return task, True
  ```

- **Qué acepté / rechacé y por qué:**
  - **Aceptado:** la huella SHA-256 del cuerpo validado (`model_dump(mode="json")`, claves
    ordenadas), calculada por el service y solo guardada por el repositorio.
  - **Aceptado:** el orden de evaluación y que la clave se guarde solo tras un 201.
  - **Aceptado:** `reset()` limpia tareas, contador de ids y claves.
  - **Rechazado:** que `create_task` devuelva `(task, código HTTP)`. Debe devolver
    `(task, created: bool)` y la ruta solo asigna `response.status_code` según `created`. La
    decisión vive en el service, pero el service no conoce códigos HTTP.
  - **Rechazado:** el 409 con `errors.already_exists`. No encaja, porque el problema no es que
    la tarea exista sino que la clave se reutilizó con otro cuerpo. Se añade a
    `core/errors.py` la función genérica `conflict(message: str)`, con el estilo de
    `invalid_request`.
  - La IA advirtió que `conflict()` contradice la decisión 11 y la sección "No incluye" de
    `docs/feature-tasks.md`. Mantuvo el texto del contrato
    (`"clave de idempotencia ya existe: <clave>"`). Actualizar la especificación queda
    [PENDIENTE].

- **Iteraciones:**

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

  → La IA cambió dos puntos de su propuesta (los otros dos ya coincidían):
  - (1) **Rechazado:** `(task, código HTTP)` pasa a `(task, created: bool)`. La ruta asigna
    `HTTP_201_CREATED if created else HTTP_200_OK`, sin `raise` ni `HTTPException`.
  - (3) **Rechazado:** `errors.already_exists` pasa a `errors.conflict(...)`, nueva en
    `core/errors.py`.
  - (2) y (4) ya coincidían y no se modificaron.

  → Ajuste: `core/errors.py` (nueva `conflict`), `tasks/service.py` (retorno `bool` y
  `conflict`) y `tasks/routes.py` (asignación según `created`). Prueba manual con la clave
  `K`: 201 → 200 (cuerpo normalizado) → 409 `"clave de idempotencia ya existe: K"`.

- **Validación:**
  - `pytest -q` → 86 verdes y 1 rojo, con los 6 de `users` en verde. CA-26, 27, 28 y 43 pasan
    a verde. Sigue en rojo `test_ca17[2026-10-20T00:00:00]`: Pydantic acepta una fecha con
    hora `00:00:00` y el contrato solo admite `YYYY-MM-DD` (regla de forma pendiente).
    Log: [`logs/09-tests.txt`](logs/09-tests.txt)
  - `ruff check .` → `All checks passed!`. Log: [`logs/09-ruff.txt`](logs/09-ruff.txt)
- **Captura:** N/A
- **Commit:** `feat(tasks): idempotencia con Idempotency-Key`

## Paso P10 — Integración y estilo

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Un plan (modo plan) basado en comprobaciones de solo lectura:
    - pytest daba 86 verdes y 1 rojo (CA-17 `T00:00:00`); ruff limpio y sin avisos.
    - Cobertura de `tasks/` al 100 %.
    - El OpenAPI expone los 3 endpoints con `Task` / `list[Task]`.
    - Capas, catálogo de errores, nombres y orden de rutas conformes con `CLAUDE.md`.
    - `git diff main --stat` sin cambios en `migrations/` ni `legacy/`.
  - Incumplimiento 1 — `tasks/schemas.py:19-20`: `due_date` aceptaba
    `"2026-10-20T00:00:00"`, contra la decisión 4 y la "Definición de hecho" (pytest en verde).
    Se propuso `Field(strict=True)`.
  - Incumplimiento 2 — "Definición de hecho": `README.md` no mencionaba `tasks` y
    `CHANGELOG.md` no existía. Se añaden 3 filas en la tabla de endpoints del README y un
    `CHANGELOG.md` con `[Unreleased]`.
  - Al implementar, `Field(strict=True)` rompió 8 tests: FastAPI valida el cuerpo en modo
    Python y el modo estricto rechaza también `"2026-12-31"`. Se sustituyó por un validador
    `mode="before"` que solo admite `YYYY-MM-DD`; Pydantic comprueba después que la fecha
    exista.
  - Solo se informó, sin cambiarlo:
    - Queda un TODO de CA-01 (`status: str`).
    - `docs/feature-tasks.md` (decisión 11) sigue diciendo `already_exists`.

  ```python
  DATE_ONLY_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

  @field_validator("due_date", mode="before")
  @classmethod
  def require_date_only(cls, value: object) -> object:
      """Solo acepta `YYYY-MM-DD`: sin hora, aunque sea 00:00:00 (CA-17)."""
      if value is None or isinstance(value, date):
          return value
      if not isinstance(value, str) or not DATE_ONLY_PATTERN.fullmatch(value):
          raise ValueError("la fecha límite debe tener el formato YYYY-MM-DD")
      # Pydantic valida después que sea una fecha real (p. ej. rechaza 2026-02-30).
      return value
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan.
  - Se descartó `Field(strict=True)` para `due_date` porque rompía 8 tests: FastAPI pasa el
    cuerpo como `dict` y el modo estricto exige un objeto `date`. Se reemplazó por el
    validador de formato (decisión propuesta por la IA y aceptada).
  - Crear `CHANGELOG.md` y ampliar `README.md` se aceptó para cumplir la "Definición de
    hecho" de `CLAUDE.md`.
  - El TODO de `status` y la contradicción de `docs/feature-tasks.md` con `conflict()` quedan
    sin cambiar: [PENDIENTE].

- **Iteraciones:** ninguna; un único mensaje de trabajo en el paso.

- **Validación:**
  - `pytest -q` → 87 verdes, 0 rojos y sin avisos (`pytest -rw`). Cobertura
    `pytest --cov=tasks --cov-branch` → 100 %.
    Log: [`logs/10-tests-verde.txt`](logs/10-tests-verde.txt)
  - `ruff check .` → `All checks passed!`. Log: [`logs/10-ruff.txt`](logs/10-ruff.txt)
  - Dos `curl -i -X POST /tasks` con `Idempotency-Key: demo-1` y la app levantada → `201 Created`
    y luego `200 OK`, con el mismo `id` (`1`) y el mismo `created_at`. La app se detuvo al
    terminar. Log: [`logs/10-curl.txt`](logs/10-curl.txt)
  - `git diff main --stat -- migrations legacy` → vacío.
- **Captura:**
  - ![Swagger con los endpoints de tasks](capturas/P10-swagger.png)
  - ![Respuestas 201 y 200 de los curl](capturas/P10-curl.png)
- **Commit:** `chore(tasks): integración y linting`

## Paso P11 — Configuración de cobertura y mutación

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - `[tool.coverage.run]` con `branch = true`, `source = ["core", "users", "tasks", "main"]`
    (`main` se resuelve como módulo importable, equivalente a `main.py`) y `omit` de
    `tests/*`, `legacy/*` y `migrations/*`.
  - `[tool.coverage.report]` con `show_missing = true` y `fail_under = 90`.
  - `mutmut>=3.8` en `requirements.txt`; versión instalada 3.8.0.
  - Al revisar el código de mutmut 3.8.0 instalado, la IA vio que `paths_to_mutate` y
    `tests_dir` (previstos en su plan inicial) están deprecados: usó `source_paths`, que
    admite un archivo suelto (`core/clock.py`), y `also_copy` para `core/`, `users/` y
    `main.py` (`tests/` y `pyproject.toml` se copian por defecto).
  - `.gitignore`: añadidos `mutants/` y `.mutmut-cache`; `htmlcov/` y `.coverage` ya estaban.

  ```toml
  [tool.coverage.run]
  branch = true
  source = ["core", "users", "tasks", "main"]
  omit = ["tests/*", "legacy/*", "migrations/*"]

  [tool.coverage.report]
  show_missing = true
  fail_under = 90

  [tool.mutmut]
  source_paths = ["tasks/", "core/clock.py"]
  also_copy = ["core/", "users/", "main.py"]
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan. El cambio de `paths_to_mutate`/`tests_dir` a `source_paths` se aceptó
    porque el prompt pedía usar la sintaxis de la versión instalada (3.8.0).
  - Las líneas sin cubrir (`core/clock.py:16`, cuerpo de `today()`, mockeado en los tests;
    `main.py:18`, `/health` sin test) quedan anotadas como línea base, sin cambios en este
    paso: los mutantes de `today()` sobrevivirán en `mutmut run`. [PENDIENTE] decidir si se
    cubren.

- **Iteraciones:** ninguna; un único mensaje de trabajo en el paso.

- **Validación:**
  - `pytest --cov --cov-branch --cov-report=term-missing` → 87 passed, cobertura total
    99,10 % (umbral 90 % alcanzado); `tasks/` y `users/` al 100 %, `core/clock.py` 80 %
    (falta línea 16), `main.py` 89 % (falta línea 18).
    Log: [`logs/11-cobertura-antes.txt`](logs/11-cobertura-antes.txt)
  - `mutmut --version` → `mutmut, version 3.8.0`.
    Log: [`logs/11-mutmut-version.txt`](logs/11-mutmut-version.txt)
  - `ruff check .` → `All checks passed!` (ejecutado en el paso, sin log guardado).
- **Captura:** N/A
- **Commit:** `chore: configuración de cobertura de ramas y mutmut`

## Paso P12 — Tests unitarios del service

- **Prompt usado:**

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

- **Qué propuso la IA:**
  - Nuevo `tests/test_tasks_service.py` con 19 tests (22 casos con la parametrización), sin
    tocar código de producción.
  - Dos fixtures autouse con `monkeypatch`: `core.clock.today` fijado en 2026-10-20 y un
    fake de `users.service.get_user` que registra los ids consultados y levanta
    `errors.not_found("usuario", id)` fuera de los ids 1–4. El repositorio en memoria es real.
  - Aserciones exactas de `status_code` y `detail` (`PAST_DUE_DATE_MESSAGE`,
    `"usuario no encontrado: 999"`, `"clave de idempotencia ya existe: <clave>"`,
    `"tarea no encontrado: 999"`).
  - Refuerzos por la pregunta de control: 409 cambiando un solo campo de la huella
    (parametrizado: description `""` frente a None, priority, due_date, assignee_id),
    un 404 previo que no reserva la clave (CA-29), filtro con coincidencias y listado sin filtro.
  - Mutantes equivalentes previstos: `sort_keys` y `ensure_ascii` de `json.dumps` en `_fingerprint`.

  ```python
  @pytest.mark.parametrize(
      "changed_field",
      [
          {"description": ""},
          {"priority": 4},
          {"due_date": TODAY + timedelta(days=1)},
          {"assignee_id": 2},
      ],
      ids=["description_vacia_frente_a_none", "priority", "due_date", "assignee_id"],
  )
  def test_misma_clave_cambiando_un_solo_campo_da_409(changed_field: dict) -> None:
      # Arrange
      original, _ = service.create_task(TaskCreate(title="Revisar backups"), idempotency_key=KEY)
      other = TaskCreate(title="Revisar backups", **changed_field)

      # Act
      with pytest.raises(HTTPException) as error:
          service.create_task(other, idempotency_key=KEY)

      # Assert
      assert error.value.status_code == 409
      assert error.value.detail == f"clave de idempotencia ya existe: {KEY}"
      assert tasks_repository.list_all() == [original]
  ```

- **Qué acepté / rechacé y por qué:**
  - Aprobé el plan.
  - **Decisión (caso 5):** el prompt planteaba qué hacer con `description` None frente a
    omitida y pedía preguntar si no estaba en la especificación. La IA no preguntó: lo
    resolvió con `docs/feature-tasks.md` (decisión 2, omitida y null son equivalentes;
    decisión 8, la huella usa el cuerpo normalizado). Comportamiento esperado: misma huella.
    Mi respuesta lo fijó como decisión: son el mismo cuerpo; con la misma clave se
    devuelve la misma tarea, con `created False` y sin 409. El test se deja así. Yo cité
    las decisiones 3 y 7; la IA señaló que en la especificación corresponden a la 2 y la 8,
    y el comentario del test cita la 2.
  - Exigí que ningún test mockeara la lógica bajo prueba y que hubiera más líneas de
    aserción que de mock, con el recuento y refuerzo de los que no cumplieran: aceptado.

- **Iteraciones:**

  ```text
  Caso 5: description omitida y description None son el mismo cuerpo (decisión 3 y 7 de la
  especificación): misma clave → misma tarea, created False, sin 409. Deja el test así.
  Revisa además que ningún test mockea la lógica bajo prueba y que hay más líneas de
  aserción que de mock; dame el recuento (líneas de mock / líneas de assert) y refuerza
  los que no cumplan. Vuelve a ejecutar pytest -q.
  ```

  → La IA confirmó que solo hay dos `monkeypatch.setattr`, ambos sobre dependencias
  (`core.clock.today`, `users.service.get_user`). Contó por test líneas de mock (los 2
  `setattr` autouse más las que manipulan el fake) frente a sentencias `assert`: antes
  39/45 en total, con 12 de 19 tests sin cumplir.
  → Ajuste: se reforzaron los 12 con aserciones que comprueban algo nuevo (contenido exacto
  del almacén, `created`, títulos y responsables del listado, una tarea previa en el 404 de
  `get_task`) y se quitó `user_lookups.clear()` del test de filtro sin coincidencias. Después:
  38/61 en total, los 19 tests con más asserts que mocks.

- **Validación:**
  - `pytest -q` → 109 tests en verde (87 previos + 22 nuevos), código de salida 0.
    Log: [`logs/12-tests.txt`](logs/12-tests.txt)
  - `ruff check .` → `All checks passed!`. Log: [`logs/12-ruff.txt`](logs/12-ruff.txt)
  - `pytest tests/test_tasks_service.py --cov=tasks --cov-branch` (ejecutado en el paso,
    sin log guardado) → `tasks/service.py` al 100 % solo con los unitarios.
- **Captura:** N/A
- **Commit:** `test(tasks): unitarios del service con reloj y usuarios mockeados`
