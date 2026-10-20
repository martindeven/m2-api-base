"""Schemas Pydantic del recurso `tasks`.

Las rutas devuelven siempre estos modelos (vía `response_model=`), nunca `dict`
crudos. Aquí van las validaciones de forma; las reglas de dominio van en `service.py`.
"""
import re
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 120
DATE_ONLY_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class TaskBase(BaseModel):
    title: str
    description: str | None = Field(default=None, max_length=1000)
    priority: Annotated[int, Field(strict=True, ge=1, le=5)] = 3
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

    @field_validator("due_date", mode="before")
    @classmethod
    def require_date_only(cls, value: object) -> object:
        """Solo acepta `YYYY-MM-DD`: sin hora, aunque sea 00:00:00 (CA-17)."""
        if value is None or isinstance(value, date):
            return value
        if not isinstance(value, str) or not DATE_ONLY_PATTERN.fullmatch(value):
            raise ValueError("la fecha límite debe tener el formato YYYY-MM-DD")
        # Pydantic valida después que sea una fecha real (p. ej. rechaza 2026-02-30).
        return value


class TaskCreate(TaskBase):
    """Cuerpo de entrada para crear una tarea."""

    # Los campos desconocidos o que asigna el servidor se ignoran (por defecto en Pydantic).


class Task(TaskBase):
    """Tarea tal como la devuelve la API."""

    id: int
    # TODO(CA-01): solo "pending" en este sprint.
    status: str
    created_at: datetime
