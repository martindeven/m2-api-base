"""Tests de integración del recurso `tasks` con el recurso `users`.

Usan la app real (`client` de `conftest.py`) y nada mockeado salvo el reloj:
  routes → tasks.service → tasks.repository
                         → users.service → users.repository

Setup / teardown:
  - `_reset_data` (autouse, `conftest.py`) llama a `users_repository.reset()` y
    `tasks_repository.reset()` antes y después de cada test: cada test arranca con los
    4 usuarios semilla (Ada Lovelace es el id 1), sin tareas ni claves de idempotencia,
    y no deja nada para el siguiente.
  - `_fixed_today` (autouse, aquí) fija `core.clock.today` en 2026-10-20 (UTC) con
    monkeypatch, que deshace el cambio al terminar cada test.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

TODAY = date(2026, 10, 20)
SEED_USER_IDS = [1, 2, 3, 4]


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("core.clock.today", lambda: TODAY)


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
