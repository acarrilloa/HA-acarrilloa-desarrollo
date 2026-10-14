"""Entidades (sensores) para la integración Optimizador Batería OMIE."""

from homeassistant.const import STATE_UNAVAILABLE
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


class SensorBase(CoordinatorEntity):
    """Clase base para los sensores."""

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

    @property
    def extra_state_attributes(self) -> dict | None:
        """Atributos adicionales: fuente de los datos."""
        datos = self.coordinator.datos
        if datos is not None:
            return {ATTR_FUENTE: datos.fuente}
        return None


class SensorPrecioEfectivo(SensorBase):
    """Sensor para el precio efectivo (con peajes, cargos e impuestos)."""

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

    @property
    def unique_id(self) -> str:
        """ID único del sensor."""
        return SENSOR_PRECIO_CLASIFICACION

    @property
    def name(self) -> str:
        """Nombre del sensor."""
        return "Clasificación"

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Unidad de medida nativa."""
        return None

    @property
    def native_value(self) -> str | None:
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
    def extra_state_attributes(self) -> dict | None:
        """Atributos adicionales del estado."""
        estadisticas = self.coordinator.obtener_estadisticas_actual()
        if not estadisticas:
            return None
        datos = self.coordinator.datos
        return {
            ATTR_MIN: estadisticas.get(ATTR_MIN, 0),
            ATTR_MAX: estadisticas.get(ATTR_MAX, 0),
            ATTR_MEDIANA: estadisticas.get(ATTR_MEDIANA, 0),
            ATTR_FUENTE: datos.fuente if datos else None,
            ATTR_TS_ACTUALIZACION: (
                datos.ts_actualizacion.isoformat() if datos else None
            ),
        }
