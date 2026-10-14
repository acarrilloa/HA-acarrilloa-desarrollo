"""Entidades (sensores) para la integración Optimizador Batería OMIE."""

from typing import ClassVar

from homeassistant.const import (
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from custom_components.optimizador_bateria_omie.const import (
    ATTR_FUENTE,
    ATTR_MAX,
    ATTR_MEDIANA,
    ATTR_MIN,
    ATTR_TS_ACTUALIZACION,
    DOMAIN,
    SENSOR_PRECIO_ACTUAL,
    SENSOR_PRECIO_CLASIFICACION,
    SENSOR_PRECIO_EFECTIVO,
    SENSOR_PRECIO_ESTADISTICAS,
)
from custom_components.optimizador_bateria_omie.coordinador import CoordinadorDatosOmie


class SensorBase(CoordinatorEntity):
    """Clase base para los sensores."""

    def __init__(self, coordinador: CoordinadorDatosOmie):
        """Inicializa el sensor."""
        super().__init__(coordinador)
        self._attr = {}

    @property
    def device_info(self) -> DeviceInfo:
        """Información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, "optimizador_bateria_omie")},
            name="Optimizador Batería OMIE",
            manufacturer="Custom Component",
            model="Optimizador Batería OMIE",
        )


class SensorPrecioActual(SensorBase):
    """Sensor para el precio actual de la electricidad."""

    _attr_templates: ClassVar[dict] = {
        "friendly_name": "Precio actual",
        "unique_id": SENSOR_PRECIO_ACTUAL,
    }

    def __init__(self, coordinador: CoordinadorDatosOmie):
        """Inicializa el sensor."""
        super().__init__(coordinador)
        self._attr[CONF_UNIT_OF_MEASUREMENT] = "€/kWh"
        self._attr[ATTR_FUENTE] = None

    @property
    def unique_id(self) -> str:
        """ID único del sensor."""
        return SENSOR_PRECIO_ACTUAL

    @property
    def name(self) -> str:
        """Nombre del sensor."""
        return "Precio actual"

    @property
    def native_unit_of_measurement(self) -> str:
        """Unidad de medida nativa."""
        return "€/kWh"

    @property
    def suggested_unit_of_measurement(self) -> str:
        """Unidad de medida sugerida."""
        return "€"

    @callback
    def async_update(self):
        """Actualiza el estado del sensor."""
        precio = self.coordinator.obtener_precio_actual()
        if precio is not None:
            self._attr[ATTR_FUENTE] = self.coordinator._datos.fuente if self.coordinator._datos else None
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | str:
        """Valor nativo del sensor."""
        precio = self.coordinator.obtener_precio_actual()
        if precio is not None:
            return round(precio, 4)
        return STATE_UNAVAILABLE

    @property
    def available(self) -> bool:
        """Indica si el sensor está disponible."""
        return self.coordinator.obtener_precio_actual() is not None


class SensorPrecioEfectivo(SensorBase):
    """Sensor para el precio efectivo (con peajes, cargos e impuestos)."""

    def __init__(self, coordinador: CoordinadorDatosOmie):
        """Inicializa el sensor."""
        super().__init__(coordinador)
        self._attr[CONF_UNIT_OF_MEASUREMENT] = "€/kWh"

    @property
    def unique_id(self) -> str:
        """ID único del sensor."""
        return SENSOR_PRECIO_EFECTIVO

    @property
    def name(self) -> str:
        """Nombre del sensor."""
        return "Precio efectivo"

    @property
    def native_unit_of_measurement(self) -> str:
        """Unidad de medida nativa."""
        return "€/kWh"

    @property
    def suggested_unit_of_measurement(self) -> str:
        """Unidad de medida sugerida."""
        return "€"

    @callback
    def async_update(self):
        """Actualiza el estado del sensor."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | str:
        """Valor nativo del sensor."""
        precio = self.coordinator.obtener_precio_efectivo_actual()
        if precio is not None:
            return round(precio, 4)
        return STATE_UNAVAILABLE

    @property
    def available(self) -> bool:
        """Indica si el sensor está disponible."""
        return self.coordinator.obtener_precio_efectivo_actual() is not None


class SensorPrecioClasificacion(SensorBase):
    """Sensor para la clasificación del precio (valle, llano, punta)."""

    def __init__(self, coordinador: CoordinadorDatosOmie):
        """Inicializa el sensor."""
        super().__init__(coordinador)

    @property
    def unique_id(self) -> str:
        """ID único del sensor."""
        return SENSOR_PRECIO_CLASIFICACION

    @property
    def name(self) -> str:
        """Nombre del sensor."""
        return "Clasificación"

    @property
    def native_unit_of_measurement(self) -> str:
        """Unidad de medida nativa."""
        return None

    @callback
    def async_update(self):
        """Actualiza el estado del sensor."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Valor nativo del sensor."""
        clasificacion = self.coordinator.obtener_clasificacion_actual()
        if clasificacion is not None:
            return clasificacion
        return STATE_UNAVAILABLE

    @property
    def available(self) -> bool:
        """Indica si el sensor está disponible."""
        return self.coordinator.obtener_clasificacion_actual() is not None


class SensorPrecioEstadisticas(SensorBase):
    """Sensor para estadísticas de precios."""

    def __init__(self, coordinador: CoordinadorDatosOmie):
        """Inicializa el sensor."""
        super().__init__(coordinador)

    @property
    def unique_id(self) -> str:
        """ID único del sensor."""
        return SENSOR_PRECIO_ESTADISTICAS

    @property
    def name(self) -> str:
        """Nombre del sensor."""
        return "Estadísticas"

    @property
    def native_unit_of_measurement(self) -> str:
        """Unidad de medida nativa."""
        return "€/kWh"

    @callback
    def async_update(self):
        """Actualiza el estado del sensor."""
        estadisticas = self.coordinator.obtener_estadisticas_actual()
        if estadisticas:
            self._attr[ATTR_MIN] = estadisticas.get(ATTR_MIN, 0)
            self._attr[ATTR_MAX] = estadisticas.get(ATTR_MAX, 0)
            self._attr[ATTR_MEDIANA] = estadisticas.get(ATTR_MEDIANA, 0)
            self._attr[ATTR_FUENTE] = self.coordinator._datos.fuente if self.coordinator._datos else None
            self._attr[ATTR_TS_ACTUALIZACION] = (
                self.coordinator._datos.ts_actualizacion.isoformat()
                if self.coordinator._datos
                else None
            )
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | str:
        """Valor nativo del sensor (mediana)."""
        estadisticas = self.coordinator.obtener_estadisticas_actual()
        if estadisticas:
            return estadisticas.get(ATTR_MEDIANA, 0)
        return STATE_UNAVAILABLE

    @property
    def available(self) -> bool:
        """Indica si el sensor está disponible."""
        return self.coordinator.obtener_estadisticas_actual() is not None

    @property
    def extra_state_attributes(self) -> dict:
        """Atributos adicionales del estado."""
        return self._attr
