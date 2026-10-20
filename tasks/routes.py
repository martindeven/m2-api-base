"""Rutas HTTP del recurso `tasks`.

Mismo patrón que `users/routes.py`: `response_model=` siempre, sin lógica de
negocio; la función delega en `service.py`, que levanta los errores con `core.errors`.
"""
from fastapi import APIRouter, Header, status

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
    # TODO(CA-32): min_length=1, max_length=64 en el Header.
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Task:
    # TODO(CA-26, CA-27): responder 200 (no 201) en una repetición idempotente.
    return service.create_task(data, idempotency_key)
