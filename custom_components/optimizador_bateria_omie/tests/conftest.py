"""Fixtures para tests del componente optimizador_bateria_omie."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.optimizador_bateria_omie.cliente_omie import (
    ClienteOmie,
    ConfiguracionOmie,
)


@pytest.fixture
def cliente_omie(tmp_path):
    """Fixture para ClienteOmie con configuración mock."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.components = ["omie"]
    hass.config.config_dir = str(tmp_path)
    hass.services = MagicMock()
    hass.states = MagicMock()

    # async_add_executor_job ejecuta la función síncrona directamente
    # en los tests (no hay event loop real que bloquear).
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda fn, *args: fn(*args)
    )

    config = ConfiguracionOmie(
        fuente_prioritaria="omie",
        usar_cache=True,
        dias_cache=7,
    )

    cliente = ClienteOmie(hass, config)
    return cliente


@pytest.fixture
def fixture_respuesta_integracion_omie():
    """Fixture para respuesta de la integración OMIE (96 tramos normales)."""
    hoy = datetime.now(tz=UTC).date()
    respuesta = []
    for h in range(24):
        for m in [0, 15, 30, 45]:
            respuesta.append(
                {
                    "date": hoy.strftime("%Y-%m-%d"),
                    "hour": h,
                    "minute": m,
                    "price": 0.10 + h * 0.01 + (m // 15) * 0.0025,
                }
            )
    return respuesta


@pytest.fixture
def fixture_respuesta_redata():
    """Fixture para respuesta de REData API."""
    hoy = datetime.now(tz=UTC).date()
    return {
        "data": [
            {
                "datetime": f"{hoy.strftime('%Y-%m-%d')}T{h:02d}:{m:02d}:00+01:00",
                "price": 0.12 + h * 0.008 + (m // 15) * 0.0015,
            }
            for h in range(24)
            for m in [0, 15, 30, 45]
        ]
    }


@pytest.fixture
def fixture_respuesta_integracion_omie_horario():
    """Fixture para respuesta de OMIE en día con cambio horario (92 tramos)."""
    # 30 de marzo 2025 - día con 92 tramos por cambio horario
    respuesta = []
    for h in range(24):
        for m in [0, 15, 30, 45]:
            # Simular solo 92 tramos (23 horas * 4 = 92)
            if h >= 23:
                continue
            respuesta.append(
                {
                    "date": "2025-03-30",
                    "hour": h,
                    "minute": m,
                    "price": 0.11 + h * 0.009 + (m // 15) * 0.002,
                }
            )
    return respuesta
