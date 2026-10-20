"""Tests de `core/clock.py`.

Decisión 4 de `docs/feature-tasks.md`: "hoy" es la fecha UTC del servidor, aunque el
cliente esté en otra zona horaria. Se fija solo `core.clock.now` (la hora del sistema)
y se ejecuta el `today()` real.
"""
from datetime import date, datetime, timezone

import pytest

from core import clock


def test_hoy_es_la_fecha_utc_del_ultimo_segundo_del_dia(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: en UTC+2 este instante ya sería el día 21.
    instant = datetime(2026, 10, 20, 23, 59, 59, tzinfo=timezone.utc)
    monkeypatch.setattr("core.clock.now", lambda: instant)

    # Act
    today = clock.today()

    # Assert
    assert today == date(2026, 10, 20)


def test_hoy_cambia_a_medianoche_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    instant = datetime(2026, 10, 21, 0, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("core.clock.now", lambda: instant)

    # Act
    today = clock.today()

    # Assert
    assert today == date(2026, 10, 21)
