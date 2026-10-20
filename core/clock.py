"""Reloj de la aplicación.

Único punto del proyecto que consulta la fecha del sistema. La lógica que depende
de "hoy" llama a estas funciones para poder mockearlas en los tests.
"""
from datetime import date


def today() -> date:
    """Fecha actual en UTC."""
    # TODO(CA-15, CA-19): devolver la fecha UTC del servidor (no la local).
    raise NotImplementedError
