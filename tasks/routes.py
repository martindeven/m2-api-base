"""Rutas HTTP del recurso `tasks`.

Mismo patrón que `users/routes.py`: `response_model=` siempre, sin lógica de
negocio; la función delega en `service.py`, que levanta los errores con `core.errors`.

Endpoints:
  - `POST /tasks`: 201 al crear; 200 con la misma tarea si se repite la
    `Idempotency-Key` con el mismo cuerpo. El código lo elige la ruta a partir de lo
    que devuelve el service.
  - `GET /tasks`: listado por `id` ascendente, con filtro opcional `?assignee_id=`.
  - `GET /tasks/{task_id}`: una tarea, o 404.

La forma del cuerpo, de la cabecera y de los parámetros la valida FastAPI con Pydantic
(422 con `detail` en lista) antes de llegar al service. Los `summary`, `description` y
`responses=` solo documentan OpenAPI (`/docs`): no cambian el comportamiento.
"""
from fastapi import APIRouter, Header, Path, Query, Response, status

from tasks import service
from tasks.schemas import ErrorMessage, IdempotencyKey, Task, TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Al declarar 422 en `responses=`, FastAPI deja de añadir su esquema de validación: se
# referencia a mano (el componente existe porque lo generan las rutas con parámetros).
_VALIDATION_ERROR_SCHEMA = {"$ref": "#/components/schemas/HTTPValidationError"}
_SHAPE_ERROR_EXAMPLE = {
    "summary": "Forma inválida (formato de Pydantic, `detail` en lista)",
    "value": {
        "detail": [
            {
                "type": "string_too_short",
                "loc": ["body", "title"],
                "msg": "String should have at least 3 characters",
                "input": "ab",
                "ctx": {"min_length": 3},
            }
        ]
    },
}


@router.get(
    "",
    response_model=list[Task],
    summary="Listar tareas",
    description=(
        "Devuelve las tareas ordenadas por `id` ascendente. Con `?assignee_id=` devuelve "
        "solo las de ese responsable: es un filtro, así que un id inexistente, `0` o un "
        "negativo dan `[]`, no 404."
    ),
    responses={
        200: {"description": "Lista de tareas por `id` ascendente (`[]` si no hay ninguna)."},
        422: {
            "description": "`assignee_id` no es un entero.",
            "content": {
                "application/json": {
                    "schema": _VALIDATION_ERROR_SCHEMA,
                    "examples": {"forma": _SHAPE_ERROR_EXAMPLE},
                }
            },
        },
    },
)
def list_tasks(
    assignee_id: int | None = Query(
        default=None,
        description="Filtra por responsable. No se comprueba que el usuario exista.",
        examples=[1],
    ),
) -> list[Task]:
    return service.list_tasks(assignee_id)


@router.get(
    "/{task_id}",
    response_model=Task,
    summary="Consultar una tarea",
    description="Devuelve la tarea con ese `id`, igual que se devolvió al crearla.",
    responses={
        200: {"description": "La tarea existe."},
        404: {
            "model": ErrorMessage,
            "description": "No hay ninguna tarea con ese `id` (incluidos `0` y negativos).",
            "content": {
                "application/json": {"example": {"detail": "tarea no encontrado: 999"}}
            },
        },
        422: {
            "description": "`task_id` no es un entero.",
            "content": {
                "application/json": {
                    "schema": _VALIDATION_ERROR_SCHEMA,
                    "examples": {"forma": _SHAPE_ERROR_EXAMPLE},
                }
            },
        },
    },
)
def get_task(
    task_id: int = Path(description="Id de la tarea.", examples=[1]),
) -> Task:
    return service.get_task(task_id)


@router.post(
    "",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una tarea",
    description=(
        "Crea una tarea con `status` `\"pending\"`. El servidor asigna `id`, `status` y "
        "`created_at`, e ignora esos campos y los desconocidos si vienen en el cuerpo.\n\n"
        "**Idempotencia (opcional):** con la cabecera `Idempotency-Key`, repetir la "
        "petición con el mismo cuerpo devuelve 200 con la tarea original (mismo `id` y "
        "`created_at`) sin crear otra; con otro cuerpo, 409. El cuerpo se compara ya "
        "normalizado: `title` recortado y valores por defecto aplicados. La clave solo "
        "se guarda si la tarea se crea.\n\n"
        "**Orden de evaluación:** forma del cuerpo y la cabecera (422) → fecha límite "
        "pasada (422) → clave de idempotencia (200 / 409) → responsable (404) → "
        "creación (201)."
    ),
    responses={
        200: {
            "model": Task,
            "description": (
                "Repetición idempotente: misma `Idempotency-Key` y mismo cuerpo. Devuelve "
                "la tarea original; no se crea otra."
            ),
        },
        201: {"description": "Tarea creada."},
        404: {
            "model": ErrorMessage,
            "description": "`assignee_id` no corresponde a ningún usuario.",
            "content": {
                "application/json": {"example": {"detail": "usuario no encontrado: 999"}}
            },
        },
        409: {
            "model": ErrorMessage,
            "description": "La `Idempotency-Key` ya se usó con otro cuerpo.",
            "content": {
                "application/json": {
                    "example": {"detail": "clave de idempotencia ya existe: alta-backup-001"}
                }
            },
        },
        422: {
            "description": (
                "Forma inválida del cuerpo o de la cabecera (`detail` en lista, formato de "
                "Pydantic), o `due_date` anterior a hoy en UTC (`detail` de texto)."
            ),
            "content": {
                "application/json": {
                    "schema": {
                        "anyOf": [
                            _VALIDATION_ERROR_SCHEMA,
                            {"$ref": "#/components/schemas/ErrorMessage"},
                        ]
                    },
                    "examples": {
                        "forma": _SHAPE_ERROR_EXAMPLE,
                        "fecha_pasada": {
                            "summary": "Fecha límite anterior a hoy (`detail` de texto)",
                            "value": {
                                "detail": "la fecha límite no puede ser anterior a hoy (UTC)"
                            },
                        },
                    }
                }
            },
        },
    },
)
def create_task(
    data: TaskCreate,
    response: Response,
    idempotency_key: IdempotencyKey | None = Header(
        default=None,
        alias="Idempotency-Key",
        description=(
            "Opcional. Hace la creación idempotente. De 1 a 64 caracteres (no bytes), "
            "sin recortar y distinguiendo mayúsculas. La clave es global y no caduca. "
            "Vacía o de más de 64 caracteres da 422."
        ),
        examples=["alta-backup-001"],
    ),
) -> Task:
    # service decide si se ha creado (201) o es una repetición idempotente (200).
    task, created = service.create_task(data, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return task
