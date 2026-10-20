"""Rutas HTTP del recurso `tasks`.

Mismo patrón que `users/routes.py`: `response_model=` siempre, sin lógica de
negocio; la función delega en `service.py`, que levanta los errores con `core.errors`.
"""
from fastapi import APIRouter, Header, Response, status

from tasks import service
from tasks.schemas import Task, TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def list_tasks(assignee_id: int | None = None) -> list[Task]:
    return service.list_tasks(assignee_id)


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    return service.get_task(task_id)


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    response: Response,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=1, max_length=64
    ),
) -> Task:
    # service decide si se ha creado (201) o es una repetición idempotente (200).
    task, created = service.create_task(data, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return task
