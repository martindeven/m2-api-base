# Feature: recurso `tasks` — registro de tareas de equipo

## Historia de usuario

Como **miembro del equipo de operaciones** quiero **registrar tareas con responsable,
prioridad y fecha límite** para que **ningún trabajo quede sin registrar y se pueda rastrear**.

## Objetivo

Añadir a la API un recurso `tasks` que permita crear, listar y consultar tareas, con
validaciones de dominio (título, prioridad, fecha límite, responsable existente) y creación
idempotente opcional mediante la cabecera `Idempotency-Key`, siguiendo el patrón de capas
del proyecto (`routes` → `service` → `repository`, errores desde `core/errors.py`).

## Alcance

### Incluye

- `POST /tasks` — crear una tarea, con idempotencia opcional (`Idempotency-Key`).
- `GET /tasks` — listar tareas por `id` ascendente, con filtro opcional `?assignee_id=<id>`.
- `GET /tasks/{task_id}` — consultar una tarea.
- Validación de `title`, `description`, `priority`, `due_date`, `assignee_id` e `Idempotency-Key`.
- Comprobación de que `assignee_id` existe en `users`.
- `core/clock.py` con la función que da la fecha actual en UTC (sustituible en los tests).
- Almacén en memoria de tareas y de claves de idempotencia, con `reset()` para aislar los tests.
- Tests en `tests/test_tasks.py` (caso feliz y de error por endpoint).

### No incluye

- Modificar, completar o borrar tareas (`PUT` / `PATCH` / `DELETE`).
- Valores de `status` distintos de `"pending"`.
- Paginación, ordenación configurable o filtros distintos de `assignee_id`.
- Caducidad de las claves de idempotencia.
- Autenticación / autorización.
- Persistencia en base de datos.
- Nuevas funciones en `core/errors.py`.
- Cambios en `migrations/` o `legacy/`.

## Contrato de la API

### Modelo `Task` (respuesta)

| Campo         | Tipo                     | Notas                                                    |
|---------------|--------------------------|----------------------------------------------------------|
| `id`          | int                      | Asignado por el servidor; empieza en 1 (almacén vacío).  |
| `title`       | str                      | Ya recortado (`strip`).                                  |
| `description` | str \| null              | Tal como se recibió (sin recortar).                      |
| `priority`    | int (1–5)                | `3` si no se envía.                                      |
| `due_date`    | str `YYYY-MM-DD` \| null |                                                          |
| `assignee_id` | int \| null              | Id de un usuario existente.                              |
| `status`      | str                      | Siempre `"pending"` en este sprint.                      |
| `created_at`  | datetime ISO 8601 (UTC)  | Asignado por el servidor.                                |

### `POST /tasks`

**Cabeceras**

| Cabecera          | Obligatoria | Regla                                                                   |
|-------------------|-------------|-------------------------------------------------------------------------|
| `Idempotency-Key` | No          | 1–64 caracteres (`len()`), sin `strip`, sensible a mayúsculas.          |

**Cuerpo (JSON)**

| Campo         | Tipo             | Obligatorio | Regla                                                                          |
|---------------|------------------|-------------|--------------------------------------------------------------------------------|
| `title`       | str              | Sí          | Se recorta (`strip`); tras recortar, 3–120 caracteres (inclusivo).             |
| `description` | str \| null      | No          | Máximo 1000 caracteres sobre el valor recibido. Sin mínimo; `""` es válido.    |
| `priority`    | int estricto     | No          | 1–5. Por defecto `3`. No se aceptan `3.0`, `"3"`, `true` ni `null`.            |
| `due_date`    | str \| null      | No          | Solo `YYYY-MM-DD` y fecha real. No anterior a hoy (UTC del servidor).          |
| `assignee_id` | int estricto \| null | No      | ≥ 1 y existente en `users`.                                                    |

Campos desconocidos o que asigna el servidor (`id`, `status`, `created_at`, …): se ignoran,
como en `users`. El servidor siempre pone sus propios valores.

**Orden de evaluación**

1. Forma del cuerpo y de la cabecera → `422` (Pydantic, formato por defecto).
2. `due_date` anterior a hoy → `422` (dominio, `errors.invalid_request`).
3. Búsqueda de la `Idempotency-Key` → `200` (misma huella) o `409` (huella distinta).
4. Existencia del responsable → `404` (`errors.not_found`).
5. Creación → `201`; si hay clave, se guarda junto con la huella y la tarea.

**Respuestas**

| Código | Cuándo                                                       | Cuerpo                                     |
|--------|--------------------------------------------------------------|--------------------------------------------|
| 201    | Tarea creada.                                                | `Task`                                     |
| 200    | Misma `Idempotency-Key` y misma huella del cuerpo.           | La **misma** `Task` (mismo `id` y `created_at`) |
| 404    | `assignee_id` ≥ 1 que no existe en `users`.                  | `{"detail": "usuario no encontrado: <id>"}` |
| 409    | Misma `Idempotency-Key` con huella distinta.                 | `{"detail": "clave de idempotencia ya existe: <clave>"}` |
| 422    | Forma inválida del cuerpo o de la cabecera.                  | `{"detail": [ ... ]}` (lista de Pydantic)  |
| 422    | `due_date` anterior a hoy (UTC).                             | `{"detail": "<mensaje en español>"}` (texto) |

### `GET /tasks`

| Parámetro     | Tipo | Obligatorio | Regla                                                                  |
|---------------|------|-------------|------------------------------------------------------------------------|
| `assignee_id` | int  | No          | Filtro: solo tareas con ese responsable. Si no hay ninguna, `[]`.      |

| Código | Cuándo                         | Cuerpo                              |
|--------|--------------------------------|-------------------------------------|
| 200    | Query válida (incluye `0`, negativos e ids inexistentes) | `list[Task]` ordenada por `id` |
| 422    | `assignee_id` no es entero     | `{"detail": [ ... ]}`               |

### `GET /tasks/{task_id}`

| Código | Cuándo                                         | Cuerpo                                   |
|--------|------------------------------------------------|------------------------------------------|
| 200    | La tarea existe.                               | `Task`                                   |
| 404    | Entero sin tarea (incluye `0` y negativos).    | `{"detail": "tarea no encontrado: <id>"}` |
| 422    | `task_id` no es entero.                        | `{"detail": [ ... ]}`                    |

Los errores de dominio (404, 409 y 422 por fecha) llevan `detail` de texto en español,
generado con `core/errors.py`. Los 422 de forma usan el formato por defecto de Pydantic.

## Decisiones

Decisiones del responsable de producto sobre las preguntas abiertas del ticket.

1. **`title`**
   - Los límites 3 y 120 son inclusivos y se miden tras el `strip`.
   - Un título solo de espacios da 422, porque queda con longitud 0.
   - El mensaje es el de Pydantic por defecto, igual que en `users`; no hay mensaje propio en español para los errores de forma.
   - Un `title` que no es texto (número, `null`) da 422.
2. **`description`**
   - No se recorta; se guarda tal cual.
   - `""` es válido y se guarda como `""`.
   - Omitida y `null` son equivalentes: se guarda `null`.
   - El máximo de 1000 se cuenta sobre el valor recibido.
   - No tiene longitud mínima.
3. **`priority`**
   - Es un entero estricto: `3.0`, `3.5`, `"3"`, `"alta"`, `true` y `null` dan 422.
   - Si se omite, vale 3.
   - El rango es 1–5; `0` o `6` dan 422.
4. **`due_date`**
   - Solo se acepta `YYYY-MM-DD`. Una fecha con hora da 422, y una fecha inexistente (`2026-02-30`) también.
   - "Hoy" es la fecha UTC del servidor al recibir la petición, calculada con una función de `core/clock.py`, aunque el cliente esté en otra zona horaria.
   - Hoy es válido; ayer da 422.
   - No hay fecha máxima.
   - Omitida y `null` son equivalentes: se guarda `null`.
5. **`assignee_id`**
   - `0` o negativo da 422, porque es un error de forma y no de existencia.
   - Un entero ≥ 1 que no existe en `users` da 404, con `errors.not_found`.
   - `null` explícito equivale a omitido: la tarea queda sin responsable.
6. **Varios errores a la vez**
   - El orden de evaluación es el de la sección *Orden de evaluación*.
   - Título corto + responsable inexistente → 422.
   - Fecha pasada + responsable inexistente → 422.
7. **Campos desconocidos o que asigna el servidor**
   - Se tratan igual que en `users`, con el comportamiento por defecto de Pydantic: se ignoran.
   - El servidor siempre pone sus propios valores.
8. **Idempotencia, "mismo cuerpo"**
   - La huella se calcula sobre el cuerpo ya validado y normalizado (tras el `strip` y los valores por defecto).
   - El orden de las claves no importa.
   - `{"title":"x"}` y `{"title":"x","priority":3}` son el mismo cuerpo, y también `" Revisar "` y `"Revisar"`.
9. **Idempotencia cuando la primera petición falla**
   - La clave solo se guarda tras un 201. Si la primera petición con la clave K da 422 o 404, la clave no se guarda.
   - Una petición válida posterior con K crea la tarea (201).
   - Un cuerpo inválido con una clave ya usada da 422, no 200 ni 409.
10. **Idempotencia, alcance y duración**
    - La clave es global, porque no hay usuarios autenticados, y no caduca.
    - Se guarda en memoria y `reset()` la limpia.
    - No tiene restricción de caracteres ni se recorta.
    - Distingue mayúsculas: `"abc"` y `"ABC"` son claves distintas.
    - Admite de 1 a 64 caracteres, contados con `len()` y no en bytes. Vacía o más larga da 422.
11. **Idempotencia, respuesta repetida**
    - Misma clave y misma huella → 200 con la misma `Task`, idéntica a la original (mismo `id` y `created_at`). No se crea una tarea nueva.
    - Misma clave y huella distinta → 409, usando la función de conflicto del catálogo: `errors.already_exists("clave de idempotencia", <clave>)`.
    - No se añaden funciones nuevas a `core/errors.py`.
12. **`GET /tasks?assignee_id=X` con un usuario inexistente**
    - Devuelve 200 con lista vacía, porque es un filtro y no una consulta del usuario.
    - Vale también para `0` y negativos.
    - Solo un valor no entero da 422.
13. **Orden del listado:** por `id` ascendente.
14. **Datos semilla**
    - El almacén de tareas arranca vacío.
    - `reset()` vacía las tareas y las claves de idempotencia.
    - `GET /tasks` sin tareas → 200 con `[]`.
15. **`GET /tasks/{task_id}` con `task_id` ≤ 0:** da 404, porque es un entero que no corresponde a ninguna tarea. Solo un valor no entero da 422.
16. **`status` y `created_at`**
    - `status` solo puede ser `"pending"` en este sprint.
    - `created_at` va en UTC y en formato ISO 8601.
17. **422 por fecha pasada**
    - Se valida en el service.
    - Su `detail` sale de `errors.invalid_request(...)`, con el texto en español "la fecha límite no puede ser anterior a hoy (UTC)".
    - Los demás 422 de forma usan el formato por defecto de Pydantic.

### Decisiones propuestas por la IA y aceptadas

Casos que las decisiones anteriores no cubren. Se aplica la opción más conservadora y
coherente con ellas.

- **A1 — `assignee_id` es un entero estricto, como `priority`.** `"1"`, `1.0` y `true` dan 422.
- **A2 — Repetición con una fecha que ya ha pasado.** Por el orden de evaluación, la fecha se comprueba antes que la clave. Si se repite una petición idempotente y entre medias cambia el día en UTC, de modo que `due_date` ya es pasada, la respuesta es 422 y no 200.
- **A3 — El 404 de la tarea usa el catálogo sin cambios.** `errors.not_found("tarea", id)` produce "tarea no encontrado: <id>". El catálogo concuerda en masculino y no se modifica, igual que en el punto 11. Los tests comprueban el fragmento `"no encontrado"`, como en `users`.
- **A4 — El `strip` de `title` es `str.strip()` de Python.** Elimina cualquier espacio en blanco Unicode de los extremos.
- **A5 — La huella del cuerpo no incluye la `Idempotency-Key` ni los campos ignorados.** Solo cuentan `title`, `description`, `priority`, `due_date` y `assignee_id`, ya normalizados.

## Criterios de aceptación

Mientras no se diga lo contrario, cada criterio parte del almacén de tareas vacío y de los
4 usuarios semilla (ids 1–4). En los criterios con fecha, la función de `core/clock.py` está
fijada para devolver `2026-10-20` como fecha actual en UTC.

### Creación

- **CA-01 — Creación mínima.**
  - **Dado** el cuerpo `{"title": "Revisar backups"}`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `201` con `id` `1`, `status` `"pending"`, `priority` `3`, y `description`, `due_date` y `assignee_id` a `null`.
  - **Y** `created_at` es una fecha-hora ISO 8601 con zona UTC.
- **CA-02 — Creación completa.**
  - **Dado** el cuerpo `{"title": "Rotar certificados", "description": "Servidores web", "priority": 5, "due_date": "2026-12-31", "assignee_id": 2}`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `201` y la tarea devuelta tiene exactamente esos valores.
- **CA-03 — El servidor ignora los campos que asigna él y los desconocidos.**
  - **Dado** el cuerpo `{"title": "Tarea x", "id": 99, "status": "done", "created_at": "2000-01-01T00:00:00Z", "foo": 1}`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `201` con `id` `1`, `status` `"pending"` y un `created_at` distinto del enviado.
  - **Y** el cuerpo de la respuesta no contiene `foo`.

### `title`

- **CA-04 — Se recorta.**
  - **Dado** `title` `"  Revisar backups  "`.
  - **Cuando** creo la tarea.
  - **Entonces** recibo `201` y la tarea tiene `title` `"Revisar backups"`.
- **CA-05 — Los límites son inclusivos tras el recorte.**
  - **Dado** cada uno de estos `title`: `"abc"`, `"  abc  "` y `"a"` × 120.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `201`.
- **CA-06 — Demasiado corto o vacío.**
  - **Dado** cada uno de estos `title`: `"ab"`, `"  ab  "`, `"   "` y `""`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.
- **CA-07 — Demasiado largo.**
  - **Dado** `title` `"a"` × 121, o `"a"` × 121 con espacios a los lados.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.
- **CA-08 — Ausente o no es texto.**
  - **Dado** un cuerpo sin `title`, o con `title` `123` o `null`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.

### `description`

- **CA-09 — Se guarda tal cual.**
  - **Dado** `description` `"  con espacios  "`, o `""`.
  - **Cuando** creo la tarea.
  - **Entonces** recibo `201` y `description` es exactamente el valor enviado.
- **CA-10 — Omitida o `null`.**
  - **Dado** un cuerpo sin `description`, o con `description` `null`.
  - **Cuando** creo la tarea.
  - **Entonces** recibo `201` con `description` `null`.
- **CA-11 — Límite de 1000 sobre el valor recibido.**
  - **Dado** `description` `"a"` × 1000.
  - **Entonces** recibo `201`.
  - **Dado** `description` `"a"` × 1001, o `"a"` × 999 con un espacio delante y otro detrás (1001 en total).
  - **Entonces** recibo `422`.

### `priority`

- **CA-12 — Valor por defecto y límites.**
  - **Dado** un cuerpo sin `priority`, la tarea creada tiene `priority` `3`.
  - **Dado** `priority` `1` o `5`, recibo `201` con ese valor.
- **CA-13 — Fuera de rango.**
  - **Dado** `priority` `0` o `6`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.
- **CA-14 — No es un entero estricto.**
  - **Dado** cada uno de estos `priority`: `3.0`, `3.5`, `"3"`, `"alta"`, `true` y `null`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.

### `due_date` (hoy fijado en `2026-10-20`)

- **CA-15 — Hoy o futura.**
  - **Dado** `due_date` `"2026-10-20"` o `"2030-01-01"`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `201` con ese `due_date`.
- **CA-16 — Pasada.**
  - **Dado** `due_date` `"2026-10-19"`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422` con un `detail` de texto en español.
- **CA-17 — Formato o fecha inválidos.**
  - **Dado** cada uno de estos `due_date`: `"20/10/2026"`, `"2026-10-20T10:00:00"`, `"2026-10-20T00:00:00"` y `"2026-02-30"`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.
- **CA-18 — Omitida o `null`.**
  - **Dado** un cuerpo sin `due_date`, o con `due_date` `null`.
  - **Cuando** creo la tarea.
  - **Entonces** recibo `201` con `due_date` `null`.
- **CA-19 — La referencia es el reloj del servidor.**
  - **Dado** que `core/clock.py` está fijado en `2026-10-21`.
  - **Cuando** hago `POST /tasks` con `due_date` `"2026-10-20"`.
  - **Entonces** recibo `422`.

### `assignee_id`

- **CA-20 — Responsable existente.**
  - **Dado** `assignee_id` `1`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `201` con `assignee_id` `1`.
- **CA-21 — Responsable inexistente.**
  - **Dado** `assignee_id` `999`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `404`, y `detail` es un texto que contiene `"no encontrado"`.
- **CA-22 — Forma inválida.**
  - **Dado** cada uno de estos `assignee_id`: `0`, `-1`, `"1"`, `1.0` y `true`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.
- **CA-23 — `null` explícito.**
  - **Dado** `assignee_id` `null`.
  - **Cuando** creo la tarea.
  - **Entonces** recibo `201` con `assignee_id` `null`.

### Varios errores a la vez

- **CA-24 — La forma gana al 404.**
  - **Dado** `title` `"ab"` y `assignee_id` `999`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.
- **CA-25 — La fecha pasada gana al 404.**
  - **Dado** `due_date` `"2026-10-19"` y `assignee_id` `999`.
  - **Cuando** hago `POST /tasks`.
  - **Entonces** recibo `422`.

### Idempotencia

- **CA-26 — Repetición idéntica.**
  - **Dado** un `POST /tasks` con `Idempotency-Key: K` que devolvió `201`.
  - **Cuando** repito el mismo `POST` con la misma clave y el mismo cuerpo.
  - **Entonces** recibo `200` con un cuerpo idéntico al original (mismo `id` y `created_at`).
  - **Y** `GET /tasks` devuelve una sola tarea.
- **CA-27 — Huella normalizada.**
  - **Dado** un `POST` con `K` y `{"title": "Revisar"}` que devolvió `201`.
  - **Cuando** hago `POST` con `K` y `{"priority": 3, "title": " Revisar "}`.
  - **Entonces** recibo `200` con la misma tarea.
- **CA-28 — Huella distinta.**
  - **Dado** un `POST` con `K` y `{"title": "Revisar"}` que devolvió `201`.
  - **Cuando** hago `POST` con `K` y `{"title": "Otra tarea"}`.
  - **Entonces** recibo `409`, y `detail` es un texto que contiene `"ya existe"`.
  - **Y** `GET /tasks` devuelve una sola tarea.
- **CA-29 — Un fallo no guarda la clave.**
  - **Dado** un `POST` con `K` y `assignee_id` `999` que devolvió `404`, o con `title` `"ab"` que devolvió `422`.
  - **Cuando** hago `POST` con `K` y un cuerpo válido.
  - **Entonces** recibo `201`.
- **CA-30 — Cuerpo inválido con clave usada.**
  - **Dado** un `POST` con `K` que devolvió `201`.
  - **Cuando** hago `POST` con `K` y `title` `"ab"`.
  - **Entonces** recibo `422`, no `200` ni `409`.
- **CA-31 — Distingue mayúsculas.**
  - **Dado** un `POST` con `Idempotency-Key: abc` que devolvió `201`.
  - **Cuando** hago el mismo `POST` con `Idempotency-Key: ABC`.
  - **Entonces** recibo `201` con otro `id`.
- **CA-32 — Longitud de la clave.**
  - **Dada** una clave de 1 o de 64 caracteres, recibo `201`.
  - **Dada** una clave vacía o de 65 caracteres, recibo `422`.
- **CA-33 — Sin clave no hay deduplicación.**
  - **Dado** un cuerpo válido sin `Idempotency-Key`.
  - **Cuando** hago dos `POST /tasks` iguales.
  - **Entonces** recibo `201` las dos veces, con `id` `1` y `2`.

### Listado y consulta

- **CA-34 — Listado vacío.**
  - **Dado** el almacén de tareas vacío.
  - **Cuando** hago `GET /tasks`.
  - **Entonces** recibo `200` con `[]`.
- **CA-35 — Listado completo y ordenado.**
  - **Dadas** tres tareas creadas.
  - **Cuando** hago `GET /tasks`.
  - **Entonces** recibo `200` con las tres, con `id` `[1, 2, 3]` en ese orden.
- **CA-36 — Filtro por responsable.**
  - **Dadas** tareas con `assignee_id` `1`, `2`, `1` y una sin responsable.
  - **Cuando** hago `GET /tasks?assignee_id=1`.
  - **Entonces** recibo `200` solo con las dos tareas de `1`, en orden de `id`.
- **CA-37 — Filtro sin coincidencias.**
  - **Dadas** tareas creadas.
  - **Cuando** hago `GET /tasks?assignee_id=X` con `X` en `999`, `0` o `-1`.
  - **Entonces** recibo `200` con `[]`.
- **CA-38 — Filtro no entero.**
  - **Cuando** hago `GET /tasks?assignee_id=abc`.
  - **Entonces** recibo `422`.
- **CA-39 — Consultar tarea existente.**
  - **Dada** una tarea creada.
  - **Cuando** hago `GET /tasks/{id}` con su `id`.
  - **Entonces** recibo `200` con un cuerpo igual al devuelto al crearla.
- **CA-40 — Consultar tarea inexistente.**
  - **Cuando** hago `GET /tasks/999`, `GET /tasks/0` o `GET /tasks/-1`.
  - **Entonces** recibo `404`, y `detail` es un texto que contiene `"no encontrado"`.
- **CA-41 — `task_id` no entero.**
  - **Cuando** hago `GET /tasks/abc`.
  - **Entonces** recibo `422`.

### Aislamiento y errores

- **CA-42 — `reset()` limpia tareas y claves.**
  - **Dada** una tarea creada con `Idempotency-Key: K`.
  - **Cuando** se llama a `reset()` del repositorio de tareas.
  - **Entonces** `GET /tasks` devuelve `[]`.
  - **Y** un `POST` con `K` y un cuerpo distinto devuelve `201`.
- **CA-43 — Formato de los errores de dominio.**
  - **Dados** los errores de CA-16 (fecha pasada), CA-21 (responsable), CA-28 (conflicto) y CA-40 (tarea).
  - **Entonces** su `detail` es un `str` en español.
  - **Y** en los 422 de forma (p. ej. CA-06), `detail` es una lista (formato de Pydantic).

## Ejemplos de uso

Crear una tarea:

    curl -i -X POST http://127.0.0.1:8000/tasks \
      -H "Content-Type: application/json" \
      -d '{"title": "  Revisar backups  ", "priority": 2, "due_date": "2026-12-31", "assignee_id": 1}'

Crear con clave de idempotencia (repetir el mismo comando devuelve `200` y la misma tarea):

    curl -i -X POST http://127.0.0.1:8000/tasks \
      -H "Content-Type: application/json" \
      -H "Idempotency-Key: alta-backup-001" \
      -d '{"title": "Rotar certificados", "assignee_id": 2}'

Misma clave, cuerpo distinto (`409`):

    curl -i -X POST http://127.0.0.1:8000/tasks \
      -H "Content-Type: application/json" \
      -H "Idempotency-Key: alta-backup-001" \
      -d '{"title": "Otra tarea distinta"}'

Responsable inexistente (`404`):

    curl -i -X POST http://127.0.0.1:8000/tasks \
      -H "Content-Type: application/json" \
      -d '{"title": "Tarea huérfana", "assignee_id": 999}'

Fecha límite pasada (`422` con mensaje de dominio):

    curl -i -X POST http://127.0.0.1:8000/tasks \
      -H "Content-Type: application/json" \
      -d '{"title": "Tarea atrasada", "due_date": "2020-01-01"}'

Listar todas / filtrar por responsable:

    curl -i http://127.0.0.1:8000/tasks
    curl -i "http://127.0.0.1:8000/tasks?assignee_id=1"

Consultar una tarea:

    curl -i http://127.0.0.1:8000/tasks/1
