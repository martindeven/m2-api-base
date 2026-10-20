"""Tests del recurso `tasks`.

Escritos a partir de los criterios de aceptación de `docs/feature-tasks.md`: un test
por criterio CA-XX. Mismo estilo que `test_users.py`:
  - arrange / act / assert separados por una línea en blanco
  - se comprueba el status code y el campo del cuerpo que demuestra el criterio
  - "hoy" está fijado en 2026-10-20 (UTC) con monkeypatch sobre `core.clock.today`
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tasks import repository as tasks_repository

TODAY = date(2026, 10, 20)


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
