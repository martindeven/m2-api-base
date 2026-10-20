"""Schemas Pydantic del recurso `tasks`.

Las rutas devuelven siempre estos modelos (vía `response_model=`), nunca `dict`
crudos. Aquí van las validaciones de forma; las reglas de dominio van en `service.py`.
"""
from datetime import date, datetime

from pydantic import BaseModel


class TaskBase(BaseModel):
    # TODO(CA-04..CA-08): strip y longitud 3–120 tras recortar; debe ser texto.
    title: str
    # TODO(CA-09..CA-11): máximo 1000 sobre el valor recibido, sin strip.
    description: str | None = None
    # TODO(CA-12..CA-14): entero estricto, rango 1–5.
    priority: int = 3
    # TODO(CA-17): solo formato YYYY-MM-DD y fecha real (sin hora).
    due_date: date | None = None
    # TODO(CA-22): entero estricto, ≥ 1.
    assignee_id: int | None = None


class TaskCreate(TaskBase):
    """Cuerpo de entrada para crear una tarea."""

    # TODO(CA-03): los campos desconocidos o que asigna el servidor se ignoran
    # (comportamiento por defecto de Pydantic; comprobarlo en los tests).


class Task(TaskBase):
    """Tarea tal como la devuelve la API."""

    id: int
    # TODO(CA-01): solo "pending" en este sprint.
    status: str
    created_at: datetime
