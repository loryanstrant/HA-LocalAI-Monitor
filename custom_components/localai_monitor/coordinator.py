"""Data coordinator for the LocalAI Manager integration."""
from asyncio import timeout
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    ENDPOINT_BACKENDS,
    ENDPOINT_MODELS,
    ENDPOINT_MODELS_JOBS,
    ENDPOINT_SYSTEM,
    ENDPOINT_RESOURCES,
    ENDPOINT_VERSION,
    SENSOR_BACKENDS,
    SENSOR_MODELS,
    SENSOR_MODELS_JOBS,
    SENSOR_SYSTEM,
    SENSOR_RESOURCES,
    SENSOR_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class LocalAIDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching LocalAI data."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str | None,
        verify_ssl: bool,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self._hass = hass
        self.last_update_success_time: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        session = async_get_clientsession(self._hass, verify_ssl=self.verify_ssl)

        try:
            async with timeout(30):
                data = {}
                
                # Fetch backends
                data[SENSOR_BACKENDS] = await self._fetch_endpoint(session, ENDPOINT_BACKENDS)
                
                # Fetch models
                data[SENSOR_MODELS] = await self._fetch_endpoint(session, ENDPOINT_MODELS)
                
                # Fetch model jobs
                data[SENSOR_MODELS_JOBS] = await self._fetch_endpoint(session, ENDPOINT_MODELS_JOBS)
                
                # Fetch system info
                data[SENSOR_SYSTEM] = await self._fetch_endpoint(session, ENDPOINT_SYSTEM)
                
                # Fetch resources (undocumented)
                data[SENSOR_RESOURCES] = await self._fetch_endpoint(session, ENDPOINT_RESOURCES)
                
                # Fetch version
                data[SENSOR_VERSION] = await self._fetch_endpoint(session, ENDPOINT_VERSION)
                
                self.last_update_success_time = datetime.now(timezone.utc)
                return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_endpoint(self, session, endpoint: str) -> dict[str, Any] | list[Any] | None:
        """Fetch data from a specific endpoint."""
        url = f"{self.url}{endpoint}"
        headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with session.get(
                url,
                headers=headers,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.warning(
                        "Failed to fetch %s: HTTP %s", endpoint, response.status
                    )
                    return None
        except Exception as err:
            _LOGGER.warning("Error fetching %s: %s", endpoint, err)
            return None


