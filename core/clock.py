"""Reloj de la aplicación.

Único punto del proyecto que consulta la fecha del sistema. La lógica que depende
de "hoy" llama a estas funciones para poder mockearlas en los tests.
"""
from datetime import date, datetime, timezone


def now() -> datetime:
    """Fecha y hora actuales en UTC."""
    return datetime.now(timezone.utc)


def today() -> date:
    """Fecha actual en UTC."""
    return now().date()
