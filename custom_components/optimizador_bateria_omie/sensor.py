"""Plataforma de sensores para la integración Optimizador Batería OMIE."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.optimizador_bateria_omie.cliente_omie import (
    ClienteOmie,
    ConfiguracionOmie,
)
from custom_components.optimizador_bateria_omie.coordinador import CoordinadorDatosOmie
from custom_components.optimizador_bateria_omie.entidades import (
    SensorPrecioActual,
    SensorPrecioClasificacion,
    SensorPrecioEfectivo,
    SensorPrecioEstadisticas,
)
from custom_components.optimizador_bateria_omie.tarifa import ModeloTarifa

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configuración de los sensores."""
    _LOGGER.info("Configurando sensores de Optimizador Batería OMIE")
    try:
        # Crear configuraciones
        config_omie = ConfiguracionOmie(
            fuente_prioritaria=entry.options.get("fuente_prioritaria", "omie"),
            usar_cache=entry.options.get("usar_cache", True),
            dias_cache=entry.options.get("dias_cache", 7),
        )
        
        modelo_tarifa = ModeloTarifa()
        cliente_omie = ClienteOmie(hass, config_omie)
        coordinador = CoordinadorDatosOmie(hass, cliente_omie, modelo_tarifa)
        
        # Iniciar actualización del coordinador (no bloquear si falla)
        # El primer refresh no debe romper el setup: los sensores se
        # actualizan en el siguiente intervalo del coordinador.
        try:
            await coordinador.async_config_entry_first_refresh()
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning(f"No se pudo obtener datos iniciales: {e}. Los sensores se actualizarán en el próximo intervalo.")
        
        # Crear sensores
        sensores = [
            SensorPrecioActual(coordinador),
            SensorPrecioEfectivo(coordinador),
            SensorPrecioClasificacion(coordinador),
            SensorPrecioEstadisticas(coordinador),
        ]
        
        # Añadir sensores
        async_add_entities(sensores)
        _LOGGER.info(f"Sensores configurados correctamente: {len(sensores)} sensores")
        
    except Exception:
        _LOGGER.exception("Error al configurar sensores")
        raise
