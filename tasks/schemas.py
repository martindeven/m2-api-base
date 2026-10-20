"""Schemas Pydantic del recurso `tasks`.

Las rutas devuelven siempre estos modelos (vía `response_model=`), nunca `dict`
crudos. Aquí van las validaciones de forma; las reglas de dominio van en `service.py`.
"""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 120


class TaskBase(BaseModel):
    title: str
    description: str | None = Field(default=None, max_length=1000)
    priority: Annotated[int, Field(strict=True, ge=1, le=5)] = 3
    # TODO(CA-17): solo formato YYYY-MM-DD y fecha real (sin hora).
    due_date: date | None = None
    assignee_id: Annotated[int, Field(strict=True, ge=1)] | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """Recorta con `str.strip()` y mide la longitud ya recortada."""
        title = value.strip()
        if not TITLE_MIN_LENGTH <= len(title) <= TITLE_MAX_LENGTH:
            raise ValueError(
                f"el título debe tener entre {TITLE_MIN_LENGTH} y {TITLE_MAX_LENGTH} "
                "caracteres tras recortar"
            )
        return title


class TaskCreate(TaskBase):
    """Cuerpo de entrada para crear una tarea."""

    # Los campos desconocidos o que asigna el servidor se ignoran (por defecto en Pydantic).


class Task(TaskBase):
    """Tarea tal como la devuelve la API."""

    id: int
    # TODO(CA-01): solo "pending" en este sprint.
    status: str
    created_at: datetime
