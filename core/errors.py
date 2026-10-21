"""Catálogo de errores de la API.

Todas las rutas deben levantar errores a través de estas funciones, para que los
códigos de estado y el formato de la respuesta sean consistentes en todo el
proyecto. No usar `HTTPException` directamente en las rutas.
"""
from fastapi import HTTPException, status


def not_found(resource: str, identifier: object) -> HTTPException:
    """404 — el recurso pedido no existe."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} no encontrado: {identifier}",
    )


def invalid_request(message: str) -> HTTPException:
    """422 — la petición llegó bien formada pero no es válida a nivel de dominio."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=message,
    )


def already_exists(resource: str, identifier: object) -> HTTPException:
    """409 — el recurso que se quiere crear ya existe."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"{resource} ya existe: {identifier}",
    )
