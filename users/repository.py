"""Almacén en memoria del recurso `users`.

Sustituye a una base de datos real para que el proyecto sea ejecutable sin
infraestructura. La API pública de este módulo (las funciones de abajo) imita la
de un repositorio real: la capa de `service.py` no debería notar la diferencia.
"""
from core import clock
from users.schemas import User

_users: dict[int, User] = {}
_next_id: int = 1

_SEED = [
    ("Ada Lovelace", "ada@example.com"),
    ("Alan Turing", "alan@example.com"),
    ("Grace Hopper", "grace@example.com"),
    ("Katherine Johnson", "katherine@example.com"),
]


def add(*, name: str, email: str) -> User:
    global _next_id
    user = User(
        id=_next_id,
        name=name,
        email=email,
        created_at=clock.now(),
    )
    _users[user.id] = user
    _next_id += 1
    return user


def get(user_id: int) -> User | None:
    return _users.get(user_id)


def list_all() -> list[User]:
    return list(_users.values())


def find_by_email(email: str) -> User | None:
    target = email.lower()
    return next((u for u in _users.values() if u.email.lower() == target), None)


def reset() -> None:
    """Deja el almacén con solo los datos semilla. Se usa entre tests."""
    global _next_id
    _users.clear()
    _next_id = 1
    for name, email in _SEED:
        add(name=name, email=email)


reset()
