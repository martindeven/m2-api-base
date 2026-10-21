"""Schemas Pydantic del recurso `tasks`.

Las rutas devuelven siempre estos modelos (vía `response_model=`), nunca `dict`
crudos. Aquí van las validaciones de forma; las reglas de dominio van en `service.py`.

Validaciones de forma (`docs/feature-tasks.md`, decisiones 1–5 y A1):
  - `title`: se recorta con `str.strip()` y debe quedar con 3–120 caracteres.
  - `description`: máximo 1000 caracteres sobre el valor recibido.
  - `priority`: entero estricto de 1 a 5; vale 3 por defecto.
  - `due_date`: solo `YYYY-MM-DD`, y una fecha real.
  - `assignee_id`: entero estricto ≥ 1.

Los campos desconocidos o que asigna el servidor (`id`, `status`, `created_at`) se
ignoran en la entrada.
"""
import re
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)
from pydantic_core import PydanticKnownError

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 1000
PRIORITY_MIN = 1
PRIORITY_MAX = 5
PRIORITY_DEFAULT = 3
ASSIGNEE_ID_MIN = 1
IDEMPOTENCY_KEY_MIN_LENGTH = 1
IDEMPOTENCY_KEY_MAX_LENGTH = 64
DATE_ONLY_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _decode_utf8_header(value: object) -> object:
    """Recupera el texto UTF-8 de una cabecera que Starlette decodificó como latin-1.

    Así la longitud de la clave se cuenta en caracteres y no en bytes (decisión 10).
    Si los bytes no son UTF-8 válido, deja el valor tal cual.
    """
    if not isinstance(value, str):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return value


# StringConstraints antes que BeforeValidator: el validador envuelve al tipo y se ejecuta
# primero, de modo que la longitud se mide sobre el texto ya decodificado.
IdempotencyKey = Annotated[
    str,
    StringConstraints(min_length=IDEMPOTENCY_KEY_MIN_LENGTH, max_length=IDEMPOTENCY_KEY_MAX_LENGTH),
    BeforeValidator(_decode_utf8_header),
]


class TaskBase(BaseModel):
    title: Annotated[
        str,
        Field(
            min_length=TITLE_MIN_LENGTH,
            max_length=TITLE_MAX_LENGTH,
            description=(
                "Título de la tarea. Se recortan los espacios de los extremos y, tras "
                "recortar, debe tener entre 3 y 120 caracteres."
            ),
            examples=["Revisar backups"],
        ),
    ]
    description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
        description=(
            "Descripción libre. Se guarda tal cual, sin recortar; máximo 1000 caracteres "
            "sobre el valor recibido. `\"\"` es válido; omitida equivale a `null`."
        ),
        examples=["Comprobar que la copia nocturna terminó sin errores"],
    )
    priority: Annotated[
        int,
        Field(
            strict=True,
            ge=PRIORITY_MIN,
            le=PRIORITY_MAX,
            description=(
                "Prioridad de 1 a 5, entero estricto: `3.0`, `\"3\"`, `true` o `null` dan "
                "422. Si se omite, vale 3."
            ),
            examples=[2],
        ),
    ] = PRIORITY_DEFAULT
    due_date: date | None = Field(
        default=None,
        description=(
            "Fecha límite en formato `YYYY-MM-DD`, sin hora. No puede ser anterior a hoy "
            "en UTC (fecha del servidor). Omitida equivale a `null`."
        ),
        examples=["2026-12-31"],
    )
    # La descripción va en el Field exterior: dentro de `| None` OpenAPI la pierde.
    assignee_id: Annotated[int, Field(strict=True, ge=ASSIGNEE_ID_MIN)] | None = Field(
        default=None,
        description=(
            "Id del responsable: entero estricto ≥ 1 que debe existir en `users` (si no "
            "existe, 404). `null` o ausente: tarea sin responsable."
        ),
        examples=[1],
    )

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        """Recorta con `str.strip()` (A4) antes de medir la longitud con el `Field`.

        Los errores de longitud y de tipo son los de Pydantic por defecto (decisión 1).
        """
        return value.strip() if isinstance(value, str) else value

    @field_validator("due_date", mode="before")
    @classmethod
    def require_date_only(cls, value: object) -> object:
        """Solo acepta `YYYY-MM-DD`: sin hora, aunque sea 00:00:00 (CA-17)."""
        if value is None or isinstance(value, date):
            return value
        if not isinstance(value, str) or not DATE_ONLY_PATTERN.fullmatch(value):
            # Error de Pydantic por defecto, sin mensaje propio (decisión 1).
            raise PydanticKnownError("date_type")
        # Pydantic valida después que sea una fecha real (p. ej. rechaza 2026-02-30).
        return value


class TaskCreate(TaskBase):
    """Cuerpo de entrada para crear una tarea."""

    # Los campos desconocidos o que asigna el servidor se ignoran (por defecto en Pydantic).
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "  Revisar backups  ",
                    "description": "Comprobar que la copia nocturna terminó sin errores",
                    "priority": 2,
                    "due_date": "2026-12-31",
                    "assignee_id": 1,
                }
            ]
        }
    )


class Task(TaskBase):
    """Tarea tal como la devuelve la API."""

    id: int = Field(description="Id asignado por el servidor; empieza en 1.", examples=[1])
    # TODO(CA-01): solo "pending" en este sprint.
    status: str = Field(description='Siempre `"pending"` en este sprint.', examples=["pending"])
    created_at: datetime = Field(
        description="Fecha y hora de creación en UTC (ISO 8601), asignada por el servidor.",
        examples=["2026-10-20T09:30:00Z"],
    )


class ErrorMessage(BaseModel):
    """Error de dominio: `detail` es un texto en español generado por `core/errors.py`.

    Solo documenta la respuesta en OpenAPI; las rutas no lo instancian.
    """

    detail: str = Field(examples=["usuario no encontrado: 999"])
