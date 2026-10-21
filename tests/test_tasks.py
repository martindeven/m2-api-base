"""Tests del recurso `tasks`.

Un único archivo por recurso (CLAUDE.md), en cuatro secciones:
  - criterios de aceptación de `docs/feature-tasks.md`: un test por criterio CA-XX, con
    TestClient y el mismo estilo que `test_users.py`
  - `TestService`: tests unitarios de `tasks/service.py`; dentro de la clase,
    `users.service.get_user` se sustituye por un fake que registra los ids consultados, y
    cada test indica, cuando no es obvio, qué mutación del service detecta
  - integración con `users`: la app real, sin nada mockeado salvo el reloj
  - reloj: `core/clock.py` con `core.clock.now` fijado y el `today()` real

Setup / teardown:
  - `_reset_data` (autouse, `conftest.py`) deja los 4 usuarios semilla, sin tareas ni
    claves de idempotencia, antes y después de cada test
  - `_fixed_today` (autouse, aquí) fija `core.clock.today` en 2026-10-20 (UTC) con
    monkeypatch; los tests de reloj usan `_real_today`, guardado antes de cualquier patch
"""
import threading
import time
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from core import clock, errors
from tasks import repository as tasks_repository
from tasks import service
from tasks.schemas import Task, TaskCreate
from users.schemas import User

TODAY = date(2026, 10, 20)
EXISTING_USER_IDS = {1, 2, 3, 4}
SEED_USER_IDS = [1, 2, 3, 4]
KEY = "alta-backup-001"
# `today()` real, guardado al importar: `_fixed_today` sustituye `core.clock.today`.
_real_today = clock.today


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los criterios con fecha parten de hoy = 2026-10-20 (UTC)."""
    monkeypatch.setattr("core.clock.today", lambda: TODAY)


def _post(client: TestClient, body: dict, key: str | None = None):
    headers = {"Idempotency-Key": key} if key is not None else {}
    return client.post("/tasks", json=body, headers=headers)


# --- Creación ---------------------------------------------------------------


def test_ca01_creacion_minima_devuelve_201_con_valores_por_defecto(client: TestClient) -> None:
    body = {"title": "Revisar backups"}

    response = _post(client, body)

    assert response.status_code == 201
    task = response.json()
    assert task["id"] == 1
    assert task["status"] == "pending"
    assert task["priority"] == 3
    assert task["description"] is None
    assert task["due_date"] is None
    assert task["assignee_id"] is None
    created_at = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
    assert created_at.utcoffset() == timedelta(0)


def test_ca02_creacion_completa_devuelve_los_valores_enviados(client: TestClient) -> None:
    body = {
        "title": "Rotar certificados",
        "description": "Servidores web",
        "priority": 5,
        "due_date": "2026-12-31",
        "assignee_id": 2,
    }

    response = _post(client, body)

    assert response.status_code == 201
    task = response.json()
    assert {field: task[field] for field in body} == body


def test_ca03_ignora_campos_del_servidor_y_desconocidos(client: TestClient) -> None:
    body = {
        "title": "Tarea x",
        "id": 99,
        "status": "done",
        "created_at": "2000-01-01T00:00:00Z",
        "foo": 1,
    }

    response = _post(client, body)

    assert response.status_code == 201
    task = response.json()
    assert task["id"] == 1
    assert task["status"] == "pending"
    assert not task["created_at"].startswith("2000-01-01")
    assert "foo" not in task


# --- title ------------------------------------------------------------------


def test_ca04_titulo_se_recorta(client: TestClient) -> None:
    body = {"title": "  Revisar backups  "}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["title"] == "Revisar backups"


@pytest.mark.parametrize("title", ["abc", "  abc  ", "a" * 120])
def test_ca05_titulo_en_los_limites_3_y_120_devuelve_201(client: TestClient, title: str) -> None:
    body = {"title": title}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["title"] == title.strip()


@pytest.mark.parametrize("title", ["ab", "  ab  ", "   ", ""])
def test_ca06_titulo_corto_o_vacio_devuelve_422(client: TestClient, title: str) -> None:
    body = {"title": title}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("title", ["a" * 121, "  " + "a" * 121 + "  "])
def test_ca07_titulo_de_121_caracteres_devuelve_422(client: TestClient, title: str) -> None:
    body = {"title": title}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize(
    "body",
    [{"description": "sin título"}, {"title": 123}, {"title": None}],
    ids=["ausente", "numero", "null"],
)
def test_ca08_titulo_ausente_o_no_texto_devuelve_422(client: TestClient, body: dict) -> None:
    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# --- description ------------------------------------------------------------


@pytest.mark.parametrize("description", ["  con espacios  ", ""])
def test_ca09_descripcion_se_guarda_tal_cual(client: TestClient, description: str) -> None:
    body = {"title": "Revisar backups", "description": description}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["description"] == description


@pytest.mark.parametrize(
    "body",
    [{"title": "Revisar backups"}, {"title": "Revisar backups", "description": None}],
    ids=["omitida", "null"],
)
def test_ca10_descripcion_omitida_o_null_se_guarda_null(client: TestClient, body: dict) -> None:
    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize(
    ("description", "expected_status"),
    [("a" * 1000, 201), ("a" * 1001, 422), (" " + "a" * 999 + " ", 422)],
    ids=["1000", "1001", "999_con_espacios"],
)
def test_ca11_descripcion_maximo_1000_sobre_el_valor_recibido(
    client: TestClient, description: str, expected_status: int
) -> None:
    body = {"title": "Revisar backups", "description": description}

    response = _post(client, body)

    assert response.status_code == expected_status
    if expected_status == 201:
        assert response.json()["description"] == description
    else:
        assert isinstance(response.json()["detail"], list)


# --- priority ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("extra", "expected_priority"),
    [({}, 3), ({"priority": 1}, 1), ({"priority": 5}, 5)],
    ids=["por_defecto", "1", "5"],
)
def test_ca12_prioridad_por_defecto_3_y_limites_1_y_5(
    client: TestClient, extra: dict, expected_priority: int
) -> None:
    body = {"title": "Revisar backups", **extra}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["priority"] == expected_priority


@pytest.mark.parametrize("priority", [0, 6])
def test_ca13_prioridad_fuera_de_rango_devuelve_422(client: TestClient, priority: int) -> None:
    body = {"title": "Revisar backups", "priority": priority}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("priority", [3.0, 3.5, "3", "alta", True, None])
def test_ca14_prioridad_no_entera_estricta_devuelve_422(client: TestClient, priority) -> None:
    body = {"title": "Revisar backups", "priority": priority}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# --- due_date (hoy = 2026-10-20) --------------------------------------------


@pytest.mark.parametrize(
    "due_date", ["2026-10-20", "2026-10-21", "2030-01-01"], ids=["hoy", "manana", "futura"]
)
def test_ca15_fecha_limite_hoy_o_futura_devuelve_201(client: TestClient, due_date: str) -> None:
    body = {"title": "Revisar backups", "due_date": due_date}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["due_date"] == due_date


def test_ca16_fecha_limite_ayer_devuelve_422_con_detalle_en_texto(client: TestClient) -> None:
    body = {"title": "Revisar backups", "due_date": "2026-10-19"}

    response = _post(client, body)

    assert response.status_code == 422
    assert "anterior a hoy" in response.json()["detail"]


@pytest.mark.parametrize(
    "due_date", ["20/10/2026", "2026-10-20T10:00:00", "2026-10-20T00:00:00", "2026-02-30"]
)
def test_ca17_fecha_limite_con_formato_o_fecha_invalidos_devuelve_422(
    client: TestClient, due_date: str
) -> None:
    body = {"title": "Revisar backups", "due_date": due_date}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_regresion_fecha_limite_con_hora_a_medianoche_devuelve_422(client: TestClient) -> None:
    # CA-17: Pydantic convierte un datetime a las 00:00:00 en date; aun así no es YYYY-MM-DD.
    body = {"title": "Revisar backups", "due_date": "2026-10-20T00:00:00"}

    response = _post(client, body)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "due_date"]
    assert client.get("/tasks").json() == []


@pytest.mark.parametrize(
    ("body", "error_type"),
    [
        ({"title": "ab"}, "string_too_short"),
        ({"title": "a" * 121}, "string_too_long"),
        ({"title": "Revisar backups", "due_date": "20/10/2026"}, "date_type"),
        ({"title": "Revisar backups", "due_date": "2026-10-20T00:00:00"}, "date_type"),
    ],
    ids=["titulo_corto", "titulo_largo", "fecha_formato", "fecha_con_hora"],
)
def test_regresion_decision_1_errores_de_forma_con_mensaje_de_pydantic_por_defecto(
    client: TestClient, body: dict, error_type: str
) -> None:
    # Decisión 1: sin mensaje propio en español para los errores de forma.
    response = _post(client, body)

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == error_type
    assert not error["msg"].startswith("Value error")


@pytest.mark.parametrize(
    "body",
    [{"title": "Revisar backups"}, {"title": "Revisar backups", "due_date": None}],
    ids=["omitida", "null"],
)
def test_ca18_fecha_limite_omitida_o_null_se_guarda_null(client: TestClient, body: dict) -> None:
    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["due_date"] is None


def test_ca19_la_referencia_es_el_reloj_del_servidor(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("core.clock.today", lambda: date(2026, 10, 21))
    body = {"title": "Revisar backups", "due_date": "2026-10-20"}

    response = _post(client, body)

    assert response.status_code == 422
    assert "anterior a hoy" in response.json()["detail"]


# --- assignee_id ------------------------------------------------------------


def test_ca20_responsable_existente_devuelve_201(client: TestClient) -> None:
    body = {"title": "Revisar backups", "assignee_id": 1}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["assignee_id"] == 1


def test_ca21_responsable_inexistente_devuelve_404(client: TestClient) -> None:
    body = {"title": "Revisar backups", "assignee_id": 999}

    response = _post(client, body)

    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"]


@pytest.mark.parametrize("assignee_id", [0, -1, "1", 1.0, True])
def test_ca22_responsable_con_forma_invalida_devuelve_422(client: TestClient, assignee_id) -> None:
    body = {"title": "Revisar backups", "assignee_id": assignee_id}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_ca23_responsable_null_explicito_queda_sin_responsable(client: TestClient) -> None:
    body = {"title": "Revisar backups", "assignee_id": None}

    response = _post(client, body)

    assert response.status_code == 201
    assert response.json()["assignee_id"] is None


# --- Varios errores a la vez ------------------------------------------------


def test_ca24_la_forma_gana_al_responsable_inexistente(client: TestClient) -> None:
    body = {"title": "ab", "assignee_id": 999}

    response = _post(client, body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_ca25_la_fecha_pasada_gana_al_responsable_inexistente(client: TestClient) -> None:
    body = {"title": "Revisar backups", "due_date": "2026-10-19", "assignee_id": 999}

    response = _post(client, body)

    assert response.status_code == 422
    assert "anterior a hoy" in response.json()["detail"]


# --- Idempotencia -----------------------------------------------------------


def test_ca26_misma_clave_y_mismo_cuerpo_devuelve_200_con_la_misma_tarea(
    client: TestClient,
) -> None:
    body = {"title": "Revisar backups", "assignee_id": 1}
    first = _post(client, body, key="K")

    repeated = _post(client, body, key="K")

    assert first.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    assert len(client.get("/tasks").json()) == 1


def test_ca27_la_huella_se_calcula_sobre_el_cuerpo_normalizado(client: TestClient) -> None:
    first = _post(client, {"title": "Revisar"}, key="K")

    repeated = _post(client, {"priority": 3, "title": " Revisar "}, key="K")

    assert first.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["created_at"] == first.json()["created_at"]


def test_ca28_misma_clave_y_cuerpo_distinto_devuelve_409(client: TestClient) -> None:
    first = _post(client, {"title": "Revisar"}, key="K")

    response = _post(client, {"title": "Otra tarea"}, key="K")

    assert first.status_code == 201
    assert response.status_code == 409
    assert "ya existe" in response.json()["detail"]
    assert len(client.get("/tasks").json()) == 1


@pytest.mark.parametrize(
    ("failing_body", "failing_status"),
    [({"title": "Revisar", "assignee_id": 999}, 404), ({"title": "ab"}, 422)],
    ids=["tras_404", "tras_422"],
)
def test_ca29_un_fallo_no_guarda_la_clave(
    client: TestClient, failing_body: dict, failing_status: int
) -> None:
    first = _post(client, failing_body, key="K")

    response = _post(client, {"title": "Revisar backups"}, key="K")

    assert first.status_code == failing_status
    assert response.status_code == 201
    assert response.json()["title"] == "Revisar backups"


def test_ca30_cuerpo_invalido_con_clave_usada_devuelve_422(client: TestClient) -> None:
    first = _post(client, {"title": "Revisar"}, key="K")

    response = _post(client, {"title": "ab"}, key="K")

    assert first.status_code == 201
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_ca31_la_clave_distingue_mayusculas(client: TestClient) -> None:
    body = {"title": "Revisar backups"}
    first = _post(client, body, key="abc")

    response = _post(client, body, key="ABC")

    assert first.status_code == 201
    assert response.status_code == 201
    assert response.json()["id"] != first.json()["id"]


@pytest.mark.parametrize(
    ("key", "expected_status"),
    [("k", 201), ("k" * 64, 201), ("", 422), ("k" * 65, 422)],
    ids=["1", "64", "vacia", "65"],
)
def test_ca32_longitud_de_la_clave_entre_1_y_64(
    client: TestClient, key: str, expected_status: int
) -> None:
    body = {"title": "Revisar backups"}

    response = _post(client, body, key=key)

    assert response.status_code == expected_status
    if expected_status == 201:
        assert response.json()["title"] == "Revisar backups"
    else:
        assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize(
    ("key", "expected_status"),
    [("ñ" * 64, 201), ("ñ" * 65, 422)],
    ids=["64_no_ascii", "65_no_ascii"],
)
def test_regresion_decision_10_la_clave_se_cuenta_en_caracteres_no_en_bytes(
    client: TestClient, key: str, expected_status: int
) -> None:
    # "ñ" ocupa 2 bytes en UTF-8: contada en bytes, la clave de 64 caracteres daría 422.
    headers = {"Idempotency-Key": key.encode("utf-8")}

    response = client.post("/tasks", json={"title": "Revisar backups"}, headers=headers)

    assert response.status_code == expected_status
    if expected_status == 201:
        repeated = client.post("/tasks", json={"title": "Revisar backups"}, headers=headers)
        assert repeated.status_code == 200
        assert repeated.json() == response.json()


def test_ca33_sin_clave_no_hay_deduplicacion(client: TestClient) -> None:
    body = {"title": "Revisar backups"}
    first = _post(client, body)

    second = _post(client, body)

    assert first.status_code == 201
    assert second.status_code == 201
    assert [first.json()["id"], second.json()["id"]] == [1, 2]


# --- Listado y consulta -----------------------------------------------------


def test_ca34_listado_vacio_devuelve_lista_vacia(client: TestClient) -> None:
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_ca35_listado_completo_ordenado_por_id(client: TestClient) -> None:
    for title in ["Tarea uno", "Tarea dos", "Tarea tres"]:
        _post(client, {"title": title})

    response = client.get("/tasks")

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [1, 2, 3]


def test_ca36_filtro_por_responsable_devuelve_solo_sus_tareas(client: TestClient) -> None:
    for assignee_id in [1, 2, 1, None]:
        _post(client, {"title": "Revisar backups", "assignee_id": assignee_id})

    response = client.get("/tasks", params={"assignee_id": 1})

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [1, 3]


@pytest.mark.parametrize("assignee_id", [999, 0, -1])
def test_ca37_filtro_sin_coincidencias_devuelve_lista_vacia(
    client: TestClient, assignee_id: int
) -> None:
    _post(client, {"title": "Revisar backups", "assignee_id": 1})
    _post(client, {"title": "Rotar certificados"})

    response = client.get("/tasks", params={"assignee_id": assignee_id})

    assert response.status_code == 200
    assert response.json() == []


def test_ca38_filtro_no_entero_devuelve_422(client: TestClient) -> None:
    response = client.get("/tasks", params={"assignee_id": "abc"})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_ca39_consultar_tarea_existente_devuelve_la_misma_tarea(client: TestClient) -> None:
    created = _post(client, {"title": "Revisar backups", "priority": 2}).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize("task_id", [999, 0, -1])
def test_ca40_consultar_tarea_inexistente_devuelve_404(client: TestClient, task_id: int) -> None:
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"]


def test_ca41_task_id_no_entero_devuelve_422(client: TestClient) -> None:
    response = client.get("/tasks/abc")

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# --- Aislamiento y errores --------------------------------------------------


def test_ca42_reset_limpia_tareas_y_claves(client: TestClient) -> None:
    _post(client, {"title": "Revisar"}, key="K")

    tasks_repository.reset()

    assert client.get("/tasks").json() == []
    response = _post(client, {"title": "Otra tarea"}, key="K")
    assert response.status_code == 201
    assert response.json()["id"] == 1


def test_ca43_errores_de_dominio_en_texto_y_de_forma_en_lista(client: TestClient) -> None:
    _post(client, {"title": "Revisar"}, key="K")

    past_date = _post(client, {"title": "Revisar backups", "due_date": "2026-10-19"})
    missing_assignee = _post(client, {"title": "Revisar backups", "assignee_id": 999})
    conflict = _post(client, {"title": "Otra tarea"}, key="K")
    missing_task = client.get("/tasks/999")
    shape_error = _post(client, {"title": "ab"})

    assert past_date.status_code == 422
    assert isinstance(past_date.json()["detail"], str)
    assert missing_assignee.status_code == 404
    assert isinstance(missing_assignee.json()["detail"], str)
    assert conflict.status_code == 409
    assert isinstance(conflict.json()["detail"], str)
    assert missing_task.status_code == 404
    assert "no encontrado" in missing_task.json()["detail"]
    assert shape_error.status_code == 422
    assert isinstance(shape_error.json()["detail"], list)


# --- Service (tests unitarios, sin TestClient) ------------------------------


def _create_tasks_for(assignee_ids: list[int | None]) -> None:
    for position, assignee_id in enumerate(assignee_ids, start=1):
        service.create_task(TaskCreate(title=f"Tarea {position}", assignee_id=assignee_id), None)


class TestService:
    """`tasks/service.py` con `users.service.get_user` sustituido por un fake."""

    @pytest.fixture(autouse=True)
    def user_lookups(self, monkeypatch: pytest.MonkeyPatch) -> list[int]:
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

    def test_crear_tarea_valida_queda_pendiente_con_los_valores_recibidos(self) -> None:
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

    def test_crear_dos_tareas_asigna_ids_incrementales(self) -> None:
        # Arrange
        data = TaskCreate(title="Revisar backups")

        # Act
        first, first_created = service.create_task(data, idempotency_key=None)
        second, second_created = service.create_task(data, idempotency_key=None)

        # Assert
        assert (first.id, second.id) == (1, 2)
        assert (first_created, second_created) == (True, True)
        assert tasks_repository.list_all() == [first, second]

    def test_crear_con_responsable_existente_consulta_ese_usuario(
        self, user_lookups: list[int]
    ) -> None:
        # Arrange
        data = TaskCreate(title="Revisar backups", assignee_id=2)

        # Act
        task, created = service.create_task(data, idempotency_key=None)

        # Assert
        assert created is True
        assert task.assignee_id == 2
        assert user_lookups == [2]

    # --- create_task: due_date --------------------------------------------------

    def test_fecha_limite_ayer_da_422_y_no_crea_la_tarea(self) -> None:
        # Arrange
        data = TaskCreate(title="Tarea atrasada", due_date=TODAY - timedelta(days=1))

        # Act
        with pytest.raises(HTTPException) as error:
            service.create_task(data, idempotency_key=None)

        # Assert
        assert error.value.status_code == 422
        assert error.value.detail == service.PAST_DUE_DATE_MESSAGE
        assert tasks_repository.list_all() == []

    def test_fecha_limite_hoy_es_valida(self) -> None:
        # Detecta `<` → `<=` en la comparación con hoy.
        # Arrange
        data = TaskCreate(title="Tarea de hoy", due_date=TODAY)

        # Act
        task, created = service.create_task(data, idempotency_key=None)

        # Assert
        assert created is True
        assert task.due_date == TODAY
        assert tasks_repository.list_all() == [task]

    def test_fecha_limite_none_es_valida(self) -> None:
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

    def test_responsable_inexistente_da_404_y_no_crea_la_tarea(
        self, user_lookups: list[int]
    ) -> None:
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

    def test_responsable_none_no_consulta_usuarios(self, user_lookups: list[int]) -> None:
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

    def test_misma_clave_y_mismo_cuerpo_devuelve_la_tarea_original(self) -> None:
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

    def test_misma_clave_y_otro_cuerpo_da_409(self) -> None:
        # Arrange
        service.create_task(TaskCreate(title="Revisar backups"), idempotency_key=KEY)

        # Act
        with pytest.raises(HTTPException) as error:
            service.create_task(TaskCreate(title="Otra tarea"), idempotency_key=KEY)

        # Assert
        assert error.value.status_code == 409
        assert error.value.detail == f"clave de idempotencia ya existe: {KEY}"
        assert len(tasks_repository.list_all()) == 1

    def test_claves_distintas_crean_dos_tareas(self) -> None:
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
    def test_misma_clave_cambiando_un_solo_campo_da_409(self, changed_field: dict) -> None:
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
        self,
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

    def test_un_404_previo_no_reserva_la_clave(self) -> None:
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

    def test_description_none_y_omitida_tienen_la_misma_huella(self) -> None:
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

    def test_obtener_tarea_existente_la_devuelve(self) -> None:
        # Arrange
        created_task, _ = service.create_task(TaskCreate(title="Revisar backups"), None)

        # Act
        task = service.get_task(created_task.id)

        # Assert
        assert task == created_task
        assert task.id == 1
        assert task.title == "Revisar backups"

    def test_obtener_tarea_inexistente_da_404(self) -> None:
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

    def test_listar_sin_filtro_devuelve_todas_en_orden_de_id(self) -> None:
        # Arrange
        _create_tasks_for([1, 2, None])

        # Act
        tasks = service.list_tasks(assignee_id=None)

        # Assert
        assert [task.id for task in tasks] == [1, 2, 3]
        assert [task.title for task in tasks] == ["Tarea 1", "Tarea 2", "Tarea 3"]
        assert [task.assignee_id for task in tasks] == [1, 2, None]

    def test_listar_con_filtro_devuelve_solo_las_del_responsable(self) -> None:
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
        self,
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


# --- Integración con `users` (sin mocks salvo el reloj) ---------------------


def test_flujo_alta_de_usuario_y_tareas_con_idempotencia_y_filtro(client: TestClient) -> None:
    # 1. Estado inicial: usuarios semilla y ninguna tarea.
    users = client.get("/users").json()
    assert [user["id"] for user in users] == SEED_USER_IDS
    assert users[0]["name"] == "Ada Lovelace"
    assert client.get("/tasks").json() == []

    # 2. Alta de Margaret por la API de users.
    response = client.post(
        "/users", json={"name": "Margaret Hamilton", "email": "margaret@example.com"}
    )
    assert response.status_code == 201
    margaret_id = response.json()["id"]
    assert margaret_id == 5

    # 3. Tarea para Margaret con Idempotency-Key "k-1" (vence hoy: válida con el reloj fijado).
    body = {"title": "Revisar guiado", "due_date": "2026-10-20", "assignee_id": margaret_id}
    response = client.post("/tasks", json=body, headers={"Idempotency-Key": "k-1"})
    assert response.status_code == 201
    margaret_task = response.json()
    assert margaret_task["assignee_id"] == margaret_id
    assert margaret_task["status"] == "pending"

    # 4. Repetición con la misma clave: 200 y la misma tarea.
    response = client.post("/tasks", json=body, headers={"Idempotency-Key": "k-1"})
    assert response.status_code == 200
    assert response.json() == margaret_task

    # 5. Tarea para Ada sin clave.
    response = client.post("/tasks", json={"title": "Revisar backups", "assignee_id": 1})
    assert response.status_code == 201
    assert response.json()["id"] == margaret_task["id"] + 1

    # 6. El filtro por Margaret devuelve solo su tarea.
    response = client.get("/tasks", params={"assignee_id": margaret_id})
    assert response.status_code == 200
    assert response.json() == [margaret_task]

    # 7. La consulta por id coincide con lo creado.
    response = client.get(f"/tasks/{margaret_task['id']}")
    assert response.status_code == 200
    assert response.json() == margaret_task


def test_no_queda_estado_de_otro_test(client: TestClient) -> None:
    # Se ejecuta después del flujo anterior: si el teardown fallara, aquí quedarían
    # Margaret, sus tareas o la clave "k-1".
    assert client.get("/tasks").json() == []
    assert [user["id"] for user in client.get("/users").json()] == SEED_USER_IDS

    response = client.post(
        "/tasks", json={"title": "Otro cuerpo"}, headers={"Idempotency-Key": "k-1"}
    )

    assert response.status_code == 201
    assert response.json()["id"] == 1


# --- Reloj (`core/clock.py`, con el today() real) --------------------------


def test_hoy_es_la_fecha_utc_del_ultimo_segundo_del_dia(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: en UTC+2 este instante ya sería el día 21.
    instant = datetime(2026, 10, 20, 23, 59, 59, tzinfo=timezone.utc)
    monkeypatch.setattr("core.clock.now", lambda: instant)

    # Act
    today = _real_today()

    # Assert
    assert today == date(2026, 10, 20)


def test_hoy_cambia_a_medianoche_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    instant = datetime(2026, 10, 21, 0, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("core.clock.now", lambda: instant)

    # Act
    today = _real_today()

    # Assert
    assert today == date(2026, 10, 21)
