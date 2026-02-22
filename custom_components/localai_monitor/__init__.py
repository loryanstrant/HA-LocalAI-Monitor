"""The LocalAI Monitor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import LocalAIDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Service names
SERVICE_SHUTDOWN_MODEL = "shutdown_model"

# Service schema
SERVICE_SHUTDOWN_MODEL_SCHEMA = vol.Schema(
    {
        vol.Required("model_name"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LocalAI from a config entry."""
    url = entry.data[CONF_URL]
    api_key = entry.data.get(CONF_API_KEY)
    verify_ssl = entry.options.get(
        CONF_VERIFY_SSL,
        entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = LocalAIDataUpdateCoordinator(
        hass, url, api_key, verify_ssl, scan_interval
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once for all instances)
    if not hass.services.has_service(DOMAIN, SERVICE_SHUTDOWN_MODEL):
        async def handle_shutdown_model(call: ServiceCall) -> None:
            """Handle the shutdown_model service call."""
            model_name = call.data["model_name"]
            
            # Try to find an available coordinator to use
            # In the future, we could add a device selector to target specific instances
            domain_data = hass.data.get(DOMAIN, {})
            if not domain_data:
                _LOGGER.error("No LocalAI instances configured")
                return
            
            # Use the first available coordinator
            coordinator = next(iter(domain_data.values()))
            
            _LOGGER.info("Shutting down model: %s", model_name)
            
            url = f"{coordinator.url}/backend/shutdown"
            headers = {"Content-Type": "application/json"}
            
            if coordinator.api_key:
                headers["Authorization"] = f"Bearer {coordinator.api_key}"
            
            session = async_get_clientsession(hass, verify_ssl=coordinator.verify_ssl)
            
            try:
                from asyncio import timeout
                async with timeout(10):
                    async with session.post(
                        url,
                        json={"model": model_name},
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            _LOGGER.info("Successfully shut down model: %s", model_name)
                            # Trigger coordinator refresh to update status
                            await coordinator.async_request_refresh()
                        else:
                            error_msg = f"Failed to shut down model {model_name}: HTTP {response.status}"
                            _LOGGER.error(error_msg)
                            raise HomeAssistantError(error_msg)
            except HomeAssistantError:
                raise
            except Exception as err:
                error_msg = f"Error shutting down model {model_name}: {err}"
                _LOGGER.error(error_msg)
                raise HomeAssistantError(error_msg) from err
        
        hass.services.async_register(
            DOMAIN,
            SERVICE_SHUTDOWN_MODEL,
            handle_shutdown_model,
            schema=SERVICE_SHUTDOWN_MODEL_SCHEMA,
        )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        
        # Only unregister the service when unloading the last config entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SHUTDOWN_MODEL)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
