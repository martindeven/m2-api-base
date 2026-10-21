"""Lógica de negocio del recurso `tasks`.

Las rutas no acceden al repositorio directamente: pasan por aquí. Esta capa es la
única que conoce `repository.py`, la que consulta `users` a través de su
`service.py` y la que decide cuándo algo es un error de dominio (`core.errors`).

Las reglas de forma (tipos, rangos, longitudes) ya las ha aplicado Pydantic cuando
los datos llegan aquí. Esta capa aplica las reglas de dominio de
`docs/feature-tasks.md`: fecha límite no pasada, idempotencia con `Idempotency-Key`
y responsable existente, en el orden de evaluación del spec.
"""
import hashlib
import json
import threading
from datetime import date

from core import clock, errors
from tasks import repository
from tasks.schemas import Task, TaskCreate
from users import service as users_service

PAST_DUE_DATE_MESSAGE = "la fecha límite no puede ser anterior a hoy (UTC)"
# Campos que cuentan para la huella del cuerpo (A5).
FINGERPRINT_FIELDS = {"title", "description", "priority", "due_date", "assignee_id"}
# Serializa la sección de idempotencia y creación de `create_task` (también `_next_id`).
_create_lock = threading.Lock()


def create_task(data: TaskCreate, idempotency_key: str | None) -> tuple[Task, bool]:
    """Crea una tarea con estado `"pending"`, con idempotencia opcional.

    Aplica las reglas de dominio en el orden del spec:

    1. La fecha límite no es anterior a hoy (UTC).
    2. Busca la clave de idempotencia.
    3. Comprueba que el responsable existe.
    4. Crea la tarea.

    Con la misma clave y la misma huella del cuerpo normalizado, devuelve la tarea
    original sin crear otra, aunque las dos peticiones lleguen a la vez. La clave solo
    se guarda si la tarea se crea: un 404 o un 422 no la reserva.

    Args:
        data: Cuerpo ya validado y normalizado por Pydantic (`title` recortado, valores
            por defecto aplicados).
        idempotency_key: Valor de la cabecera `Idempotency-Key`, o `None` si no se
            envió. Sin clave no hay deduplicación.

    Returns:
        Una tupla `(task, created)`. `created` es `True` si la tarea se ha creado (la
        ruta responde 201), o `False` si es una repetición idempotente: misma clave y
        misma huella, devuelve la tarea original con el mismo `id` y `created_at`, y la
        ruta responde 200.

    Raises:
        HTTPException: 422 si `due_date` es anterior a hoy (UTC), aunque la petición
            repita una clave ya guardada. 409 si la clave ya existe con otra huella.
            404 si `assignee_id` no corresponde a ningún usuario.

    Example:
        Alta normal y repetición idempotente con la misma clave:

        >>> data = TaskCreate(title="  Revisar backups  ")
        >>> task, created = create_task(data, idempotency_key="alta-backup-001")
        >>> task.title, task.status, created
        ('Revisar backups', 'pending', True)
        >>> same_body = TaskCreate(title="Revisar backups", priority=3)
        >>> repeated, created = create_task(same_body, idempotency_key="alta-backup-001")
        >>> repeated == task, created
        (True, False)
    """
    _ensure_due_date_not_past(data.due_date)

    fingerprint = _fingerprint(data)
    # Las rutas síncronas corren en un threadpool: buscar la clave, crear y guardarla
    # debe ser atómico para que dos peticiones simultáneas no creen dos tareas.
    with _create_lock:
        replayed_task = _find_replayed_task(idempotency_key, fingerprint)
        if replayed_task is not None:
            return replayed_task, False

        _ensure_assignee_exists(data.assignee_id)
        return _save_task(data, idempotency_key, fingerprint), True


def _ensure_due_date_not_past(due_date: date | None) -> None:
    """Regla de dominio: la fecha límite no puede ser anterior a hoy (UTC)."""
    if due_date is not None and due_date < clock.today():
        raise errors.invalid_request(PAST_DUE_DATE_MESSAGE)


def _find_replayed_task(idempotency_key: str | None, fingerprint: str) -> Task | None:
    """Tarea original si es una repetición idempotente; 409 si la huella no coincide."""
    if idempotency_key is None:
        return None
    stored = repository.find_by_idempotency_key(idempotency_key)
    if stored is None:
        return None
    stored_fingerprint, stored_task = stored
    if stored_fingerprint != fingerprint:
        raise errors.already_exists("clave de idempotencia", idempotency_key)
    return stored_task


def _ensure_assignee_exists(assignee_id: int | None) -> None:
    """Regla de dominio: el responsable, si se indica, existe en `users`."""
    if assignee_id is not None:
        # get_user lanza errors.not_found("usuario", assignee_id) si no existe.
        users_service.get_user(assignee_id)


def _save_task(data: TaskCreate, idempotency_key: str | None, fingerprint: str) -> Task:
    """Persiste la tarea y, si hay clave, la guarda junto con su huella."""
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
    return task


def _fingerprint(data: TaskCreate) -> str:
    """Huella del cuerpo normalizado, independiente del orden de las claves."""
    normalized = data.model_dump(mode="json", include=FINGERPRINT_FIELDS)
    canonical = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_task(task_id: int) -> Task:
    """Devuelve una tarea por su id.

    Args:
        task_id: Identificador de la tarea. Cualquier entero es válido aquí: `0` y los
            negativos no son un error de forma, simplemente no existen.

    Returns:
        La tarea, igual que se devolvió al crearla.

    Raises:
        HTTPException: 404 ("tarea no encontrado: <id>") si no existe ninguna tarea
            con ese id, incluidos `0` y los negativos.
    """
    task = repository.get(task_id)
    if task is None:
        raise errors.not_found("tarea", task_id)
    return task


def list_tasks(assignee_id: int | None) -> list[Task]:
    """Lista las tareas por id ascendente, con filtro opcional por responsable.

    Args:
        assignee_id: Si se indica, solo devuelve las tareas de ese responsable. Es un
            filtro, no una consulta del usuario: no se comprueba que exista, así que un
            id inexistente, `0` o un negativo dan una lista vacía y no un 404.

    Returns:
        Las tareas ordenadas por `id` ascendente. La lista está vacía si no hay tareas o
        si ninguna coincide con el filtro.
    """
    if assignee_id is None:
        return repository.list_all()
    # Es un filtro: no se comprueba que el usuario exista (decisión 12).
    return repository.list_by_assignee(assignee_id)
