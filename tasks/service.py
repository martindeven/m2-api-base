"""Lógica de negocio del recurso `tasks`.

Las rutas no acceden al repositorio directamente: pasan por aquí. Esta capa es la
única que conoce `repository.py`, la que consulta `users` a través de su
`service.py` y la que decide cuándo algo es un error de dominio (`core.errors`).
"""
from core import clock, errors
from tasks import repository
from tasks.schemas import Task, TaskCreate
from users import service as users_service

PAST_DUE_DATE_MESSAGE = "la fecha límite no puede ser anterior a hoy (UTC)"


def create_task(data: TaskCreate, idempotency_key: str | None) -> Task:
    """Crea una tarea, con idempotencia opcional.

    Args:
        data: Cuerpo ya validado y normalizado por Pydantic.
        idempotency_key: Valor de la cabecera `Idempotency-Key`, o None si no se envió.

    Returns:
        La tarea creada, o la original si es una repetición idempotente.

    Raises:
        HTTPException: 422 si `due_date` es anterior a hoy (UTC), 409 si la clave ya
            existe con otra huella, 404 si el responsable no existe.
    """
    if data.due_date is not None and data.due_date < clock.today():
        raise errors.invalid_request(PAST_DUE_DATE_MESSAGE)
    # TODO(CA-26, CA-27, CA-28, CA-30, CA-31, CA-33): si hay clave, buscarla; misma huella
    #     -> tarea original; huella distinta ->
    #     errors.already_exists("clave de idempotencia", clave). Huella sobre los 5 campos
    #     normalizados (A5).
    if data.assignee_id is not None:
        # get_user lanza errors.not_found("usuario", assignee_id) si no existe.
        users_service.get_user(data.assignee_id)
    # TODO(CA-29): si hay clave, guardarla con su huella solo tras crear.
    return repository.add(
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
        assignee_id=data.assignee_id,
    )


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
