"""Custom component para optimizar el uso de baterías con precios OMIE."""

from homeassistant.core import HomeAssistant

from custom_components.optimizador_bateria_omie.const import DOMAIN

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry):
    """Configuración de la integración."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Desconfiguración de la integración."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return True
