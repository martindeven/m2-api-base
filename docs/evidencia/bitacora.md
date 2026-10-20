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
