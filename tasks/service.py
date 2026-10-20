"""Lógica de negocio del recurso `tasks`.

Las rutas no acceden al repositorio directamente: pasan por aquí. Esta capa es la
única que conoce `repository.py`, la que consulta `users` a través de su
`service.py` y la que decide cuándo algo es un error de dominio (`core.errors`).
"""
from tasks.schemas import Task, TaskCreate


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
    # TODO(CA-16, CA-19, CA-25): due_date < clock.today() -> errors.invalid_request(
    #     "la fecha límite no puede ser anterior a hoy (UTC)").
    # TODO(CA-26, CA-27, CA-28, CA-30, CA-31, CA-33): si hay clave, buscarla; misma huella
    #     -> tarea original; huella distinta ->
    #     errors.already_exists("clave de idempotencia", clave). Huella sobre los 5 campos
    #     normalizados (A5).
    # TODO(CA-20, CA-21, CA-24): si hay assignee_id, comprobarlo vía users.service.get_user
    #     (404 con errors.not_found).
    # TODO(CA-01, CA-02, CA-29): crear con repository.add y, si hay clave, guardarla con
    #     su huella solo tras crear.
    raise NotImplementedError


def get_task(task_id: int) -> Task:
    """Devuelve una tarea por su id.

    Args:
        task_id: Identificador de la tarea.

    Returns:
        La tarea encontrada.

    Raises:
        HTTPException: 404 si no existe ninguna tarea con ese id.
    """
    # TODO(CA-39): devolver repository.get(task_id).
    # TODO(CA-40): si no existe -> errors.not_found("tarea", task_id).
    raise NotImplementedError


def list_tasks(assignee_id: int | None) -> list[Task]:
    """Lista las tareas por id ascendente, con filtro opcional por responsable.

    Args:
        assignee_id: Si se indica, solo las tareas de ese responsable.

    Returns:
        Lista de tareas; vacía si no hay ninguna (o ninguna coincide con el filtro).
    """
    # TODO(CA-34, CA-35): sin filtro -> repository.list_all().
    # TODO(CA-36, CA-37): con filtro -> repository.list_by_assignee(assignee_id),
    #     sin comprobar que el usuario exista.
    raise NotImplementedError
