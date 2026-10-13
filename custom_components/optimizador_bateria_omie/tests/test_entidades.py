"""Tests para entidades (sensores)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from custom_components.optimizador_bateria_omie.cliente_omie import Ranura
from custom_components.optimizador_bateria_omie.coordinador import (
    CoordinadorDatosOmie,
    DatosOmie,
)
from custom_components.optimizador_bateria_omie.entidades import (
    SensorPrecioActual,
    SensorPrecioClasificacion,
    SensorPrecioEfectivo,
    SensorPrecioEstadisticas,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_coordinador():
    """Fixture para CoordinadorDatosOmie con datos mock."""
    hass = MagicMock(spec=HomeAssistant)
    cliente_omie = MagicMock()
    modelo_tarifa = MagicMock()

    coordinador = CoordinadorDatosOmie(hass, cliente_omie, modelo_tarifa)

    # Crear datos mock
    hoy = datetime.now(tz=timezone.utc).date()
    tz_utc = timezone.utc
    ranuras_hoy = [
        Ranura(
            fecha_hora_utc=datetime(hoy.year, hoy.month, hoy.day, h, m, tzinfo=tz_utc),
            precio_eur_kwh=0.10 + h * 0.01,
            fuente="omie",
            fecha_publicacion=datetime.now(tz=tz_utc),
        )
        for h in range(24)
        for m in [0, 15, 30, 45]
    ]

    coordinador._datos = DatosOmie(
        precios_hoy=ranuras_hoy,
        precios_manana=None,
        clasificaciones_hoy=["valle"] * 96,
        clasificaciones_manana=None,
        estadisticas_hoy={"min": 0.10, "max": 0.34, "mediana": 0.22},
        estadisticas_manana=None,
        fuente="omie",
        ts_actualizacion=datetime.now(tz=tz_utc),
    )

    return coordinador


@pytest.fixture
def sensor_precio_actual(mock_coordinador):
    """Fixture para SensorPrecioActual."""
    return SensorPrecioActual(mock_coordinador)


@pytest.fixture
def sensor_precio_efectivo(mock_coordinador):
    """Fixture para SensorPrecioEfectivo."""
    return SensorPrecioEfectivo(mock_coordinador)


@pytest.fixture
def sensor_precio_clasificacion(mock_coordinador):
    """Fixture para SensorPrecioClasificacion."""
    return SensorPrecioClasificacion(mock_coordinador)


@pytest.fixture
def sensor_precio_estadisticas(mock_coordinador):
    """Fixture para SensorPrecioEstadisticas."""
    return SensorPrecioEstadisticas(mock_coordinador)


class TestSensorPrecioActual:
    """Tests para SensorPrecioActual."""

    def test_unique_id(self, sensor_precio_actual):
        """Test de unique_id."""
        assert sensor_precio_actual.unique_id == "ob_precio_actual"

    def test_nombre(self, sensor_precio_actual):
        """Test de nombre."""
        assert sensor_precio_actual.name == "Precio actual"

    def test_unidad(self, sensor_precio_actual):
        """Test de unidad de medida."""
        assert sensor_precio_actual.native_unit_of_measurement == "kWh"
        assert (
            sensor_precio_actual.suggested_unit_of_measurement == "€"
        )

    def test_estado(self, sensor_precio_actual):
        """Test de estado."""
        # Mockear obtener_precio_actual para que devuelva un valor
        sensor_precio_actual.coordinador.obtener_precio_actual = MagicMock(
            return_value=0.15
        )
        sensor_precio_actual.async_update()

        assert sensor_precio_actual.native_value == 0.15
        assert sensor_precio_actual.available is True

    def test_disponibilidad(self, sensor_precio_actual):
        """Test de disponibilidad cuando no hay datos."""
        sensor_precio_actual.coordinador.obtener_precio_actual = MagicMock(
            return_value=None
        )
        sensor_precio_actual.async_update()

        assert sensor_precio_actual.native_value == STATE_UNAVAILABLE
        assert sensor_precio_actual.available is False


class TestSensorPrecioEfectivo:
    """Tests para SensorPrecioEfectivo."""

    def test_unique_id(self, sensor_precio_efectivo):
        """Test de unique_id."""
        assert sensor_precio_efectivo.unique_id == "ob_precio_efectivo"

    def test_nombre(self, sensor_precio_efectivo):
        """Test de nombre."""
        assert sensor_precio_efectivo.name == "Precio efectivo"

    def test_estado(self, sensor_precio_efectivo):
        """Test de estado."""
        sensor_precio_efectivo.coordinador.obtener_precio_efectivo_actual = (
            MagicMock(return_value=0.20)
        )
        sensor_precio_efectivo.coordinador.obtener_ranura_actual = MagicMock(
            return_value=Ranura(
                datetime.now(tz=timezone.utc),
                0.15,
                "omie",
                datetime.now(tz=timezone.utc),
            )
        )
        sensor_precio_efectivo.async_update()

        assert sensor_precio_efectivo.native_value == 0.20
        assert sensor_precio_efectivo.available is True


class TestSensorPrecioClasificacion:
    """Tests para SensorPrecioClasificacion."""

    def test_unique_id(self, sensor_precio_clasificacion):
        """Test de unique_id."""
        assert (
            sensor_precio_clasificacion.unique_id
            == "ob_precio_clasificacion"
        )

    def test_nombre(self, sensor_precio_clasificacion):
        """Test de nombre."""
        assert sensor_precio_clasificacion.name == "Clasificación"

    def test_estado(self, sensor_precio_clasificacion):
        """Test de estado."""
        sensor_precio_clasificacion.coordinador.obtener_clasificacion_actual = (
            MagicMock(return_value="punta")
        )
        sensor_precio_clasificacion.async_update()

        assert sensor_precio_clasificacion.native_value == "punta"
        assert sensor_precio_clasificacion.available is True


class TestSensorPrecioEstadisticas:
    """Tests para SensorPrecioEstadisticas."""

    def test_unique_id(self, sensor_precio_estadisticas):
        """Test de unique_id."""
        assert (
            sensor_precio_estadisticas.unique_id == "ob_precio_estadisticas"
        )

    def test_nombre(self, sensor_precio_estadisticas):
        """Test de nombre."""
        assert sensor_precio_estadisticas.name == "Estadísticas"

    def test_estado(self, sensor_precio_estadisticas):
        """Test de estado."""
        sensor_precio_estadisticas.coordinador.obtener_estadisticas_actual = (
            MagicMock(return_value={"min": 0.10, "max": 0.30, "mediana": 0.20})
        )
        sensor_precio_estadisticas.async_update()

        assert sensor_precio_estadisticas.native_value == 0.20
        assert sensor_precio_estadisticas.available is True
        assert "min" in sensor_precio_estadisticas.extra_state_attributes
        assert "max" in sensor_precio_estadisticas.extra_state_attributes
        assert "mediana" in sensor_precio_estadisticas.extra_state_attributes
