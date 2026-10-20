"""Almacén en memoria del recurso `tasks`.

Sustituye a una base de datos real para que el proyecto sea ejecutable sin
infraestructura. Guarda las tareas y las claves de idempotencia (con la huella del
cuerpo y la tarea creada). Solo `service.py` debería usar este módulo.
"""
from datetime import date

from tasks.schemas import Task

_tasks: dict[int, Task] = {}
_next_id: int = 1
# clave de idempotencia -> (huella del cuerpo, tarea creada)
_idempotency_keys: dict[str, tuple[str, Task]] = {}


def add(
    *,
    title: str,
    description: str | None,
    priority: int,
    due_date: date | None,
    assignee_id: int | None,
) -> Task:
    # TODO(CA-01, CA-02): id incremental desde 1, status "pending", created_at en UTC.
    raise NotImplementedError


def get(task_id: int) -> Task | None:
    # TODO(CA-39, CA-40): devolver la tarea o None.
    raise NotImplementedError


def list_all() -> list[Task]:
    # TODO(CA-34, CA-35): todas las tareas ordenadas por id ascendente.
    raise NotImplementedError


def list_by_assignee(assignee_id: int) -> list[Task]:
    # TODO(CA-36, CA-37): tareas de ese responsable, por id ascendente; [] si no hay.
    raise NotImplementedError


def find_by_idempotency_key(key: str) -> tuple[str, Task] | None:
    # TODO(CA-26..CA-28, CA-31): (huella, tarea) guardadas para la clave, o None.
    raise NotImplementedError


def save_idempotency_key(key: str, fingerprint: str, task: Task) -> None:
    # TODO(CA-26, CA-29): guardar la clave solo tras un 201.
    raise NotImplementedError


def reset() -> None:
    """Vacía tareas y claves de idempotencia. Se usa entre tests."""
    # TODO(CA-42): limpiar _tasks y _idempotency_keys y reiniciar _next_id.
    raise NotImplementedError
