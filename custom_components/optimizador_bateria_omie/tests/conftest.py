"""Fixtures para tests del componente optimizador_bateria_omie."""

from unittest.mock import MagicMock

import pytest
from custom_components.optimizador_bateria_omie.cliente_omie import (
    ClienteOmie,
    ConfiguracionOmie,
)


@pytest.fixture
def cliente_omie():
    """Fixture para ClienteOmie con configuración mock."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.components = ["omie"]
    hass.services = MagicMock()
    hass.services.async_call = MagicMock()

    config = ConfiguracionOmie(
        fuente_prioritaria="omie",
        usar_cache=True,
        dias_cache=7,
    )

    return ClienteOmie(hass, config)


@pytest.fixture
def fixture_respuesta_integracion_omie():
    """Fixture para respuesta de la integración OMIE (96 tramos normales)."""
    from datetime import datetime, timezone

    hoy = datetime.now(tz=timezone.utc).date()
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
    from datetime import datetime, timezone

    hoy = datetime.now(tz=timezone.utc).date()
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
