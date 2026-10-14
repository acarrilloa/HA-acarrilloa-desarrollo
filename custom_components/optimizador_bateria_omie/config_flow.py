"""Configuración flow para la integración Optimizador Batería OMIE."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from custom_components.optimizador_bateria_omie.const import (
    DEFAULT_DIAS_CACHE,
    DEFAULT_FUENTE_PRIORITARIA,
    DEFAULT_USAR_CACHE,
    DOMAIN,
)

# Schema para la configuración
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("fuente_prioritaria", default=DEFAULT_FUENTE_PRIORITARIA): str,
        vol.Required("usar_cache", default=DEFAULT_USAR_CACHE): bool,
        vol.Required("dias_cache", default=DEFAULT_DIAS_CACHE): int,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Maneja el flujo de configuración."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_data_schema():
        """Devuelve el schema para el formulario de configuración."""
        return CONFIG_SCHEMA

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Maneja el paso de configuración del usuario."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validar entrada
            try:
                validated_input = CONFIG_SCHEMA(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_input"

            if not errors:
                # Crear entrada de configuración
                return self.async_create_entry(
                    title="Optimizador Batería OMIE",
                    data=validated_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.async_get_data_schema(),
            errors=errors,
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Maneja la importación desde YAML."""
        return await self.async_step_user(import_config)
