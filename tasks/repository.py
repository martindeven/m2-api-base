"""Almacén en memoria del recurso `tasks`.

Sustituye a una base de datos real para que el proyecto sea ejecutable sin
infraestructura. Guarda las tareas y las claves de idempotencia (con la huella del
cuerpo y la tarea creada). Solo `service.py` debería usar este módulo.

Arranca vacío: no hay datos semilla de tareas. Las claves de idempotencia son globales y
no caducan; solo `reset()` las borra. Este módulo no valida nada ni decide errores:
eso lo hace `service.py`.
"""
from datetime import date

from core import clock
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
    """Guarda una tarea nueva con los valores que asigna el servidor.

    El servidor pone `id` (correlativo, empieza en 1), `status` (siempre `"pending"`
    en este sprint) y `created_at` (`clock.now()`, en UTC). Los demás campos se guardan
    tal como llegan.

    Args:
        title: Título ya recortado.
        description: Descripción tal como se recibió, o `None`.
        priority: Prioridad de 1 a 5.
        due_date: Fecha límite, o `None`.
        assignee_id: Id de un usuario existente, o `None`.

    Returns:
        La tarea creada.
    """
    global _next_id
    task = Task(
        id=_next_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        assignee_id=assignee_id,
        status="pending",
        created_at=clock.now(),
    )
    _tasks[task.id] = task
    _next_id += 1
    return task


def get(task_id: int) -> Task | None:
    """Busca una tarea por id.

    Args:
        task_id: Identificador de la tarea.

    Returns:
        La tarea, o `None` si no existe. El 404 lo decide `service.py`.
    """
    return _tasks.get(task_id)


def list_all() -> list[Task]:
    """Devuelve todas las tareas.

    Returns:
        Las tareas ordenadas por `id` ascendente. Los ids son crecientes y el `dict`
        conserva el orden de inserción, así que no hace falta ordenar.
    """
    return list(_tasks.values())


def list_by_assignee(assignee_id: int) -> list[Task]:
    """Devuelve las tareas de un responsable.

    Args:
        assignee_id: Id del responsable. No se comprueba que exista.

    Returns:
        Las tareas con ese `assignee_id`, ordenadas por `id` ascendente. Si no hay
        ninguna, la lista está vacía.
    """
    return [task for task in _tasks.values() if task.assignee_id == assignee_id]


def find_by_idempotency_key(key: str) -> tuple[str, Task] | None:
    """Busca una clave de idempotencia guardada.

    Args:
        key: Valor exacto de la cabecera `Idempotency-Key`. Distingue mayúsculas y no se
            recorta.

    Returns:
        La tupla `(huella, tarea)` que se guardó al crear la tarea, o `None` si la
        clave no se ha usado en una creación con éxito.
    """
    return _idempotency_keys.get(key)


def save_idempotency_key(key: str, fingerprint: str, task: Task) -> None:
    """Asocia una clave de idempotencia a la huella del cuerpo y a la tarea creada.

    Solo se llama después de crear la tarea, de modo que una petición fallida no
    reserva la clave. Si la clave ya existía, la sobrescribe. `service.py` evita que
    ocurra: comprueba la clave antes de crear, con el mismo lock.

    Args:
        key: Valor exacto de la cabecera `Idempotency-Key`.
        fingerprint: Huella SHA-256 del cuerpo normalizado.
        task: Tarea creada con esa clave. Es la que devuelven las repeticiones.
    """
    _idempotency_keys[key] = (fingerprint, task)


def reset() -> None:
    """Vacía las tareas y las claves de idempotencia, y reinicia los ids a 1.

    La fixture autouse `_reset_data` de `tests/conftest.py` la llama antes y después de
    cada test.
    """
    global _next_id
    _tasks.clear()
    _idempotency_keys.clear()
    _next_id = 1
