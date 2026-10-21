"""Reloj de la aplicación.

Único punto del proyecto que consulta la fecha del sistema. La lógica que depende
de "hoy" llama a estas funciones para poder mockearlas en los tests.
"""
from datetime import date, datetime, timezone


def now() -> datetime:
    """Devuelve la fecha y hora actuales del sistema en UTC.

    Es la única llamada del proyecto a `datetime.now()`. Los repositorios la usan
    para `created_at`.

    Returns:
        Un `datetime` con zona horaria UTC (`tzinfo=timezone.utc`).
    """
    return datetime.now(timezone.utc)


def today() -> date:
    """Devuelve la fecha actual en UTC, la referencia de "hoy" para `due_date`.

    Es la fecha UTC del servidor aunque el cliente esté en otra zona horaria. Por
    ejemplo, a las 23:59:59 UTC del día 20 sigue siendo el 20, aunque en UTC+2 ya sea
    el 21. Se calcula a partir de `now()`, así que fijar `now()` en un test también
    fija `today()`.

    Returns:
        La fecha (`date`) de `now()`.
    """
    return now().date()
