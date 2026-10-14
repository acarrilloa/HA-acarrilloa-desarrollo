"""Custom component para optimizar el uso de baterías con precios OMIE."""

import importlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS = ["sensor"]


def _cargar_plataformas() -> None:
    """Pre-importa los módulos de plataforma fuera del event loop.

    ``async_forward_entry_setups`` importa los módulos de plataforma con
    ``importlib.import_module``, que es una llamada bloqueante. Importándolos
    aquí (mediante ``hass.async_add_executor_job``) se evita la advertencia
    "Detected blocking call to import_module inside the event loop".
    """
    for plataforma in PLATFORMS:
        importlib.import_module(f"{__name__}.{plataforma}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuración de la integración."""
    await hass.async_add_executor_job(_cargar_plataformas)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Desconfiguración de la integración."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
