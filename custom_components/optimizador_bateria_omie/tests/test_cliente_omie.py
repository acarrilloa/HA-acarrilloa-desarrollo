"""Tests para ClienteOmie."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.optimizador_bateria_omie.cliente_omie import (
    ErrorFuenteOmie,
)


def _estado_con_precios(precios):
    """Crea un estado mock de HA con atributos de precios OMIE."""
    state = MagicMock()
    state.state = "on"
    state.attributes = {"precios": precios}
    return state


@pytest.mark.asyncio
async def test_obtener_precios_del_dia_integracion(
    cliente_omie, fixture_respuesta_integracion_omie
):
    """Test de obtener precios usando la integración OMIE."""
    hoy = datetime.now(tz=UTC).date()
    cliente_omie.hass.config.components = ["omie"]
    cliente_omie.hass.states.get = MagicMock(
        return_value=_estado_con_precios(fixture_respuesta_integracion_omie)
    )

    ranuras = await cliente_omie.obtener_precios_del_dia(hoy)

    assert len(ranuras) == 96  # Normalizado a 96 tramos
    assert ranuras[0].fuente == "omie"
    assert isinstance(ranuras[0].precio_eur_kwh, float)


@pytest.mark.asyncio
async def test_obtener_precios_del_dia_fallback_redata(
    cliente_omie, fixture_respuesta_redata
):
    """Test de fallback a REData cuando la integración OMIE no está disponible."""
    cliente_omie.hass.config.components = []  # No tiene integración OMIE

    # Mock de la respuesta HTTP de REData
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=fixture_respuesta_redata)
    mock_response.__aenter__.return_value = mock_response
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)

    with patch.object(
        cliente_omie, "_obtener_session_aiohttp", new=AsyncMock(return_value=mock_session)
    ):
        hoy = datetime.now(tz=UTC).date()
        ranuras = await cliente_omie.obtener_precios_del_dia(hoy)

    # Verificar que se usó REData
    assert len(ranuras) == 96
    assert ranuras[0].fuente == "redata"


@pytest.mark.asyncio
async def test_obtener_precios_del_dia_cache(
    cliente_omie, fixture_respuesta_integracion_omie
):
    """Test de que la cache evita llamadas repetidas."""
    call_count = 0

    def mock_states_get(entity_id):
        nonlocal call_count
        call_count += 1
        return _estado_con_precios(fixture_respuesta_integracion_omie)

    cliente_omie.hass.config.components = ["omie"]
    cliente_omie.hass.states.get = MagicMock(side_effect=mock_states_get)

    hoy = datetime.now(tz=UTC).date()

    # Primera llamada - debe consultar el sensor OMIE
    ranuras1 = await cliente_omie.obtener_precios_del_dia(hoy)
    assert call_count == 1

    # Segunda llamada - debe usar cache
    ranuras2 = await cliente_omie.obtener_precios_del_dia(hoy)
    assert call_count == 1  # No incrementa

    # Verificar que las ranuras son las mismas
    assert ranuras1 == ranuras2


@pytest.mark.asyncio
async def test_normalizar_a_15min_horario(
    cliente_omie, fixture_respuesta_integracion_omie_horario
):
    """Test de normalización de día con cambio horario (92 tramos)."""
    cliente_omie.hass.config.components = ["omie"]
    cliente_omie.hass.states.get = MagicMock(
        return_value=_estado_con_precios(fixture_respuesta_integracion_omie_horario)
    )

    hoy = datetime.now(tz=UTC).date()
    ranuras = await cliente_omie.obtener_precios_del_dia(hoy)

    # Verificar que se normalizó a 96 tramos
    assert len(ranuras) == 96


@pytest.mark.asyncio
async def test_todas_las_fuentes_fallan(cliente_omie):
    """Test de error cuando todas las fuentes fallan."""
    cliente_omie.hass.config.components = []  # No tiene integración OMIE

    hoy = datetime.now(tz=UTC).date()

    # REData falla (error de red) y ESIOS es un placeholder vacío
    with patch.object(
        cliente_omie,
        "_obtener_session_aiohttp",
        new=AsyncMock(side_effect=ErrorFuenteOmie("fallo de red")),
    ), pytest.raises(ErrorFuenteOmie):
        await cliente_omie.obtener_precios_del_dia(hoy)
