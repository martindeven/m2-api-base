# m2-api-base

API REST de ejemplo (FastAPI + Pydantic v2) usada como base en el **Módulo 2 · Clase 1 —
Generación de código con IA**.

Es un proyecto pequeño pero completo: tiene convenciones, capas separadas, catálogo
de errores y una suite de tests que pasa. El almacén es en memoria, así que corre sin
base de datos ni otra infraestructura. Tiene dos recursos:

- **`users`**: el recurso de ejemplo, con 4 usuarios semilla (ids 1–4).
- **`tasks`**: registro de tareas de equipo con responsable, prioridad y fecha límite. Su
  objetivo es la **trazabilidad**: que ningún trabajo del equipo de operaciones quede sin
  registrar y que se pueda rastrear quién tiene asignada cada tarea. La creación es
  idempotente opcionalmente con la cabecera `Idempotency-Key`, para que un reintento no
  duplique tareas. Especificación completa: [`docs/feature-tasks.md`](docs/feature-tasks.md).

## Requisitos

- Python 3.10 o superior (`requires-python = ">=3.10"` en `pyproject.toml`)
- (Recomendado) Claude Code instalado

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` incluye la app (FastAPI, uvicorn, Pydantic, email-validator) y las
herramientas de desarrollo (pytest, pytest-cov, httpx, ruff, mutmut).

## Arranque

```bash
uvicorn main:app --reload          # http://127.0.0.1:8000  ·  Swagger en /docs
```

Los datos viven en memoria: al reiniciar la app, `users` vuelve a los 4 usuarios semilla y
`tasks` queda vacío.

## Endpoints

| Método | Ruta               | Descripción | Códigos |
|--------|--------------------|-------------|---------|
| GET    | `/health`          | Estado del servicio | 200 |
| GET    | `/users`           | Lista de usuarios | 200 |
| GET    | `/users/{id}`      | Un usuario por id | 200 · 404 si no existe · 422 si el id no es entero |
| POST   | `/users`           | Crea un usuario | 201 · 409 si el email ya existe · 422 si el cuerpo es inválido |
| GET    | `/tasks`           | Lista de tareas por `id` ascendente; filtro opcional `?assignee_id=<id>` | 200 (`[]` si no hay coincidencias) · 422 si `assignee_id` no es entero |
| GET    | `/tasks/{id}`      | Una tarea por id | 200 · 404 si no existe (también `0` y negativos) · 422 si el id no es entero |
| POST   | `/tasks`           | Crea una tarea, con `Idempotency-Key` opcional | 201 creada · 200 repetición con la misma clave y el mismo cuerpo · 404 responsable inexistente · 409 misma clave con otro cuerpo · 422 cuerpo/cabecera inválidos o `due_date` pasada |

Los errores de dominio (404, 409 y el 422 por fecha pasada) devuelven `{"detail": "<texto en
español>"}`. Los 422 de forma usan el formato de Pydantic, con `detail` como lista. Reglas
completas y orden de evaluación: [`docs/feature-tasks.md`](docs/feature-tasks.md).

## Uso de `tasks`

Con la app arrancada (`uvicorn main:app --reload`) y el almacén de tareas vacío, ejecuta estos
ejemplos en orden.

Crear una tarea: **201**. El título se guarda recortado y `id`, `status` y `created_at` los
pone el servidor.

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "  Revisar backups  ", "priority": 2, "due_date": "2030-12-31", "assignee_id": 1}'
```

Crear con clave de idempotencia: **201** la primera vez. Repetir **el mismo comando**
devuelve **200** con la misma tarea (mismo `id` y `created_at`) y no crea otra.

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alta-backup-001" \
  -d '{"title": "Rotar certificados", "assignee_id": 2}'
```

La misma clave con otro cuerpo da **409** (`"clave de idempotencia ya existe: alta-backup-001"`):

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alta-backup-001" \
  -d '{"title": "Otra tarea distinta"}'
```

Validación: **422**. Un título demasiado corto es un error de forma y devuelve `detail` en
lista:

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "ab"}'
```

Una fecha límite anterior a hoy (UTC) es un error de dominio y devuelve `detail` de texto:

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Tarea atrasada", "due_date": "2020-01-01"}'
```

Un responsable inexistente da **404**:

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Tarea huérfana", "assignee_id": 999}'
```

Listar todas, filtrar por responsable y consultar una tarea:

```bash
curl -i http://127.0.0.1:8000/tasks
curl -i "http://127.0.0.1:8000/tasks?assignee_id=1"
curl -i http://127.0.0.1:8000/tasks/1
```

## Tests y calidad

```bash
pytest                                                  # suite completa (addopts = "-q")
pytest --cov --cov-branch --cov-report=term-missing     # cobertura de líneas y ramas
pytest --cov=tasks --cov-branch                         # cobertura de tasks/ (definición de hecho)
ruff check .                                            # linter
mutmut run                                              # mutation testing de tasks/ y core/clock.py
mutmut results                                          # mutantes supervivientes
```

- **Umbral de cobertura:** `pyproject.toml` fija `fail_under = 90`, así que cualquier
  ejecución con `--cov` falla si la cobertura baja del 90 %. La definición de hecho de
  `CLAUDE.md` exige que `tasks/` supere el 90 % con cobertura de ramas.
- **Medición:** cubre `core`, `users`, `tasks` y `main`, con ramas activadas
  (`[tool.coverage.run]`).
- **mutmut:** muta `tasks/` y `core/clock.py` (`[tool.mutmut]`) y deja sus archivos en
  `mutants/`, que está en `.gitignore`. `mutmut results` lista los mutantes que sobreviven.

## Guía rápida para colaboradores

**Estructura por capas.** Cada recurso es un paquete con cuatro archivos y una dirección única
de dependencias: `routes` → `service` → `repository`.

| Archivo | Responsabilidad |
|---------|-----------------|
| `routes.py` | Rutas HTTP con `response_model=`. Sin lógica: delega en `service.py`. |
| `service.py` | Reglas de dominio y decisiones de error con `core/errors.py`. Única capa que habla con `repository.py`. |
| `schemas.py` | Modelos Pydantic de entrada (`*Create`) y salida, con las validaciones de forma. |
| `repository.py` | Acceso a datos (aquí, un `dict` en memoria) con `reset()` para los tests. |

Además:
- `core/errors.py` es el catálogo de errores (`not_found`, `invalid_request`, `already_exists`).
- `core/clock.py` es el único punto que consulta la fecha del sistema.
- `main.py` monta los routers.

**Añadir un recurso nuevo usando `tasks/` como plantilla:**

1. Escribe la especificación en `docs/feature-<recurso>.md`, como `docs/feature-tasks.md`.
2. Crea `<recurso>/` con `__init__.py`, `routes.py`, `service.py`, `schemas.py` y
   `repository.py`, copiando la estructura de `tasks/`.
3. Usa en `service.py` las funciones de `core/errors.py` y, si depende de la fecha, las de
   `core/clock.py`. Para consultar otro recurso, pasa por su `service.py`, nunca por su
   `repository.py`.
4. Monta el router en `main.py` con `app.include_router(...)`.
5. Llama al `reset()` del repositorio nuevo desde la fixture autouse `_reset_data` de
   `tests/conftest.py`.
6. Añade los tests en `tests/test_<recurso>.py`, con al menos un caso feliz y uno de error por
   endpoint.
7. Si debe contar en la cobertura o en mutmut, añádelo a `source` en `[tool.coverage.run]` y a
   `source_paths` en `[tool.mutmut]` de `pyproject.toml`.

**Convenciones.** Están en [`CLAUDE.md`](CLAUDE.md): nombres, rutas específicas antes que rutas
con parámetro, docstrings estilo Google en `service.py`, definición de hecho y carpetas fuera de
límites (`migrations/` y `legacy/`). Léelo antes de empezar.

## Documentación

- [`CHANGELOG.md`](CHANGELOG.md): cambios del proyecto.
- [`docs/feature-tasks.md`](docs/feature-tasks.md): especificación del recurso `tasks`, con
  decisiones y criterios de aceptación.
- [`docs/adr/`](docs/adr/): registros de decisiones de arquitectura.
  - [`0001-idempotencia-en-alta-de-tareas.md`](docs/adr/0001-idempotencia-en-alta-de-tareas.md):
    por qué el alta de tareas es idempotente con `Idempotency-Key`.

## Ramas del módulo

`main` es la base de la **Clase 1**. Cada clase tiene su rama de trabajo y su
rama de solución:

| Clase | Rama de trabajo | Solución | Qué añade |
|-------|-----------------|----------|-----------|
| 1 · Generación | `main` | `solucion-clase1` | La base. Falta `GET /users/search`. |
| 2 · Testing | `clase2-testing` | `solucion-clase2` | `users/validation.py` sin tests → llévalo a >80%. |
| 3 · Debugging | `clase3-debugging` | `solucion-clase3` | Recurso `reports/` con 3 bugs plantados. |
| 4 · Review | `clase4-review` | `solucion-clase4` | PR de `GET /reports/export` con issues (verde). |

```bash
git switch clase2-testing     # o la que toque
```

## Tarea del laboratorio (Clase 1)

Añadir `GET /users/search?email=<email>`:

- **200** con el usuario si existe
- **422** si el formato del email es inválido
- **404** si no hay ningún usuario con ese email
- con su test en `tests/test_users.py`, siguiendo el estilo del archivo

Lee `CLAUDE.md` antes de empezar: ahí están las convenciones que tu código debe respetar.
