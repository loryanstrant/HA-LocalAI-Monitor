"""Config flow for LocalAI Manager integration."""
from __future__ import annotations

from asyncio import timeout
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    url = data[CONF_URL].rstrip("/")
    api_key = data.get(CONF_API_KEY)
    verify_ssl = data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    try:
        async with timeout(10):
            async with session.get(
                f"{url}/system",
                headers=headers,
            ) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to connect: HTTP {response.status}")
                
                # Try to parse response
                await response.json()

    except aiohttp.ClientError as err:
        raise ValueError(f"Cannot connect to LocalAI: {err}") from err
    except Exception as err:
        raise ValueError(f"Unexpected error: {err}") from err

    return {"title": data.get(CONF_NAME, DEFAULT_NAME)}


class LocalAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LocalAI."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LocalAIOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LocalAIOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Check for duplicate entries - normalize URL first
                normalized_url = user_input[CONF_URL].rstrip("/")
                await self.async_set_unique_id(normalized_url)
                self._abort_if_unique_id_configured()
                
                info = await validate_input(self.hass, user_input)
            except ValueError as err:
                _LOGGER.exception("Validation failed")
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Optional(CONF_API_KEY): str,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)


class LocalAIOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for LocalAI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=self.config_entry.options.get(
                            CONF_VERIFY_SSL,
                            self.config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                        ),
                    ): bool,
                }
            ),
        )
