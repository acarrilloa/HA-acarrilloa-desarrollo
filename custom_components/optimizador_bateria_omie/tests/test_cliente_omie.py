"""Tests para ClienteOmie."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.optimizador_bateria_omie.cliente_omie import (
    ErrorIntegracionNoDisponible,
)


@pytest.mark.asyncio
async def test_obtener_precios_del_dia_integracion(
    cliente_omie, fixture_respuesta_integracion_omie
):
    """Test de obtener precios usando la integración OMIE."""
    # Mockear el servicio
    async def mock_call(svc, service, data, blocking, return_response):
        return fixture_respuesta_integracion_omie

    cliente_omie.hass.services.async_call = AsyncMock(side_effect=mock_call)
    cliente_omie.hass.config.components = ["omie"]

    # Obtener precios
    from datetime import datetime, timezone

    hoy = datetime.now(tz=timezone.utc).date()
    ranuras = await cliente_omie.obtener_precios_del_dia(hoy)

    # Verificar
    assert len(ranuras) == 96  # Normalizado a 96 tramos
    assert ranuras[0].fuente == "omie"
    assert isinstance(ranuras[0].precio_eur_kwh, float)


@pytest.mark.asyncio
async def test_obtener_precios_del_dia_fallback_redata(
    cliente_omie, fixture_respuesta_redata
):
    """Test de fallback a REData cuando la integración OMIE no está disponible."""
    # Mockear: integración OMIE no disponible
    cliente_omie.hass.config.components = []  # No tiene integración OMIE

    # Mockear aiohttp
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=fixture_respuesta_redata)
    mock_session.get = AsyncMock(return_value=mock_response)

    with patch.object(
        cliente_omie, "_obtener_session_aiohttp", new_callable=AsyncMock
    ) as mock_session_method:
        mock_session_method.return_value = mock_session

        from datetime import datetime, timezone

        hoy = datetime.now(tz=timezone.utc).date()
        ranuras = await cliente_omie.obtener_precios_del_dia(hoy)

        # Verificar que se usó REData
        assert len(ranuras) == 96
        assert ranuras[0].fuente == "redata"


@pytest.mark.asyncio
async def test_obtener_precios_del_dia_cache(
    cliente_omie, fixture_respuesta_integracion_omie, tmp_path
):
    """Test de que la cache evita llamadas repetidas."""
    # Configurar directorio de cache temporal
    cliente_omie._dir_cache = tmp_path

    # Mockear el servicio
    call_count = 0

    async def mock_call(svc, service, data, blocking, return_response):
        nonlocal call_count
        call_count += 1
        return fixture_respuesta_integracion_omie

    cliente_omie.hass.services.async_call = AsyncMock(side_effect=mock_call)

    from datetime import datetime, timezone

    hoy = datetime.now(tz=timezone.utc).date()

    # Primera llamada - debe llamar al servicio
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
    # Mockear el servicio con respuesta de 92 tramos
    async def mock_call(svc, service, data, blocking, return_response):
        return fixture_respuesta_integracion_omie_horario

    cliente_omie.hass.services.async_call = AsyncMock(side_effect=mock_call)
    cliente_omie.hass.config.components = ["omie"]

    from datetime import date

    hoy = date(2025, 3, 30)
    ranuras = await cliente_omie.obtener_precios_del_dia(hoy)

    # Verificar que se normalizó a 96 tramos
    assert len(ranuras) == 96


@pytest.mark.asyncio
async def test_integracion_no_disponible(cliente_omie):
    """Test de manejo de error cuando la integración OMIE no existe."""
    cliente_omie.hass.config.components = []  # No tiene integración OMIE

    from datetime import datetime, timezone

    hoy = datetime.now(tz=timezone.utc).date()

    with pytest.raises(ErrorIntegracionNoDisponible):
        await cliente_omie.obtener_precios_del_dia(hoy)
