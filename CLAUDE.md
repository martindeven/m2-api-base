# API de usuarios — guía del proyecto

API REST de ejemplo (FastAPI + Pydantic v2). Almacén en memoria, sin base de datos:
el proyecto corre sin infraestructura.

## Estructura

- `main.py` — crea la app y monta los routers.
- `users/` — recurso de ejemplo. Cada recurso sigue el mismo patrón:
  - `routes.py` — rutas HTTP. Sin lógica de negocio: delega en `service.py`.
  - `service.py` — lógica de negocio. Única capa que habla con `repository.py`.
  - `schemas.py` — modelos Pydantic de entrada (`*Create`) y salida.
  - `repository.py` — acceso a datos (aquí, un `dict` en memoria).
- `tasks/` — tareas de equipo. Mismo patrón de 4 archivos que `users/`
  (`routes.py`, `service.py`, `schemas.py`, `repository.py`).
- `core/errors.py` — catálogo de errores. Toda respuesta de error sale de aquí.
- `core/clock.py` — reloj de la aplicación (fecha actual en UTC). Único punto que consulta
  la fecha del sistema.
- `docs/` — especificaciones de features (`feature-<recurso>.md`) y ADR.
- `tests/` — un archivo por recurso: `test_<recurso>.py` (`test_users.py`, `test_tasks.py`).

## Convenciones

- Las rutas declaran `response_model=` y devuelven modelos Pydantic, nunca `dict` crudos.
- Los errores se levantan con las funciones de `core/errors.py`
  (`not_found`, `invalid_request`, `already_exists`), no con `HTTPException` a mano.
- La ruta delega en `service.py`; la lógica y las decisiones de error viven ahí.
- Identificadores en inglés y `snake_case`, sin abreviaturas. Mensajes de error en español.
- Cada endpoint nuevo lleva su test en el archivo del recurso, con al menos un caso
  feliz y un caso de error.
- Rutas específicas antes que rutas con parámetro: `/users/search` debe declararse
  **antes** de `/users/{user_id}`.
- La lógica que depende de la fecha actual no llama a `date.today()` ni a `datetime.now()`
  directamente: usa una función de `core/clock.py` para poder mockearla en los tests.
- Las validaciones de forma (tipos, rangos, longitudes) van en los schemas Pydantic. Las
  reglas de dominio (fecha pasada, responsable inexistente, idempotencia) van en `service.py`
  con `core/errors.py`.
- Un recurso consulta otro recurso a través de su `service.py`, nunca de su `repository.py`.
- Todo repositorio nuevo expone `reset()` y la fixture autouse de `tests/conftest.py` lo invoca.
- Docstrings estilo Google en las funciones públicas de `service.py`.

## Cómo ejecutar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload          # API en http://127.0.0.1:8000  ·  /docs para el Swagger
pytest                             # tests
pytest --cov=. --cov-report=term-missing   # cobertura
pytest --cov --cov-branch --cov-report=term-missing   # cobertura de ramas
ruff check .                       # linter
mutmut run                         # mutation testing
mutmut results                     # mutantes supervivientes
```

## Definición de hecho

Un cambio está hecho cuando:

- `pytest` está en verde.
- La cobertura de `tasks/` supera el 90 % (`pytest --cov=tasks --cov-branch`).
- `ruff check .` está limpio.
- Las funciones públicas de `service.py` tienen docstrings estilo Google.
- `README.md` y `CHANGELOG.md` están actualizados.

## Fuera de límites

- `migrations/` y `legacy/` — no modificar.
