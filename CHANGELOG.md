# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto
usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

## [0.2.0] - 2026-10-21

### Added

- Recurso `tasks` para registrar tareas de equipo con responsable, prioridad y fecha límite.
  Especificación y criterios de aceptación en `docs/feature-tasks.md`. Endpoints:
  - `POST /tasks`: crea una tarea con `status` `"pending"`.
  - `GET /tasks`: lista por `id` ascendente, con filtro opcional `?assignee_id=`.
  - `GET /tasks/{task_id}`: consulta una tarea.
- Validaciones de forma (422 con el formato de Pydantic):
  - `title`: se recorta y, después de recortarlo, debe tener entre 3 y 120 caracteres.
  - `description`: 1000 caracteres como máximo.
  - `priority`: entero estricto entre 1 y 5; si no se envía, vale 3.
  - `due_date`: solo `YYYY-MM-DD`.
  - `assignee_id`: entero estricto, ≥ 1.
- Reglas de dominio:
  - `due_date` no puede ser anterior a hoy en UTC (422 con mensaje de texto).
  - `assignee_id` debe ser un usuario existente (404).
- Alta idempotente opcional con la cabecera `Idempotency-Key`. Si se repite la misma clave
  con el mismo cuerpo normalizado, devuelve 200 con la tarea original; con otro cuerpo
  devuelve 409. La clave solo se guarda cuando la tarea se crea.
- `core/clock.py` con `now()` y `today()` en UTC. Es el único punto que consulta la fecha
  del sistema y se puede sustituir en los tests.
- Tests de `tasks`:
  - uno por criterio de aceptación (CA-01 a CA-43);
  - unitarios del service, con el reloj y los usuarios simulados;
  - un flujo de integración entre `users` y `tasks`;
  - tests de regresión.
- Cobertura de ramas con umbral `fail_under = 90` y mutation testing con mutmut, ambos
  configurados en `pyproject.toml`.
- Docstrings estilo Google en `tasks/service.py`, `tasks/repository.py` y `core/clock.py`.
- Documentación OpenAPI de `tasks` en `/docs`:
  - `summary`, `description` y `responses=` con los códigos 200, 201, 404, 409 y 422;
  - descripciones y ejemplos de los campos;
  - documentación de la cabecera `Idempotency-Key`.
- ADR [`docs/adr/0001-idempotencia-en-alta-de-tareas.md`](docs/adr/0001-idempotencia-en-alta-de-tareas.md).

### Changed

- `CLAUDE.md` incluye las convenciones del recurso `tasks`:
  - el reloj de `core/clock.py`;
  - validaciones de forma en los schemas y reglas de dominio en el service;
  - los recursos se consultan entre sí a través de su `service.py`;
  - `reset()` en la fixture de los tests;
  - la definición de hecho.
- `create_task` se divide en funciones de dominio con nombre, y los límites de validación
  pasan a ser constantes con nombre.
- El 409 de idempotencia usa `errors.already_exists` del catálogo de errores.
- `users` toma `created_at` de `core/clock.py` en lugar de `datetime.now()`.
- Los tests de `tasks` se concentran en un único archivo, `tests/test_tasks.py`, como pide la
  convención de un archivo por recurso.
- `README.md` reescrito para el onboarding:
  - endpoints con sus códigos de respuesta;
  - ejemplos `curl` de `tasks`;
  - tests y calidad;
  - una guía para colaboradores.
- Versión 0.2.0 en `pyproject.toml` y en la app FastAPI.

### Fixed

- Dos peticiones simultáneas con la misma `Idempotency-Key` ya no crean dos tareas: la
  búsqueda de la clave, la creación y el guardado son atómicos.
- Una `due_date` con hora, aunque sea `T00:00:00`, se rechaza con 422.
- La longitud de `Idempotency-Key` se cuenta en caracteres y no en bytes: una clave de 64
  caracteres no ASCII se acepta.
- Los 422 de forma de `title` y `due_date` usan el mensaje de Pydantic por defecto en lugar de
  un texto propio.

## [0.1.0] - 2026-09-16

### Added

- API REST de usuarios con FastAPI y Pydantic v2, con almacén en memoria y 4 usuarios semilla:
  - `GET /health`;
  - `GET /users`;
  - `GET /users/{id}`;
  - `POST /users` (409 si el email ya existe).
- Catálogo de errores en `core/errors.py` (`not_found`, `invalid_request`, `already_exists`).
- Tests de `users`, linter `ruff` y convenciones en `CLAUDE.md`.
- `README.md` con instalación, uso y la tabla de ramas del módulo.

### Fixed

- `core/errors.py` usa `HTTP_422_UNPROCESSABLE_CONTENT`, el nombre que no está deprecado.
