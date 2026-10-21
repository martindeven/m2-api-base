"""Recurso `tasks`: registro de tareas de equipo.

Crear, listar y consultar tareas con responsable, prioridad y fecha límite, y crearlas
de forma idempotente con `Idempotency-Key`. Especificación: `docs/feature-tasks.md`.
Sigue el patrón de capas del proyecto: `routes` → `service` → `repository`, con los
errores de `core/errors.py`.
"""
