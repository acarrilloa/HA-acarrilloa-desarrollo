"""Tests para CoordinadorDatosOmie."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from custom_components.optimizador_bateria_omie.cliente_omie import Ranura
from custom_components.optimizador_bateria_omie.coordinador import (
    CoordinadorDatosOmie,
    DatosOmie,
)


def _ranura(inicio: datetime, precio: float) -> Ranura:
    """Crea una ranura de 15 minutos en UTC."""
    return Ranura(
        fecha_hora_utc=inicio,
        precio_eur_kwh=precio,
        fuente="omie",
        fecha_publicacion=datetime.now(tz=UTC),
        fecha_hora_fin_utc=inicio + timedelta(minutes=15),
    )


@pytest.fixture
def coordinador():
    """Fixture para CoordinadorDatosOmie con mocks."""
    hass = MagicMock()
    return CoordinadorDatosOmie(
        hass, MagicMock(), MagicMock(), MagicMock()
    )


def test_precio_actual_en_precios_hoy(coordinador):
    """La ranura actual se busca primero en precios_hoy."""
    ahora = datetime.now(tz=UTC)
    coordenada = ahora.replace(minute=(ahora.minute // 15) * 15, second=0, microsecond=0)
    coordinador._datos = DatosOmie(
        precios_hoy=[_ranura(coordenada, 0.1234)],
        precios_manana=None,
        clasificaciones_hoy=[],
        clasificaciones_manana=None,
        estadisticas_hoy={},
        estadisticas_manana=None,
        fuente="omie",
        ts_actualizacion=datetime.now(tz=UTC),
    )

    assert coordinador.obtener_precio_actual() == pytest.approx(0.1234)


def test_precio_actual_fallback_precios_manana(coordinador):
    """Entre las 00:00 y las 02:00 locales la ranura actual pertenece al día
    local siguiente: se busca en precios_manana si no está en precios_hoy."""
    ahora = datetime.now(tz=UTC)
    coordenada = ahora.replace(minute=(ahora.minute // 15) * 15, second=0, microsecond=0)
    # precios_hoy: tramo ya pasado (hace 2 horas); precios_manana: el tramo actual
    coordinador._datos = DatosOmie(
        precios_hoy=[_ranura(coordenada - timedelta(hours=2), 0.1111)],
        precios_manana=[_ranura(coordenada, 0.2222)],
        clasificaciones_hoy=[],
        clasificaciones_manana=None,
        estadisticas_hoy={},
        estadisticas_manana=None,
        fuente="omie",
        ts_actualizacion=datetime.now(tz=UTC),
    )

    assert coordinador.obtener_precio_actual() == pytest.approx(0.2222)
    assert coordinador.obtener_ranura_actual() is not None


def test_precio_actual_no_disponible(coordinador):
    """Sin ranura actual en ningún día → None."""
    ahora = datetime.now(tz=UTC)
    coordinador._datos = DatosOmie(
        precios_hoy=[_ranura(ahora - timedelta(hours=5), 0.1111)],
        precios_manana=None,
        clasificaciones_hoy=[],
        clasificaciones_manana=None,
        estadisticas_hoy={},
        estadisticas_manana=None,
        fuente="omie",
        ts_actualizacion=datetime.now(tz=UTC),
    )

    assert coordinador.obtener_precio_actual() is None
    assert coordinador.obtener_ranura_actual() is None
