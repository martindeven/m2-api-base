"""Tests unitarios de `tasks/service.py` (sin TestClient).

Reglas de `docs/feature-tasks.md`. Qué se aísla y qué no:
  - dependencias mockeadas con monkeypatch: el reloj (`core.clock.today`, fijado en
    2026-10-20) y la consulta de usuarios (`users.service.get_user`, un fake que
    registra los ids consultados)
  - lógica bajo prueba, sin mockear: validación de fecha, idempotencia (huella) y filtro;
    el repositorio en memoria es real y lo limpia la fixture autouse de `conftest.py`
  - cada test indica, cuando no es obvio, qué mutación del service detecta
"""
import threading
import time
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from core import errors
from tasks import repository as tasks_repository
from tasks import service
from tasks.schemas import Task, TaskCreate
from users.schemas import User

TODAY = date(2026, 10, 20)
EXISTING_USER_IDS = {1, 2, 3, 4}
KEY = "alta-backup-001"


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoy = 2026-10-20 (UTC)."""
    monkeypatch.setattr("core.clock.today", lambda: TODAY)


@pytest.fixture(autouse=True)
def user_lookups(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Sustituye `users.service.get_user` y devuelve la lista de ids consultados."""
    calls: list[int] = []

    def fake_get_user(user_id: int) -> User:
        calls.append(user_id)
        if user_id not in EXISTING_USER_IDS:
            raise errors.not_found("usuario", user_id)
        return User(
            id=user_id,
            name=f"Usuario {user_id}",
            email=f"usuario{user_id}@example.com",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    monkeypatch.setattr("users.service.get_user", fake_get_user)
    return calls


# --- create_task: happy path ------------------------------------------------


def test_crear_tarea_valida_queda_pendiente_con_los_valores_recibidos() -> None:
    # Arrange
    data = TaskCreate(title="Rotar certificados", description="Servidores web", priority=5)

    # Act
    task, created = service.create_task(data, idempotency_key=None)

    # Assert
    assert created is True
    assert task.id == 1
    assert task.status == "pending"
    assert (task.title, task.description, task.priority) == (
        "Rotar certificados",
        "Servidores web",
        5,
    )
    assert (task.due_date, task.assignee_id) == (None, None)


def test_crear_dos_tareas_asigna_ids_incrementales() -> None:
    # Arrange
    data = TaskCreate(title="Revisar backups")

    # Act
    first, first_created = service.create_task(data, idempotency_key=None)
    second, second_created = service.create_task(data, idempotency_key=None)

    # Assert
    assert (first.id, second.id) == (1, 2)
    assert (first_created, second_created) == (True, True)
    assert tasks_repository.list_all() == [first, second]


def test_crear_con_responsable_existente_consulta_ese_usuario(user_lookups: list[int]) -> None:
    # Arrange
    data = TaskCreate(title="Revisar backups", assignee_id=2)

    # Act
    task, created = service.create_task(data, idempotency_key=None)

    # Assert
    assert created is True
    assert task.assignee_id == 2
    assert user_lookups == [2]


# --- create_task: due_date --------------------------------------------------


def test_fecha_limite_ayer_da_422_y_no_crea_la_tarea() -> None:
    # Arrange
    data = TaskCreate(title="Tarea atrasada", due_date=TODAY - timedelta(days=1))

    # Act
    with pytest.raises(HTTPException) as error:
        service.create_task(data, idempotency_key=None)

    # Assert
    assert error.value.status_code == 422
    assert error.value.detail == service.PAST_DUE_DATE_MESSAGE
    assert tasks_repository.list_all() == []


def test_fecha_limite_hoy_es_valida() -> None:
    # Detecta `<` → `<=` en la comparación con hoy.
    # Arrange
    data = TaskCreate(title="Tarea de hoy", due_date=TODAY)

    # Act
    task, created = service.create_task(data, idempotency_key=None)

    # Assert
    assert created is True
    assert task.due_date == TODAY
    assert tasks_repository.list_all() == [task]


def test_fecha_limite_none_es_valida() -> None:
    # Detecta `and` → `or` (comparar None con una fecha lanza TypeError).
    # Arrange
    data = TaskCreate(title="Sin fecha", due_date=None)

    # Act
    task, created = service.create_task(data, idempotency_key=None)

    # Assert
    assert created is True
    assert task.due_date is None
    assert tasks_repository.list_all() == [task]


# --- create_task: assignee_id -----------------------------------------------


def test_responsable_inexistente_da_404_y_no_crea_la_tarea(user_lookups: list[int]) -> None:
    # Arrange
    data = TaskCreate(title="Tarea huérfana", assignee_id=999)

    # Act
    with pytest.raises(HTTPException) as error:
        service.create_task(data, idempotency_key=None)

    # Assert
    assert error.value.status_code == 404
    assert error.value.detail == "usuario no encontrado: 999"
    assert user_lookups == [999]
    assert tasks_repository.list_all() == []


def test_responsable_none_no_consulta_usuarios(user_lookups: list[int]) -> None:
    # Detecta `is not None` → `is None` en la comprobación del responsable.
    # Arrange
    data = TaskCreate(title="Sin responsable", assignee_id=None)

    # Act
    task, created = service.create_task(data, idempotency_key=None)

    # Assert
    assert created is True
    assert task.assignee_id is None
    assert user_lookups == []


# --- create_task: idempotencia ----------------------------------------------


def test_misma_clave_y_mismo_cuerpo_devuelve_la_tarea_original() -> None:
    # Arrange
    data = TaskCreate(title="Revisar backups", priority=2)
    original, _ = service.create_task(data, idempotency_key=KEY)

    # Act
    repeated, created = service.create_task(data, idempotency_key=KEY)

    # Assert
    assert created is False
    assert repeated == original
    assert (repeated.id, repeated.created_at) == (original.id, original.created_at)
    assert len(tasks_repository.list_all()) == 1


def test_misma_clave_y_otro_cuerpo_da_409() -> None:
    # Arrange
    service.create_task(TaskCreate(title="Revisar backups"), idempotency_key=KEY)

    # Act
    with pytest.raises(HTTPException) as error:
        service.create_task(TaskCreate(title="Otra tarea"), idempotency_key=KEY)

    # Assert
    assert error.value.status_code == 409
    assert error.value.detail == f"clave de idempotencia ya existe: {KEY}"
    assert len(tasks_repository.list_all()) == 1


def test_claves_distintas_crean_dos_tareas() -> None:
    # Arrange
    data = TaskCreate(title="Revisar backups")

    # Act
    first, first_created = service.create_task(data, idempotency_key="abc")
    second, second_created = service.create_task(data, idempotency_key="ABC")

    # Assert
    assert (first_created, second_created) == (True, True)
    assert (first.id, second.id) == (1, 2)
    assert tasks_repository.list_all() == [first, second]


@pytest.mark.parametrize(
    "changed_field",
    [
        {"description": ""},
        {"priority": 4},
        {"due_date": TODAY + timedelta(days=1)},
        {"assignee_id": 2},
    ],
    ids=["description_vacia_frente_a_none", "priority", "due_date", "assignee_id"],
)
def test_misma_clave_cambiando_un_solo_campo_da_409(changed_field: dict) -> None:
    # Refuerzo: cada campo de FINGERPRINT_FIELDS cuenta en la huella. Detecta que mutmut
    # cambie uno de esos literales (el test de 409 anterior solo cubre `title`).
    # Arrange
    original, _ = service.create_task(TaskCreate(title="Revisar backups"), idempotency_key=KEY)
    other = TaskCreate(title="Revisar backups", **changed_field)

    # Act
    with pytest.raises(HTTPException) as error:
        service.create_task(other, idempotency_key=KEY)

    # Assert
    assert error.value.status_code == 409
    assert error.value.detail == f"clave de idempotencia ya existe: {KEY}"
    assert tasks_repository.list_all() == [original]


def test_dos_peticiones_simultaneas_con_la_misma_clave_crean_una_sola_tarea(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Decisión 11: misma clave y misma huella no crea otra tarea, tampoco en paralelo.
    # La consulta lenta del responsable abre la ventana entre buscar y guardar la clave.
    # Arrange
    def slow_get_user(user_id: int) -> None:
        time.sleep(0.05)

    monkeypatch.setattr("users.service.get_user", slow_get_user)
    data = TaskCreate(title="Revisar backups", assignee_id=1)
    results: list[tuple[Task, bool]] = []

    def create() -> None:
        results.append(service.create_task(data, idempotency_key=KEY))

    threads = [threading.Thread(target=create) for _ in range(2)]

    # Act
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Assert
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0] == results[1][0]
    assert len(tasks_repository.list_all()) == 1


def test_un_404_previo_no_reserva_la_clave() -> None:
    # Refuerzo (CA-29): la clave solo se guarda tras crear la tarea.
    # Arrange
    with pytest.raises(HTTPException):
        service.create_task(TaskCreate(title="Tarea huérfana", assignee_id=999), KEY)

    # Act
    task, created = service.create_task(TaskCreate(title="Revisar backups"), KEY)

    # Assert
    assert created is True
    assert task.id == 1
    assert tasks_repository.list_all() == [task]


# --- create_task: huella del cuerpo -----------------------------------------


def test_description_none_y_omitida_tienen_la_misma_huella() -> None:
    # Decisión 2: omitida y null son equivalentes; la huella usa el cuerpo normalizado.
    # Arrange
    original, _ = service.create_task(TaskCreate(title="Revisar backups"), KEY)

    # Act
    repeated, created = service.create_task(
        TaskCreate(title="Revisar backups", description=None), KEY
    )

    # Assert
    assert created is False
    assert repeated.id == original.id
    assert len(tasks_repository.list_all()) == 1


# --- get_task ---------------------------------------------------------------


def test_obtener_tarea_existente_la_devuelve() -> None:
    # Arrange
    created_task, _ = service.create_task(TaskCreate(title="Revisar backups"), None)

    # Act
    task = service.get_task(created_task.id)

    # Assert
    assert task == created_task
    assert task.id == 1
    assert task.title == "Revisar backups"


def test_obtener_tarea_inexistente_da_404() -> None:
    # Arrange: hay una tarea, para que el 404 no se deba a un almacén vacío.
    existing, _ = service.create_task(TaskCreate(title="Revisar backups"), None)

    # Act
    with pytest.raises(HTTPException) as error:
        service.get_task(999)

    # Assert
    assert error.value.status_code == 404
    assert error.value.detail == "tarea no encontrado: 999"
    assert tasks_repository.list_all() == [existing]


# --- list_tasks -------------------------------------------------------------


def _create_tasks_for(assignee_ids: list[int | None]) -> None:
    for position, assignee_id in enumerate(assignee_ids, start=1):
        service.create_task(TaskCreate(title=f"Tarea {position}", assignee_id=assignee_id), None)


def test_listar_sin_filtro_devuelve_todas_en_orden_de_id() -> None:
    # Arrange
    _create_tasks_for([1, 2, None])

    # Act
    tasks = service.list_tasks(assignee_id=None)

    # Assert
    assert [task.id for task in tasks] == [1, 2, 3]
    assert [task.title for task in tasks] == ["Tarea 1", "Tarea 2", "Tarea 3"]
    assert [task.assignee_id for task in tasks] == [1, 2, None]


def test_listar_con_filtro_devuelve_solo_las_del_responsable() -> None:
    # Refuerzo: detecta que se devuelva `list_all` sin filtrar.
    # Arrange
    _create_tasks_for([1, 2, 1, None])

    # Act
    tasks = service.list_tasks(assignee_id=1)

    # Assert
    assert [task.id for task in tasks] == [1, 3]
    assert [task.title for task in tasks] == ["Tarea 1", "Tarea 3"]
    assert [task.assignee_id for task in tasks] == [1, 1]


def test_listar_con_filtro_sin_coincidencias_devuelve_lista_vacia(
    user_lookups: list[int],
) -> None:
    # Hay tareas: detecta `is None` → `is not None` (devolvería todas).
    # Arrange
    _create_tasks_for([1, 2])

    # Act
    tasks = service.list_tasks(assignee_id=999)

    # Assert
    assert tasks == []
    assert len(tasks_repository.list_all()) == 2
    # Solo las 2 altas consultaron usuarios: el filtro no lo hace (decisión 12).
    assert user_lookups == [1, 2]
