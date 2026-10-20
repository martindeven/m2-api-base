# Changelog

## [Unreleased]

### Added

- Recurso `tasks`: `POST /tasks`, `GET /tasks` (filtro `?assignee_id=`) y `GET /tasks/{task_id}`,
  según `docs/feature-tasks.md`.
- Validaciones de forma de `title`, `description`, `priority`, `due_date` y `assignee_id`, y
  reglas de dominio de fecha límite (no anterior a hoy en UTC) y responsable existente.
- Creación idempotente con la cabecera `Idempotency-Key` (200 con la misma tarea, 409 si el
  cuerpo cambia).
- `core/clock.py`: `now()` y `today()` en UTC, sustituibles en los tests.
- `core/errors.py`: `conflict(message)` para respuestas 409 genéricas.
- `tests/test_tasks.py`: un test por criterio de aceptación (CA-01..CA-43).
