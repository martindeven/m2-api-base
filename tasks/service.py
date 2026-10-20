"""Lógica de negocio del recurso `tasks`.

Las rutas no acceden al repositorio directamente: pasan por aquí. Esta capa es la
única que conoce `repository.py`, la que consulta `users` a través de su
`service.py` y la que decide cuándo algo es un error de dominio (`core.errors`).
"""
import hashlib
import json

from core import clock, errors
from tasks import repository
from tasks.schemas import Task, TaskCreate
from users import service as users_service

PAST_DUE_DATE_MESSAGE = "la fecha límite no puede ser anterior a hoy (UTC)"
# Campos que cuentan para la huella del cuerpo (A5).
FINGERPRINT_FIELDS = {"title", "description", "priority", "due_date", "assignee_id"}


def create_task(data: TaskCreate, idempotency_key: str | None) -> tuple[Task, bool]:
    """Crea una tarea, con idempotencia opcional.

    Args:
        data: Cuerpo ya validado y normalizado por Pydantic.
        idempotency_key: Valor de la cabecera `Idempotency-Key`, o None si no se envió.

    Returns:
        La tarea y `created`: `True` si se ha creado, o `False` con la tarea original si
        es una repetición idempotente (misma clave y misma huella).

    Raises:
        HTTPException: 422 si `due_date` es anterior a hoy (UTC), 409 si la clave ya
            existe con otra huella, 404 si el responsable no existe.
    """
    if data.due_date is not None and data.due_date < clock.today():
        raise errors.invalid_request(PAST_DUE_DATE_MESSAGE)

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

    if data.assignee_id is not None:
        # get_user lanza errors.not_found("usuario", assignee_id) si no existe.
        users_service.get_user(data.assignee_id)

    task = repository.add(
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
        assignee_id=data.assignee_id,
    )
    # La clave solo se guarda tras crear: un 404 o 422 previo no la reserva (CA-29).
    if idempotency_key is not None:
        repository.save_idempotency_key(idempotency_key, fingerprint, task)
    return task, True


def _fingerprint(data: TaskCreate) -> str:
    """Huella del cuerpo normalizado, independiente del orden de las claves."""
    normalized = data.model_dump(mode="json", include=FINGERPRINT_FIELDS)
    canonical = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_task(task_id: int) -> Task:
    """Devuelve una tarea por su id.

    Args:
        task_id: Identificador de la tarea.

    Returns:
        La tarea encontrada.

    Raises:
        HTTPException: 404 si no existe ninguna tarea con ese id.
    """
    task = repository.get(task_id)
    if task is None:
        raise errors.not_found("tarea", task_id)
    return task


def list_tasks(assignee_id: int | None) -> list[Task]:
    """Lista las tareas por id ascendente, con filtro opcional por responsable.

    Args:
        assignee_id: Si se indica, solo las tareas de ese responsable.

    Returns:
        Lista de tareas; vacía si no hay ninguna (o ninguna coincide con el filtro).
    """
    if assignee_id is None:
        return repository.list_all()
    # Es un filtro: no se comprueba que el usuario exista (decisión 12).
    return repository.list_by_assignee(assignee_id)
